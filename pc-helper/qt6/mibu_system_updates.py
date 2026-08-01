from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Callable

from mibu_actions import APP_PACKAGE, Result, check_device_ready, parse_installed_packages, run_tool

AdbRunner = Callable[[list[str], int], Result]
ReadyCheck = Callable[[], Result]

UPDATER_PACKAGE = "com.android.updater"
OTA_AUTO_SETTING = "ota_disable_automatic_update"
UPDATE_CONTROL_RECEIVER = f"{APP_PACKAGE}/.SystemUpdateControlReceiver"
UPDATE_CONTROL_TAG = "MIBU_UPDATE_CONTROL"

_REQUEST = re.compile(r"UPDATE_REQUEST\s+id=([A-Za-z0-9._-]+)\s+action=(DISABLE|ENABLE)\b")
_RESULT = re.compile(r"UPDATE_RESULT\s+id=([A-Za-z0-9._-]+)\s+state=([A-Z_]+)\b")


@dataclass(frozen=True)
class SystemUpdateState:
    package_installed: bool
    package_enabled: bool
    automatic_updates_disabled: bool

    @property
    def fully_disabled(self) -> bool:
        return self.package_installed and not self.package_enabled and self.automatic_updates_disabled

    @property
    def fully_enabled(self) -> bool:
        return self.package_installed and self.package_enabled and not self.automatic_updates_disabled

    def summary(self) -> str:
        if not self.package_installed:
            return f"Updater package {UPDATER_PACKAGE} is missing."
        return (
            f"Updater package: {'enabled' if self.package_enabled else 'disabled'}\n"
            f"Automatic OTA: {'disabled' if self.automatic_updates_disabled else 'enabled'}"
        )


@dataclass(frozen=True)
class SystemUpdateRequest:
    request_id: str
    action: str


def _run(runner: AdbRunner, parts: list[str], timeout: int = 30) -> Result:
    return runner(parts, timeout)


def read_system_update_state(
    runner: AdbRunner = run_tool,
    ready_check: ReadyCheck = check_device_ready,
) -> tuple[Result, SystemUpdateState | None]:
    ready = ready_check()
    if not ready.ok:
        return ready, None
    enabled = _run(runner, ["shell", "pm", "list", "packages", "-e", "--user", "0"], 45)
    disabled = _run(runner, ["shell", "pm", "list", "packages", "-d", "--user", "0"], 45)
    known = _run(runner, ["shell", "pm", "list", "packages", "-u", "--user", "0"], 45)
    setting = _run(runner, ["shell", "settings", "get", "global", OTA_AUTO_SETTING])
    if not enabled.ok or not disabled.ok or not known.ok or not setting.ok:
        details = "\n".join(result.message for result in (enabled, disabled, known, setting) if not result.ok)
        return Result(False, "Could not read the Xiaomi updater state.\n" + details), None
    enabled_packages = set(parse_installed_packages(enabled.message))
    known_packages = set(parse_installed_packages(known.message))
    state = SystemUpdateState(
        package_installed=UPDATER_PACKAGE in known_packages,
        package_enabled=UPDATER_PACKAGE in enabled_packages,
        automatic_updates_disabled=setting.message.strip() == "1",
    )
    if not state.package_installed:
        return Result(False, state.summary()), state
    return Result(True, state.summary()), state


