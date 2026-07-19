from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from mibu_actions import adb_path, fastboot_path


@dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str


def python_check() -> CheckItem:
    version = sys.version_info
    ok = version.major == 3 and version.minor >= 10
    return CheckItem("Python 3.10+", ok, platform.python_version())


def pyside_check() -> CheckItem:
    spec = importlib.util.find_spec("PySide6")
    return CheckItem("PySide6 / Qt6", spec is not None, "installed" if spec else "missing")


def executable_check(name: str, executable: str | None, version_args: list[str]) -> CheckItem:
    if not executable:
        return CheckItem(name, False, "not found in MIBU bundle, configured path, or PATH")
    try:
        proc = subprocess.run([executable] + version_args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        output = proc.stdout.strip()
        first = output.splitlines()[0] if output else executable
        return CheckItem(name, proc.returncode == 0, f"{first} [{executable}]")
    except Exception as exc:
        return CheckItem(name, False, f"{exc} [{executable}]")


def adb_check() -> CheckItem:
    return executable_check("ADB platform-tools", adb_path(), ["version"])


def fastboot_check() -> CheckItem:
    return executable_check("Fastboot platform-tools", fastboot_path(), ["--version"])


def _browser_candidates(name: str) -> list[Path]:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = [Path(os.environ.get("PROGRAMFILES", "")), Path(os.environ.get("PROGRAMFILES(X86)", ""))]
    if name == "chrome":
        return [
            local / "Google" / "Chrome" / "Application" / "chrome.exe",
            *(root / "Google" / "Chrome" / "Application" / "chrome.exe" for root in program_files),
            Path(shutil.which("chrome") or ""),
            Path(shutil.which("chrome.exe") or ""),
        ]
    if name == "firefox":
        return [
            *(root / "Mozilla Firefox" / "firefox.exe" for root in program_files),
            local / "Mozilla Firefox" / "firefox.exe",
            Path(shutil.which("firefox") or ""),
            Path(shutil.which("firefox.exe") or ""),
        ]
    return []


def browser_path(name: str) -> str | None:
    for candidate in _browser_candidates(name):
        if str(candidate) and candidate.is_file():
            return str(candidate)
    return None


def browser_check(display: str, key: str) -> CheckItem:
    path = browser_path(key)
    return CheckItem(display, path is not None, path or "not installed/detected")


def run_all_checks() -> list[CheckItem]:
    return [
        python_check(),
        pyside_check(),
        adb_check(),
        fastboot_check(),
        browser_check("Chrome browser", "chrome"),
        browser_check("Firefox browser", "firefox"),
    ]


def format_checks(items: list[CheckItem]) -> str:
    lines = []
    for item in items:
        mark = "OK" if item.ok else "MISSING"
        lines.append(f"{mark:8} {item.name}: {item.detail}")
    return "\n".join(lines)


if __name__ == "__main__":
    checks = run_all_checks()
    print(format_checks(checks))
    raise SystemExit(0 if all(item.ok for item in checks) else 1)
