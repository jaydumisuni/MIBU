from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dependency_check import browser_path


BEIJING_ZONE = ZoneInfo("Asia/Shanghai")
TARGET_TIME = time(23, 59, 58, 600000)
LOGIN_URL = "https://account.xiaomi.com/"
WINGET_BROWSER_IDS = {"chrome": "Google.Chrome", "firefox": "Mozilla.Firefox"}


def classify_assistant_intent(message: str) -> str:
    clean = " ".join(message.lower().split()).strip()
    if not clean:
        return "empty"
    if clean.startswith("adb "):
        return "adb_command"

    words = set(re.findall(r"[a-z0-9']+", clean))
    if clean in {"hi", "hello", "hey", "hello mibu", "hi mibu", "are you there"}:
        return "greeting"
    if (
        ({"app", "apps", "packages"} & words)
        and ({"what", "which", "list", "show", "many", "installed"} & words)
    ):
        return "app_list"
    if "installed" in words and ({"mibu", "apk"} & words):
        return "mibu_installed"
    if "install" in words and ({"this", "mibu", "apk", "app"} & words):
        return "install_mibu"
    if "open" in words and "mibu" in words:
        return "open_mibu"
    if "status" in words or "what is happening" in clean:
        return "phone_summary"
    if (
        "connected" in words
        or "connection" in words
        or ("phone" in words and ({"what", "which", "info", "information", "model"} & words))
    ):
        return "phone_summary"
    if "four token" in clean or "4 token" in clean or "lane" in words or "lanes" in words:
        return "token_lanes"
    if "manual" in words or "guide" in words or clean == "help":
        return "manual"
    if "start waiting" in clean or "phone guide" in clean or "timer" in words or "countdown" in words:
        return "phone_guide"
    if "couldn't add" in clean or "couldnt add" in clean or "unlock status" in clean or "bind" in words or "binding" in words:
        return "unlock_methods"
    if "compatibility" in words or "hypersploit" in words or "hyperos build" in clean:
        return "compatibility"
    if {"token", "login", "browser", "session"} & words:
        return "token_handoff"
    if {"device", "adb", "connect", "usb"} & words:
        return "device_check"
    if "one click" in clean or "automatic" in words or clean in {"start", "go", "run"}:
        return "one_click"
    return "unknown"


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
                root / "pc-helper" / "release" / "MIBU-PC-Helper",
                root / "pc-helper" / "release" / "MIBU-PC-Helper" / "dist",
                root / "pc-helper" / "release" / "MIBU-PC-Helper" / "resources",
                root / "pc-helper" / "qt6" / "dist" / "MIBU-PC-Helper",
                root / "pc-helper" / "qt6" / "dist" / "MIBU-PC-Helper" / "dist",
                root / "pc-helper" / "qt6" / "dist" / "MIBU-PC-Helper" / "resources",
            ]
        )
    return list(dict.fromkeys(expanded))


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
