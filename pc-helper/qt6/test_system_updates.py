from __future__ import annotations

from mibu_actions import Result
from mibu_system_updates import (
    OTA_AUTO_SETTING,
    UPDATER_PACKAGE,
    read_pending_system_update_request,
    read_system_update_state,
    set_system_updates_disabled,
)


class FakeAdb:
    def __init__(self, protect_disable: bool = False) -> None:
        self.enabled = True
        self.auto_disabled = False
        self.protect_disable = protect_disable
        self.available = True
        self.logs = ""
        self.commands: list[list[str]] = []

    def __call__(self, parts: list[str], timeout: int) -> Result:
        self.commands.append(parts.copy())
        if parts[:5] == ["shell", "pm", "list", "packages", "-e"]:
            return Result(True, f"package:{UPDATER_PACKAGE}" if self.enabled else "")
        if parts[:5] == ["shell", "pm", "list", "packages", "-d"]:
            return Result(True, "" if self.enabled else f"package:{UPDATER_PACKAGE}")
        if parts[:5] == ["shell", "pm", "list", "packages", "-u"]:
            return Result(True, f"package:{UPDATER_PACKAGE}" if self.available else "")
        if parts[:5] == ["shell", "settings", "get", "global", OTA_AUTO_SETTING]:
            return Result(True, "1" if self.auto_disabled else "0")
        if parts[:5] == ["shell", "settings", "put", "global", OTA_AUTO_SETTING]:
            self.auto_disabled = parts[5] == "1"
            return Result(True, "")
        if parts[:3] == ["shell", "pm", "disable-user"]:
            if self.protect_disable:
                return Result(False, "Cannot disable system packages")
            self.enabled = False
            return Result(True, "new state: disabled-user")
        if parts[:3] == ["shell", "pm", "uninstall"]:
            self.enabled = False
            return Result(True, "Success")
        if parts[:4] == ["shell", "cmd", "package", "install-existing"]:
            self.enabled = True
            return Result(True, f"Package {UPDATER_PACKAGE} installed for user: 0")
        if parts[:3] == ["shell", "pm", "default-state"]:
            self.enabled = True
            return Result(True, "new state: default")
        if parts[:3] == ["shell", "am", "force-stop"]:
            return Result(True, "")
        if parts[:2] == ["logcat", "-d"]:
            return Result(True, self.logs)
        if parts[:3] == ["shell", "am", "broadcast"]:
            return Result(True, "Broadcast completed: result=0")
        return Result(False, "Unexpected command: " + " ".join(parts))


def ready() -> Result:
    return Result(True, "ready")


def test_disable_and_enable_are_both_verified() -> None:
    adb = FakeAdb(protect_disable=True)
    disabled = set_system_updates_disabled(True, runner=adb, ready_check=ready)
    assert disabled.ok
    assert adb.auto_disabled
    assert not adb.enabled
    enabled = set_system_updates_disabled(False, runner=adb, ready_check=ready)
    assert enabled.ok
    assert not adb.auto_disabled
    assert adb.enabled
    assert any(parts[:3] == ["shell", "pm", "uninstall"] for parts in adb.commands)
    assert any(parts[:4] == ["shell", "cmd", "package", "install-existing"] for parts in adb.commands)


def test_state_requires_package_and_automatic_flag_for_fully_disabled() -> None:
    adb = FakeAdb()
    adb.enabled = False
    adb.auto_disabled = True
    result, state = read_system_update_state(runner=adb, ready_check=ready)
    assert result.ok
    assert state is not None and state.fully_disabled


def test_disable_is_idempotent_after_protected_package_user_removal() -> None:
    adb = FakeAdb(protect_disable=True)
    adb.enabled = False
    adb.auto_disabled = True
    result = set_system_updates_disabled(True, runner=adb, ready_check=ready)
    assert result.ok
    assert not any(parts[:3] == ["shell", "pm", "uninstall"] for parts in adb.commands)


def test_pending_request_ignores_acknowledged_request() -> None:
    adb = FakeAdb()
    adb.logs = "\n".join(
        (
            "I/MIBU_UPDATE_CONTROL: UPDATE_REQUEST id=first-1 action=DISABLE",
            "I/MIBU_UPDATE_CONTROL: UPDATE_RESULT id=first-1 state=DISABLED accepted=true",
            "I/MIBU_UPDATE_CONTROL: UPDATE_REQUEST id=second-2 action=ENABLE",
        )
    )
    request = read_pending_system_update_request(adb)
    assert request is not None
    assert request.request_id == "second-2"
    assert request.action == "ENABLE"
