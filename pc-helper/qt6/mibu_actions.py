from __future__ import annotations

import base64
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

APP_PACKAGE = "com.thetechguy.mibu"
APP_ENTRY = "com.thetechguy.mibu/.MainActivity"
TOKEN_ENTRY = "com.thetechguy.mibu/.TokenImportActivity"
WAIT_ENTRY = "com.thetechguy.mibu/.StartWaitingActivity"
REMOTE_APK = "/sdcard/Download/MIBU.apk"
PROOF_NONCE_EXTRA = "mibu_proof_nonce"
EXPECTED_APP_VERSION = "0.2.0-dev"
MIN_TOKEN_LENGTH = 8
MAX_TOKEN_LENGTH = 8_192
_SELECTED_SERIAL: str | None = None


@dataclass
class Result:
    ok: bool
    message: str


def app_base_dir() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def _tool_candidates(name: str) -> list[Path]:
    base = app_base_dir()
    cwd = Path.cwd()
    exe = name + ".exe"
    return [
        base / "platform-tools" / exe,
        base / "platform-tools" / name,
        base / "_internal" / "platform-tools" / exe,
        base / "_internal" / "platform-tools" / name,
        cwd / "platform-tools" / exe,
        cwd / "platform-tools" / name,
        Path(f"D:/mibu-build-tools/android-sdk/platform-tools/{exe}"),
        Path(f"D:/mibu-build-tools/platform-tools/{exe}"),
    ]


def adb_path() -> str | None:
    env = os.environ.get("MIBU_ADB") or os.environ.get("ADB")
    candidates = [Path(env)] if env else []
    candidates.extend(_tool_candidates("adb"))
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("adb")


def fastboot_path() -> str | None:
    env = os.environ.get("MIBU_FASTBOOT") or os.environ.get("FASTBOOT")
    candidates = [Path(env)] if env else []
    candidates.extend(_tool_candidates("fastboot"))
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("fastboot")


def _targets_device(parts: list[str]) -> bool:
    if not parts:
        return False
    if "-s" in parts:
        return False
    return parts[0] not in {"devices", "version", "start-server", "kill-server", "reconnect"}


