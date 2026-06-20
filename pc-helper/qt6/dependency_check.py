from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str


def python_check() -> CheckItem:
    version = sys.version_info
    ok = version.major == 3 and version.minor >= 10
    return CheckItem('Python 3.10+', ok, platform.python_version())


def pyside_check() -> CheckItem:
    spec = importlib.util.find_spec('PySide6')
    return CheckItem('PySide6 / Qt6', spec is not None, 'installed' if spec else 'missing')


def adb_check() -> CheckItem:
    adb = shutil.which('adb')
    if adb:
        try:
            proc = subprocess.run([adb, 'version'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
            first = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else adb
            return CheckItem('ADB platform-tools', proc.returncode == 0, first)
        except Exception as exc:
            return CheckItem('ADB platform-tools', False, str(exc))
    return CheckItem('ADB platform-tools', False, 'missing from PATH')


def run_all_checks() -> list[CheckItem]:
    return [python_check(), pyside_check(), adb_check()]


def format_checks(items: list[CheckItem]) -> str:
    lines = []
    for item in items:
        mark = 'OK' if item.ok else 'MISSING'
        lines.append(f'{mark:8} {item.name}: {item.detail}')
    return '\n'.join(lines)


if __name__ == '__main__':
    checks = run_all_checks()
    print(format_checks(checks))
    raise SystemExit(0 if all(item.ok for item in checks) else 1)
