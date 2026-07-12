from __future__ import annotations

import base64
import os
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


def run_tool(parts: list[str], timeout: int = 45) -> Result:
    tool = adb_path()
    if not tool:
        return Result(False, "ADB not found. Install platform-tools, set MIBU_ADB, or bundle platform-tools beside MIBU PC Helper.")
    try:
        proc = subprocess.run([tool] + parts, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
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
        if len(parts) >= 2:
            parsed.append((parts[0], parts[1]))
    return parsed


def parse_device_state(devices_output: str) -> tuple[str, str]:
    devices = parse_devices(devices_output)
    return devices[0] if devices else ("", "none")


def check_device_ready() -> Result:
    devices_result = list_devices()
    if not devices_result.ok:
        return devices_result
    devices = parse_devices(devices_result.message)
    if not devices:
        return Result(False, "No device detected. Connect USB cable, enable USB debugging, then accept the RSA prompt.")
    if len(devices) > 1:
        summary = ", ".join(f"{serial}:{state}" for serial, state in devices)
        return Result(False, f"Multiple ADB devices are connected ({summary}). Leave only the phone being serviced connected, then retry.")
    serial, state = devices[0]
    if state == "unauthorized":
        return Result(False, f"Device {serial} is unauthorized. On the phone, tick ‘Always allow from this computer’ and tap OK.")
    if state == "offline":
        return Result(False, f"Device {serial} is offline. Reconnect cable or toggle USB debugging, then retry.")
    if state != "device":
        return Result(False, f"Device {serial} state is {state}. Wait for it to become online/device.")
    adb_state = run_tool(["-s", serial, "shell", "settings", "get", "global", "adb_enabled"])
    adb_value = adb_state.message.strip() if adb_state.ok else "unknown"
    if adb_value != "1":
        return Result(False, f"Device {serial} is visible but Android reports adb_enabled={adb_value}. Re-enable USB debugging and retry.")
    return Result(True, f"Device online: {serial}\nADB state: {adb_value}")


def package_exists() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(["shell", "pm", "path", APP_PACKAGE])
    if result.ok and result.message.startswith("package:"):
        return Result(True, result.message)
    return Result(False, "MIBU app is not installed on the connected phone.")


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
        return Result(False, "Android/MIUI blocked silent ADB install, so MIBU opened the phone's system installer. Complete installation on the phone, then press Install APK again to verify the package.")
    return Result(False, f"Direct install failed. APK was copied to {REMOTE_APK}, but the system installer could not be opened automatically. Open Downloads on the phone and install MIBU.apk manually.\n{opened.message}")


def install_package(path: str) -> Result:
    if not os.path.isfile(path):
        return Result(False, f"APK not found: {path}")
    ready = check_device_ready()
    if not ready.ok:
        return ready
    already = package_exists()
    if already.ok:
        return Result(True, f"MIBU is already installed and package verification passed.\n{already.message}")
    result = run_tool(["install", "-r", path], timeout=120)
    if not (result.ok and "Success" in result.message):
        fallback = _open_system_installer(path)
        return Result(False, f"Direct ADB install did not complete.\n{result.message or 'No install output.'}\n\n{fallback.message}")
    verified = package_exists()
    if not verified.ok:
        return Result(False, f"ADB reported install success, but package verification failed: {verified.message}")
    return Result(True, f"APK installed and package verified.\n{verified.message}")


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


def _encode_token(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")


def _clear_logcat() -> None:
    run_tool(["logcat", "-c"], timeout=10)


def _wait_for_log_outcome(
    tag: str,
    success_marker: str,
    failure_markers: tuple[str, ...] = (),
    wait_seconds: int = 6,
) -> Result:
    deadline = time.monotonic() + max(1, wait_seconds)
    last = ""
    while time.monotonic() < deadline:
        logs = run_tool(["logcat", "-d", "-s", f"{tag}:I", "*:S"], timeout=10)
        last = logs.message
        if logs.ok:
            for failure_marker in failure_markers:
                if failure_marker in logs.message:
                    return Result(False, f"Android reported failure marker: {failure_marker}\n{logs.message}")
            if success_marker in logs.message:
                return Result(True, f"Android proof marker confirmed: {success_marker}")
        time.sleep(0.35)
    return Result(False, f"Android did not emit proof marker {success_marker}. Last filtered log: {last or 'none'}")


def _wait_for_log_marker(tag: str, marker: str, wait_seconds: int = 6) -> Result:
    return _wait_for_log_outcome(tag, marker, wait_seconds=wait_seconds)


def push_session_to_phone(token: str) -> Result:
    token = token.strip()
    if len(token) < 8:
        return Result(False, "Token/session looks too short.")
    ready = check_device_ready()
    if not ready.ok:
        return ready
    _clear_logcat()
    started = run_tool([
        "shell", "am", "start", "-W", "-n", TOKEN_ENTRY,
        "--es", "mibu_session_token_b64", _encode_token(token),
    ], timeout=30)
    if not started.ok:
        return started
    marker = _wait_for_log_marker("MIBU_IMPORT", "SERVICE_CAPTURE_IMPORTED")
    return marker if marker.ok else Result(False, f"Token import activity opened, but import was not proven.\n{marker.message}")


def push_two_tokens_to_phone(service_token: str, pop_token: str) -> Result:
    service_token = service_token.strip()
    pop_token = pop_token.strip()
    if len(service_token) < 8:
        return Result(False, "Firefox/service token looks too short.")
    if len(pop_token) < 8:
        return Result(False, "Chrome/pop token looks too short.")
    ready = check_device_ready()
    if not ready.ok:
        return ready
    _clear_logcat()
    started = run_tool([
        "shell", "am", "start", "-W", "-n", TOKEN_ENTRY,
        "--es", "mibu_service_token_b64", _encode_token(service_token),
        "--es", "mibu_pop_token_b64", _encode_token(pop_token),
    ], timeout=30)
    if not started.ok:
        return started
    marker = _wait_for_log_marker("MIBU_IMPORT", "TWO_CAPTURES_IMPORTED")
    return marker if marker.ok else Result(False, f"Token import activity opened, but two-capture import was not proven.\n{marker.message}")


def start_phone_waiting() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    _clear_logcat()
    started = run_tool(["shell", "am", "start", "-W", "-n", WAIT_ENTRY], timeout=30)
    if not started.ok:
        return started
    proof = _wait_for_log_outcome(
        "MIBU_SERVICE",
        "WAITING_SERVICE_ARMED",
        failure_markers=(
            "WAITING_SERVICE_REJECTED_MISSING_CAPTURES",
            "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY",
            "WAITING_SERVICE_FAILED",
        ),
        wait_seconds=10,
    )
    return proof if proof.ok else Result(False, f"Waiting activity opened, but the foreground service was not proven armed.\n{proof.message}")


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
        lines = [line.strip() for line in result.message.splitlines() if line.strip()] if result.ok else []
        if len(lines) == 1:
            return Result(True, "Fastboot device detected:\n" + lines[0])
        if len(lines) > 1:
            return Result(False, "Multiple fastboot devices are connected. Leave only the phone being serviced connected, then retry.\n" + result.message)
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