def run_tool(parts: list[str], timeout: int = 45) -> Result:
    tool = adb_path()
    if not tool:
        return Result(False, "ADB not found. Install platform-tools, set MIBU_ADB, or bundle platform-tools beside MIBU PC Helper.")
    command_parts = parts
    if _SELECTED_SERIAL and _targets_device(parts):
        command_parts = ["-s", _SELECTED_SERIAL] + parts
    try:
        proc = subprocess.run([tool] + command_parts, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return Result(proc.returncode == 0, proc.stdout.strip())
    except subprocess.TimeoutExpired as exc:
        return Result(False, f"ADB command timed out: {exc}")
    except Exception as exc:
        return Result(False, str(exc))


def run_fastboot(parts: list[str], timeout: int = 45) -> Result:
    tool = fastboot_path()
    if not tool:
        return Result(False, "fastboot not found. Install Android platform-tools, set MIBU_FASTBOOT, or bundle platform-tools beside MIBU PC Helper.")
    try:
        proc = subprocess.run([tool] + parts, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return Result(proc.returncode == 0, proc.stdout.strip())
    except subprocess.TimeoutExpired as exc:
        return Result(False, f"fastboot command timed out: {exc}")
    except Exception as exc:
        return Result(False, str(exc))


def list_devices() -> Result:
    return run_tool(["devices"])


def parse_devices(devices_output: str) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for line in devices_output.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] in {"device", "unauthorized", "offline", "recovery", "sideload", "bootloader"}:
            parsed.append((parts[0], parts[1]))
    return parsed


def parse_fastboot_devices(output: str) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("<") or line.startswith("(") or line.lower().startswith("waiting for"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].lower() in {"fastboot", "bootloader"}:
            parsed.append((parts[0], parts[1].lower()))
    return parsed


def parse_device_state(devices_output: str) -> tuple[str, str]:
    devices = parse_devices(devices_output)
    return devices[0] if devices else ("", "none")


def parse_package_version(dumpsys_output: str) -> str | None:
    match = re.search(r"^\s*versionName=([^\s]+)\s*$", dumpsys_output, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def check_device_ready() -> Result:
    global _SELECTED_SERIAL
    devices_result = list_devices()
    if not devices_result.ok:
        return devices_result
    devices = parse_devices(devices_result.message)
    if not devices:
        return Result(False, "No device detected. Connect USB cable, enable USB debugging, then accept the RSA prompt.")
    requested_serial = os.environ.get("MIBU_ADB_SERIAL", "").strip()
    if requested_serial:
        match = next(((serial, state) for serial, state in devices if serial == requested_serial), None)
        if not match:
            summary = ", ".join(f"{serial}:{state}" for serial, state in devices)
            return Result(False, f"MIBU_ADB_SERIAL={requested_serial} was requested, but connected devices are: {summary}")
        serial, state = match
    else:
        online = [(serial, state) for serial, state in devices if state == "device"]
        if len(online) == 1:
            serial, state = online[0]
        elif len(online) > 1:
            preferred: tuple[str, str] | None = None
            details: list[str] = []
            for candidate_serial, candidate_state in online:
                model = run_tool(["-s", candidate_serial, "shell", "getprop", "ro.product.model"], timeout=10)
                manufacturer = run_tool(["-s", candidate_serial, "shell", "getprop", "ro.product.manufacturer"], timeout=10)
                descriptor = f"{candidate_serial}:{candidate_state}:{manufacturer.message.strip()}:{model.message.strip()}"
                details.append(descriptor)
                lowered = descriptor.lower()
                if any(marker in lowered for marker in ("xiaomi", "redmi", "poco", "23076")):
                    preferred = (candidate_serial, candidate_state)
                    break
            if preferred:
                serial, state = preferred
            else:
                return Result(False, "Multiple online ADB devices are connected and no Xiaomi/Redmi/Poco phone could be selected automatically. Disconnect the extra device or set MIBU_ADB_SERIAL.\n" + "\n".join(details))
        elif len(devices) > 1:
            summary = ", ".join(f"{serial}:{state}" for serial, state in devices)
            return Result(False, f"Multiple ADB devices are connected ({summary}). Authorize the Xiaomi phone and retry.")
        else:
            serial, state = devices[0]
    if state == "unauthorized":
        return Result(False, f"Device {serial} is unauthorized. On the phone, tick ‘Always allow from this computer’ and tap OK.")
    if state == "offline":
        return Result(False, f"Device {serial} is offline. Reconnect cable or toggle USB debugging, then retry.")
    if state != "device":
        return Result(False, f"Device {serial} state is {state}. Return Android to normal online ADB mode before continuing.")
    adb_state = run_tool(["-s", serial, "shell", "settings", "get", "global", "adb_enabled"])
    adb_value = adb_state.message.strip() if adb_state.ok else "unknown"
    if adb_value != "1":
        return Result(False, f"Device {serial} is visible but Android reports adb_enabled={adb_value}. Re-enable USB debugging and retry.")
    _SELECTED_SERIAL = serial
    return Result(True, f"Device online: {serial}\nADB state: {adb_value}")


def run_adb_user_command(command: str) -> Result:
    raw = command.strip()
    if not raw:
        return Result(False, "Type an ADB command first, for example: shell getprop ro.product.model")
    try:
        parts = shlex.split(raw, posix=False)
    except ValueError as exc:
        return Result(False, f"Command parse failed: {exc}")
    if parts and Path(parts[0]).name.lower() in {"adb", "adb.exe"}:
        parts = parts[1:]
    if not parts:
        return Result(False, "No ADB arguments were provided.")
    if _targets_device(parts):
        ready = check_device_ready()
        if not ready.ok:
            return ready
    return run_tool(parts, timeout=120)


def package_exists() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(["shell", "pm", "path", APP_PACKAGE])
    if result.ok and result.message.startswith("package:"):
        return Result(True, result.message)
    return Result(False, "MIBU app is not installed on the connected phone.")


def installed_package_version() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(["shell", "dumpsys", "package", APP_PACKAGE], timeout=30)
    if not result.ok:
        return Result(False, result.message or "Could not read the installed MIBU package version.")
    version = parse_package_version(result.message)
    if not version:
        return Result(False, "MIBU package is not installed or Android did not return versionName.")
    return Result(True, version)


def _open_system_installer(path: str) -> Result:
    pushed = run_tool(["push", path, REMOTE_APK], timeout=120)
    if not pushed.ok:
        return Result(False, f"Direct install failed and APK push also failed.\n{pushed.message}")
    opened = run_tool([
        "shell", "am", "start", "-W",
        "-a", "android.intent.action.VIEW",
        "-d", f"file://{REMOTE_APK}",
        "-t", "application/vnd.android.package-archive",
        "--grant-read-uri-permission",
    ], timeout=30)
    if opened.ok:
        return Result(False, "Android/MIUI blocked silent ADB install, so MIBU opened the phone's system installer. Complete installation on the phone, then press Install APK again. MIBU will reinstall the bundled APK and verify its version before reporting success.")
    return Result(False, f"Direct install failed. APK was copied to {REMOTE_APK}, but the system installer could not be opened automatically. Open Downloads on the phone and install MIBU.apk manually.\n{opened.message}")


def install_package(path: str) -> Result:
    if not os.path.isfile(path):
        return Result(False, f"APK not found: {path}")
    ready = check_device_ready()
    if not ready.ok:
        return ready

    installed_before = installed_package_version()
    result = run_tool(["install", "-r", path], timeout=120)
    if not (result.ok and "Success" in result.message):
        fallback = _open_system_installer(path)
        previous = f" Installed version before attempt: {installed_before.message}." if installed_before.ok else ""
        return Result(False, f"Direct ADB install/reinstall did not complete.{previous}\n{result.message or 'No install output.'}\n\n{fallback.message}")

    verified = installed_package_version()
    if not verified.ok:
        return Result(False, f"ADB reported install success, but installed-version verification failed: {verified.message}")
    if verified.message != EXPECTED_APP_VERSION:
        return Result(False, f"ADB installed a MIBU package, but version verification returned {verified.message}; expected {EXPECTED_APP_VERSION}.")
    previous = installed_before.message if installed_before.ok else "not installed"
    return Result(True, f"Bundled MIBU {EXPECTED_APP_VERSION} installed/reinstalled and version verified. Previous state: {previous}.")


def launch_phone_app() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    installed = package_exists()
    if not installed.ok:
        return installed
    result = run_tool(["shell", "am", "start", "-W", "-n", APP_ENTRY], timeout=30)
    if result.ok and ("Status: ok" in result.message or "Activity:" in result.message):
        return Result(True, result.message)
    return Result(False, result.message or "Android did not confirm that MIBU opened.")


def launch_token_import() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    installed = package_exists()
    if not installed.ok:
        return installed
    result = run_tool(["shell", "am", "start", "-W", "-n", TOKEN_ENTRY], timeout=30)
    if result.ok and ("Status: ok" in result.message or "Activity:" in result.message):
        return Result(True, result.message)
    return Result(False, result.message or "Android did not confirm that the MIBU token import screen opened.")


def _valid_token(value: str) -> bool:
    clean = _compact_token(value)
    return MIN_TOKEN_LENGTH <= len(clean) <= MAX_TOKEN_LENGTH and not any(ord(char) < 32 or ord(char) == 127 for char in clean)


def _compact_token(value: str) -> str:
    return "".join(value.strip().split())


def _encode_token(value: str) -> str:
    return base64.urlsafe_b64encode(_compact_token(value).encode("utf-8")).decode("ascii")


def _proof_nonce() -> str:
    return secrets.token_urlsafe(12)


def _wait_for_log_outcome(
    tag: str,
    success_marker: str | tuple[str, ...],
    failure_markers: tuple[str, ...] = (),
    wait_seconds: int = 6,
    nonce: str | None = None,
) -> Result:
    success_markers = (success_marker,) if isinstance(success_marker, str) else success_marker
    deadline = time.monotonic() + max(1, wait_seconds)
    last = ""
    nonce_marker = f"nonce={nonce}" if nonce else None
    while time.monotonic() < deadline:
        logs = run_tool(["logcat", "-d", "-s", f"{tag}:V", "*:S"], timeout=10)
        last = logs.message
        if logs.ok:
            matching_lines = [
                line for line in logs.message.splitlines()
                if nonce_marker is None or nonce_marker in line
            ]
            matching_text = "\n".join(matching_lines)
            for failure_marker in failure_markers:
                if failure_marker in matching_text:
                    return Result(False, f"Android reported failure marker: {failure_marker}\n{matching_text}")
            for marker in success_markers:
                if marker in matching_text:
                    detail = f" with nonce {nonce}" if nonce else ""
                    return Result(True, f"Android proof marker confirmed: {marker}{detail}")
        time.sleep(0.35)
    expected = " or ".join(success_markers)
    nonce_detail = f" for nonce {nonce}" if nonce else ""
    return Result(False, f"Android did not emit proof marker {expected}{nonce_detail}. Last filtered log: {last or 'none'}")


def _wait_for_log_marker(tag: str, marker: str, wait_seconds: int = 6, nonce: str | None = None) -> Result:
    return _wait_for_log_outcome(tag, marker, wait_seconds=wait_seconds, nonce=nonce)


def push_session_to_phone(token: str) -> Result:
    token = _compact_token(token)
    if not _valid_token(token):
        return Result(False, f"Token/session must be {MIN_TOKEN_LENGTH}-{MAX_TOKEN_LENGTH} characters with no control characters.")
    ready = check_device_ready()
    if not ready.ok:
        return ready
    nonce = _proof_nonce()
    started = run_tool([
        "shell", "am", "start", "-W", "-n", TOKEN_ENTRY,
        "--es", "mibu_session_token_b64", _encode_token(token),
        "--es", PROOF_NONCE_EXTRA, nonce,
    ], timeout=30)
    if not started.ok:
        return started
    marker = _wait_for_log_marker("MIBU_IMPORT", "SERVICE_CAPTURE_IMPORTED", nonce=nonce)
    return marker if marker.ok else Result(False, f"Token import activity opened, but import was not proven.\n{marker.message}")


def push_two_tokens_to_phone(service_token: str, pop_token: str) -> Result:
    service_token = _compact_token(service_token)
    pop_token = _compact_token(pop_token)
    if not _valid_token(service_token):
        return Result(False, f"Firefox/service token must be {MIN_TOKEN_LENGTH}-{MAX_TOKEN_LENGTH} characters with no control characters.")
    if not _valid_token(pop_token):
        return Result(False, f"Chrome/pop token must be {MIN_TOKEN_LENGTH}-{MAX_TOKEN_LENGTH} characters with no control characters.")
    ready = check_device_ready()
    if not ready.ok:
        return ready
    nonce = _proof_nonce()
    started = run_tool([
        "shell", "am", "start", "-W", "-n", TOKEN_ENTRY,
        "--es", "mibu_service_token_b64", _encode_token(service_token),
        "--es", "mibu_pop_token_b64", _encode_token(pop_token),
        "--es", PROOF_NONCE_EXTRA, nonce,
    ], timeout=30)
    if not started.ok:
        return started
    marker = _wait_for_log_marker("MIBU_IMPORT", "TWO_CAPTURES_IMPORTED", nonce=nonce)
    return marker if marker.ok else Result(False, f"Token import activity opened, but two-capture import was not proven.\n{marker.message}")


def start_phone_waiting() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    nonce = _proof_nonce()
    started = run_tool([
        "shell", "am", "start", "-W", "-n", WAIT_ENTRY,
        "--es", PROOF_NONCE_EXTRA, nonce,
    ], timeout=30)
    if not started.ok:
        return started
    proof = _wait_for_log_outcome(
        "MIBU_SERVICE",
        (
            "WAITING_SERVICE_ARMED",
            "WAITING_SERVICE_RECOVERED_COMPLETE",
            "WAITING_SERVICE_COMPLETE",
        ),
        failure_markers=(
            "WAITING_SERVICE_REJECTED_MISSING_CAPTURES",
            "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY",
            "WAITING_SERVICE_FAILED",
            "WAITING_SERVICE_NOT_NEEDED",
        ),
        wait_seconds=10,
        nonce=nonce,
    )
    return proof if proof.ok else Result(False, f"Waiting activity opened, but the foreground service was not proven armed or complete.\n{proof.message}")


def reboot_to_fastboot() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(["reboot", "bootloader"], timeout=30)
    return Result(result.ok, result.message or ("Reboot command accepted." if result.ok else "Reboot command failed."))


def check_fastboot_ready(wait_seconds: int = 30) -> Result:
    deadline = time.monotonic() + max(0, wait_seconds)
    last_message = ""
    while True:
        result = run_fastboot(["devices"], timeout=10)
        last_message = result.message
        devices = parse_fastboot_devices(result.message) if result.ok else []
        if len(devices) == 1:
            serial, state = devices[0]
            return Result(True, f"Fastboot device detected:\n{serial}\t{state}")
        if len(devices) > 1:
            summary = "\n".join(f"{serial}\t{state}" for serial, state in devices)
            return Result(False, "Multiple fastboot devices are connected. Leave only the phone being serviced connected, then retry.\n" + summary)
        if time.monotonic() >= deadline:
            break
        time.sleep(1)
    suffix = f" Last fastboot output: {last_message}" if last_message else ""
    return Result(False, "No fastboot device detected within the wait window. Check cable/driver and retry." + suffix)


def fastboot_oem_info() -> Result:
    info = run_fastboot(["oem", "device-info"], timeout=30)
    if info.ok and info.message:
        return info
    fallback = run_fastboot(["getvar", "unlocked"], timeout=30)
    if fallback.ok or fallback.message:
        return fallback
    return Result(False, "Fastboot responded, but no device-info/unlocked value was returned.")