def set_system_updates_disabled(
    disabled: bool,
    *,
    runner: AdbRunner = run_tool,
    ready_check: ReadyCheck = check_device_ready,
) -> Result:
    ready = ready_check()
    if not ready.ok:
        return ready
    initial_result, initial_state = read_system_update_state(
        runner=runner,
        ready_check=lambda: Result(True, "Device already checked."),
    )
    if initial_result.ok and initial_state is not None:
        already_requested = initial_state.fully_disabled if disabled else initial_state.fully_enabled
        if already_requested:
            verb = "disabled" if disabled else "enabled"
            return Result(True, f"System updates were already {verb} and are verified.\n{initial_state.summary()}")

    if disabled:
        operations = (
            ["shell", "settings", "put", "global", OTA_AUTO_SETTING, "1"],
            ["shell", "am", "force-stop", UPDATER_PACKAGE],
        )
    else:
        operations = (
            ["shell", "cmd", "package", "install-existing", "--user", "0", UPDATER_PACKAGE],
            ["shell", "pm", "default-state", "--user", "0", UPDATER_PACKAGE],
            ["shell", "settings", "put", "global", OTA_AUTO_SETTING, "0"],
        )

    for command in operations:
        changed = _run(runner, command, 45)
        if not changed.ok:
            return Result(False, f"System update change failed at: {' '.join(command[1:])}\n{changed.message}")

    if disabled:
        package_change = _run(
            runner,
            ["shell", "pm", "disable-user", "--user", "0", UPDATER_PACKAGE],
            45,
        )
        if not package_change.ok:
            package_change = _run(
                runner,
                ["shell", "pm", "uninstall", "--user", "0", UPDATER_PACKAGE],
                45,
            )
        if not package_change.ok:
            return Result(False, "Xiaomi blocked both reversible updater-disable methods.\n" + package_change.message)

    verified_result, state = read_system_update_state(runner=runner, ready_check=ready_check)
    if not verified_result.ok or state is None:
        return Result(False, "System update command ran, but verification failed.\n" + verified_result.message)
    expected = state.fully_disabled if disabled else state.fully_enabled
    if not expected:
        return Result(
            False,
            "Android did not reach the requested system-update state.\n" + state.summary(),
        )
    verb = "disabled" if disabled else "enabled"
    return Result(True, f"System updates are {verb} and verified.\n{state.summary()}")


def read_pending_system_update_request(runner: AdbRunner = run_tool) -> SystemUpdateRequest | None:
    logs = _run(runner, ["logcat", "-d", "-s", f"{UPDATE_CONTROL_TAG}:I", "*:S"], 15)
    if not logs.ok:
        return None
    acknowledged: set[str] = set()
    requests: list[SystemUpdateRequest] = []
    for line in logs.message.splitlines():
        result_match = _RESULT.search(line)
        if result_match:
            acknowledged.add(result_match.group(1))
        request_match = _REQUEST.search(line)
        if request_match:
            requests.append(SystemUpdateRequest(request_match.group(1), request_match.group(2)))
    for request in reversed(requests):
        if request.request_id not in acknowledged:
            return request
    return None


def acknowledge_system_update_request(
    request: SystemUpdateRequest,
    result: Result,
    runner: AdbRunner = run_tool,
) -> Result:
    state = ("DISABLED" if request.action == "DISABLE" else "ENABLED") if result.ok else "FAILED"
    safe_message = " ".join(result.message.split())[:300]
    encoded_message = base64.urlsafe_b64encode(safe_message.encode("utf-8")).decode("ascii").rstrip("=")
    acknowledged = _run(
        runner,
        [
            "shell",
            "am",
            "broadcast",
            "-n",
            UPDATE_CONTROL_RECEIVER,
            "--es",
            "request_id",
            request.request_id,
            "--es",
            "result_state",
            state,
            "--es",
            "result_message_b64",
            encoded_message,
        ],
        30,
    )
    if not acknowledged.ok:
        return Result(False, f"{result.message}\nPhone result acknowledgement failed: {acknowledged.message}")
    return result


def process_pending_system_update_request(runner: AdbRunner = run_tool) -> Result | None:
    request = read_pending_system_update_request(runner)
    if request is None:
        return None
    result = set_system_updates_disabled(
        request.action == "DISABLE",
        runner=runner,
        ready_check=lambda: Result(True, "Phone request already proved the ADB transport."),
    )
    return acknowledge_system_update_request(request, result, runner)
