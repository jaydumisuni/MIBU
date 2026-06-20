#!/usr/bin/env python3
"""MIBU PC Helper.

Phase 1:
- Check ADB devices.
- Install MIBU APK after ADB is enabled.
- Show the Beijing target window converted to the local PC timezone.

The credential handoff is documented for later implementation and should use a
secure, consent-based flow owned by the user.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

BEIJING_ZONE = ZoneInfo("Asia/Shanghai")
TARGET_TIME = time(23, 59, 58, 600000)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def find_adb() -> str:
    adb = shutil.which("adb")
    if adb:
        return adb
    for name in ("adb.exe", "adb"):
        path = os.path.join(os.getcwd(), "platform-tools", name)
        if os.path.exists(path):
            return path
    raise SystemExit("ADB not found. Install Android platform-tools or place adb in PATH.")


def next_beijing_window(now: datetime | None = None) -> datetime:
    now = now or datetime.now(BEIJING_ZONE)
    target = datetime.combine(now.date(), TARGET_TIME, tzinfo=BEIJING_ZONE)
    if target <= now:
        target += timedelta(days=1)
    return target


def print_window() -> None:
    target = next_beijing_window()
    local_target = target.astimezone()
    print("MIBU timing guide")
    print(f"Beijing target : {target:%Y-%m-%d %H:%M:%S.%f %Z}")
    print(f"Local target   : {local_target:%Y-%m-%d %H:%M:%S.%f %Z}")
    print("Keep internet stable at least 5 minutes before the local target time.")


def adb_devices(adb: str) -> None:
    print(run([adb, "devices"]).stdout)


def install_apk(adb: str, apk_path: str) -> None:
    if not os.path.exists(apk_path):
        raise SystemExit(f"APK not found: {apk_path}")
    result = run([adb, "install", "-r", apk_path])
    print(result.stdout)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="MIBU PC Helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("time", help="Show Beijing target converted to local time")
    sub.add_parser("devices", help="Show connected ADB devices")
    p_install = sub.add_parser("install", help="Install MIBU APK over ADB")
    p_install.add_argument("apk", help="Path to MIBU APK")
    args = parser.parse_args(argv)

    if args.cmd == "time":
        print_window()
        return 0

    adb = find_adb()
    if args.cmd == "devices":
        adb_devices(adb)
        return 0
    if args.cmd == "install":
        install_apk(adb, args.apk)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
