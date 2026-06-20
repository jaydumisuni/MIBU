#!/usr/bin/env python3
"""MIBU PC Helper.

This helper keeps the desktop side simple:
- guide the user to log in themselves through a normal browser
- check connected Android devices
- install MIBU.apk after ADB is enabled
- open the phone-side MIBU app
- show the Beijing target window converted to the local PC timezone
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

BEIJING_ZONE = ZoneInfo("Asia/Shanghai")
TARGET_TIME = time(23, 59, 58, 600000)
MIBU_PACKAGE = "com.thetechguy.mibu"
LOGIN_URL = "https://account.xiaomi.com/"


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


def open_login() -> None:
    print("Opening Xiaomi account login in your default browser...")
    print("Log in yourself. MIBU does not need or ask for your password.")
    webbrowser.open(LOGIN_URL)


def adb_devices(adb: str) -> None:
    print(run([adb, "devices"]).stdout)


def install_apk(adb: str, apk_path: str) -> None:
    if not os.path.exists(apk_path):
        raise SystemExit(f"APK not found: {apk_path}")
    result = run([adb, "install", "-r", apk_path])
    print(result.stdout)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def open_phone_app(adb: str) -> None:
    result = run([adb, "shell", "monkey", "-p", MIBU_PACKAGE, "1"])
    print(result.stdout)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="MIBU PC Helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="Open Xiaomi login in normal browser")
    sub.add_parser("time", help="Show Beijing target converted to local time")
    sub.add_parser("devices", help="Show connected ADB devices")
    p_install = sub.add_parser("install", help="Install MIBU APK over ADB")
    p_install.add_argument("apk", help="Path to MIBU APK")
    sub.add_parser("open", help="Open MIBU on the connected phone")
    args = parser.parse_args(argv)

    if args.cmd == "login":
        open_login()
        return 0
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
    if args.cmd == "open":
        open_phone_app(adb)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
