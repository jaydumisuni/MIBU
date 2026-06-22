from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

APP_PACKAGE = 'com.thetechguy.mibu'
APP_ENTRY = 'com.thetechguy.mibu/.MainActivity'
TOKEN_ENTRY = 'com.thetechguy.mibu/.TokenImportActivity'
WAIT_ENTRY = 'com.thetechguy.mibu/.StartWaitingActivity'


@dataclass
class Result:
    ok: bool
    message: str


def app_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def adb_path() -> str | None:
    env = os.environ.get('MIBU_ADB') or os.environ.get('ADB')
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env))
    base = app_base_dir()
    cwd = Path.cwd()
    candidates.extend([
        base / 'platform-tools' / 'adb.exe',
        base / 'platform-tools' / 'adb',
        base / '_internal' / 'platform-tools' / 'adb.exe',
        base / '_internal' / 'platform-tools' / 'adb',
        cwd / 'platform-tools' / 'adb.exe',
        cwd / 'platform-tools' / 'adb',
        Path('D:/mibu-build-tools/android-sdk/platform-tools/adb.exe'),
        Path('D:/mibu-build-tools/platform-tools/adb.exe'),
    ])
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    found = shutil.which('adb')
    return found


def run_tool(parts: list[str], timeout: int = 45) -> Result:
    tool = adb_path()
    if not tool:
        return Result(False, 'ADB not found. Install platform-tools, set MIBU_ADB, or bundle platform-tools beside MIBU PC Helper.')
    try:
        proc = subprocess.run([tool] + parts, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return Result(proc.returncode == 0, proc.stdout.strip())
    except subprocess.TimeoutExpired as exc:
        return Result(False, f'ADB command timed out: {exc}')
    except Exception as exc:
        return Result(False, str(exc))


def list_devices() -> Result:
    return run_tool(['devices'])


def parse_device_state(devices_output: str) -> tuple[str, str]:
    for line in devices_output.splitlines():
        line = line.strip()
        if not line or line.lower().startswith('list of devices'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            return parts[0], parts[1]
    return '', 'none'


def check_device_ready() -> Result:
    devices = list_devices()
    if not devices.ok:
        return devices
    serial, state = parse_device_state(devices.message)
    if not serial:
        return Result(False, 'No device detected. Connect USB cable, enable USB debugging, then accept the RSA prompt.')
    if state == 'unauthorized':
        return Result(False, f'Device {serial} is unauthorized. On the phone, tick “Always allow from this computer” and tap OK.')
    if state == 'offline':
        return Result(False, f'Device {serial} is offline. Reconnect cable or toggle USB debugging, then retry.')
    if state != 'device':
        return Result(False, f'Device {serial} state is {state}. Wait for it to become online/device.')

    adb_state = run_tool(['shell', 'settings', 'get', 'global', 'adb_enabled'])
    adb_value = adb_state.message.strip() if adb_state.ok else 'unknown'
    return Result(True, f'Device online: {serial}\nADB state: {adb_value}\n{devices.message}')


def install_package(path: str) -> Result:
    if not os.path.exists(path):
        return Result(False, f'APK not found: {path}')
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(['install', '-r', path], timeout=120)
    if result.ok and 'Success' in result.message:
        return Result(True, result.message)
    return result


def launch_phone_app() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    return run_tool(['shell', 'monkey', '-p', APP_PACKAGE, '1'])


def push_session_to_phone(token: str) -> Result:
    token = token.strip()
    if len(token) < 8:
        return Result(False, 'Token/session looks too short.')
    ready = check_device_ready()
    if not ready.ok:
        return ready
    return run_tool(['shell', 'am', 'start', '-n', TOKEN_ENTRY, '--es', 'mibu_session_token', token], timeout=30)


def start_phone_waiting() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    return run_tool(['shell', 'am', 'start', '-n', WAIT_ENTRY], timeout=30)


def package_exists() -> Result:
    ready = check_device_ready()
    if not ready.ok:
        return ready
    result = run_tool(['shell', 'pm', 'path', APP_PACKAGE])
    if result.ok and result.message:
        return Result(True, result.message)
    return Result(False, 'MIBU app is not installed on the connected phone.')
