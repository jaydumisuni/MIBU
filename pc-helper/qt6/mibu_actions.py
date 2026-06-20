from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

APP_PACKAGE = 'com.thetechguy.mibu'
APP_ENTRY = 'com.thetechguy.mibu/.MainActivity'


@dataclass
class Result:
    ok: bool
    message: str


def adb_path() -> str | None:
    found = shutil.which('adb')
    if found:
        return found
    local_names = ['adb.exe', 'adb']
    for item in local_names:
        path = os.path.join(os.getcwd(), 'platform-tools', item)
        if os.path.exists(path):
            return path
    return None


def run_tool(parts: list[str]) -> Result:
    tool = adb_path()
    if not tool:
        return Result(False, 'ADB not found. Install platform-tools or place platform-tools beside MIBU PC Helper.')
    try:
        proc = subprocess.run([tool] + parts, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        return Result(proc.returncode == 0, proc.stdout.strip())
    except Exception as exc:
        return Result(False, str(exc))


def list_devices() -> Result:
    return run_tool(['devices'])


def install_package(path: str) -> Result:
    if not os.path.exists(path):
        return Result(False, f'APK not found: {path}')
    return run_tool(['install', '-r', path])


def launch_phone_app() -> Result:
    return run_tool(['shell', 'monkey', '-p', APP_PACKAGE, '1'])
