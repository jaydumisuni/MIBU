from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dependency_check import browser_path


BEIJING_ZONE = ZoneInfo("Asia/Shanghai")
TARGET_TIME = time(23, 59, 58, 600000)
LOGIN_URL = "https://account.xiaomi.com/"
WINGET_BROWSER_IDS = {"chrome": "Google.Chrome", "firefox": "Mozilla.Firefox"}


def app_base_dir() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def asset_roots() -> list[Path]:
    base = app_base_dir()
    cwd = Path.cwd()
    candidates = [base, cwd, base.parent, base.parent.parent, cwd.parent, cwd.parent.parent]
    roots: list[Path] = []
    for candidate in candidates:
        if candidate not in roots:
            roots.append(candidate)
    expanded: list[Path] = []
    for root in roots:
        expanded.extend(
            [
                root,
                root / "dist",
                root / "resources",
                root / "resources" / "live_ui",
                root / "_internal",
                root / "_internal" / "dist",
                root / "_internal" / "resources",
                root / "_internal" / "resources" / "live_ui",
            ]
        )
    return expanded


def find_asset(*names: str) -> str:
    for root in asset_roots():
        for name in names:
            candidate = root / name
            if candidate.is_file():
                return str(candidate)
    return ""


def open_or_install_browser(key: str, url: str = LOGIN_URL) -> str:
    path = browser_path(key)
    if path:
        subprocess.Popen(
            [path, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return f"{key.title()} opened."

    package_id = WINGET_BROWSER_IDS.get(key)
    winget = shutil.which("winget")
    if package_id and winget:
        subprocess.Popen(
            [
                winget,
                "install",
                "-e",
                "--id",
                package_id,
                "--accept-source-agreements",
                "--accept-package-agreements",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return f"{key.title()} was not detected. Its winget installation has started."

    webbrowser.open(url)
    return f"{key.title()} is unavailable, so the default browser opened instead."


def next_target(now: datetime | None = None) -> datetime:
    current = now.astimezone(BEIJING_ZONE) if now else datetime.now(BEIJING_ZONE)
    target = datetime.combine(current.date(), TARGET_TIME, tzinfo=BEIJING_ZONE)
    return target if target > current else target + timedelta(days=1)


@dataclass
class AppState:
    device_ok: bool = False
    apk_ok: bool = False
    tokens_ok: bool = False
    fastboot_ok: bool = False
