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


def parse_device_state(devices_output: str) -> tuple[str, str]:
    for line in devices_output.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            return parts[0], parts[1]
    return "", "none"


def check_device_ready() -> Result:
    devices = list_devices()
    if not devices.ok:
        return devices
    serial, state = parse_device_state(devices.message)
    if not serial:
        return Result(False, "No device detected. Connect USB cable, enable USB debugging, then accept the RSA prompt.")
    if state == "unauthorized":
        return Result(False, f"Device {serial} is unauthorized. On the phone, tick ‘Always allow from this computer’ and tap OK.")
    if state == "offline":
        return Result(False, f"Device {serial} is offline. Reconnect cable or toggle USB debugging, then retry.")
    if state != "device":
        return Result(False, f"Device {serial} state is {state}. Wait for it to become online/device.")
    adb_state = run_tool(["shell", "settings", "get", "global", "adb_enabled"])
    adb_value = adb_state.message.strip() if adb_state.ok else "unknown"
    return Result(True, f"Device online: {serial}\nADB state: {adb_value}\n{devices.message}")


def package_exists() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(["shell", "pm", "path", APP_PACKAGE])
    if result.ok and result.message.startswith("package:"):
        return Result(True, result.message)
    return Result(False, "MIBU app is not installed on the connected phone.")


def install_package(path: str) -> Result:
    if not os.path.isfile(path):
        return Result(False, f"APK not found: {path}")
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(["install", "-r", path], timeout=120)
    if not (result.ok and "Success" in result.message):
        return Result(False, result.message or "ADB install did not report Success.")
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


def _wait_for_log_marker(tag: str, marker: str, wait_seconds: int = 6) -> Result:
    deadline = time.monotonic() + max(1, wait_seconds)
    last = ""
    while time.monotonic() < deadline:
        logs = run_tool(["logcat", "-d", "-s", f"{tag}:I", "*:S"], timeout=10)
        last = logs.message
        if logs.ok and marker in logs.message:
            return Result(True, f"Android proof marker confirmed: {marker}")
        time.sleep(0.35)
    return Result(False, f"Android did not emit proof marker {marker}. Last filtered log: {last or 'none'}")


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
    marker = _wait_for_log_marker("MIBU_WAIT", "WAITING_ACTIVITY_STARTED")
    return marker if marker.ok else Result(False, f"Waiting activity opened, but waiting was not proven armed.\n{marker.message}")


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
        if lines:
            return Result(True, "Fastboot device detected:\n" + result.message)
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
