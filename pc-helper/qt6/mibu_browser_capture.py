from __future__ import annotations

import configparser
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

from dependency_check import browser_path
from mibu_actions import Result, _valid_token
from mibu_runtime import LOGIN_URL

STATUS_URL = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
CHROME_BOOKMARKLET_BODY = (
    '(function(){var token=document.cookie.match(/popRunToken=([^;]+)/);'
    'if(token){prompt("MIBU approved capture:",token[1]);}'
    'else{alert("MIBU: Xiaomi login capture is not ready");}})()'
)


@dataclass(frozen=True)
class BrowserCaptures:
    service_token: str
    pop_token: str


def validate_xiaomi_capture(token: str, label: str) -> Result:
    if not _valid_token(token):
        return Result(False, f"{label} capture is malformed.")
    device_id = uuid.uuid4().hex.upper()
    request = urllib.request.Request(
        STATUS_URL,
        headers={
            "Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};",
            "User-Agent": "okhttp/4.12.0",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        return Result(False, f"{label} could not be verified with Xiaomi: {exc}")
    code = payload.get("code")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    is_pass = data.get("is_pass")
    button_state = data.get("button_state")
    if code == 100004:
        return Result(False, f"{label} has expired according to Xiaomi.")
    if code == 0 and is_pass == 1:
        return Result(True, f"{label} is valid; Xiaomi reports this application is already approved.")
    if code == 0 and is_pass == 4 and button_state == 1:
        return Result(True, f"{label} is valid; Xiaomi reports the account is eligible to submit.")
    deadline = str(data.get("deadline_format") or "").strip()
    detail = f" Deadline: {deadline}." if deadline else ""
    return Result(False, f"{label} is valid but Xiaomi reports is_pass={is_pass}, button_state={button_state}.{detail}")


def _read_text_with_bom(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
        except UnicodeError:
            continue
        if "[Profile" in text or "[Install" in text:
            return text
    raise ValueError("Firefox profiles.ini encoding is not supported")


def firefox_profile_dir() -> Path | None:
    appdata = Path(os.environ.get("APPDATA", ""))
    root = appdata / "Mozilla" / "Firefox"
    profiles_ini = root / "profiles.ini"
    if not profiles_ini.is_file():
        return None
    parser = configparser.RawConfigParser()
    parser.read_string(_read_text_with_bom(profiles_ini))
    candidates: list[tuple[int, Path]] = []
    for section in parser.sections():
        if not section.startswith("Profile"):
            continue
        value = parser.get(section, "Path", fallback="").strip()
        if not value:
            continue
        profile = Path(value) if parser.getboolean(section, "IsRelative", fallback=True) is False else root / value
        score = 10 if parser.getboolean(section, "Default", fallback=False) else 0
        if (profile / "cookies.sqlite").is_file():
            candidates.append((score, profile))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], (item[1] / "cookies.sqlite").stat().st_mtime))[1]


def capture_firefox_service_token() -> tuple[Result, str | None]:
    profile = firefox_profile_dir()
    if profile is None:
        return Result(False, "Firefox profile or cookies database was not found."), None
    source = profile / "cookies.sqlite"
    try:
        with tempfile.TemporaryDirectory(prefix="mibu-firefox-") as temp:
            copied = Path(temp) / "cookies.sqlite"
            shutil.copy2(source, copied)
            connection = sqlite3.connect(f"file:{copied.as_posix()}?mode=ro", uri=True)
            try:
                row = connection.execute(
                    "SELECT value FROM moz_cookies WHERE name=? AND host LIKE ? ORDER BY lastAccessed DESC LIMIT 1",
                    ("new_bbs_serviceToken", "%mi.com"),
                ).fetchone()
            finally:
                connection.close()
    except Exception as exc:
        return Result(False, f"Firefox capture could not be read: {exc}"), None
    token = row[0].strip() if row and isinstance(row[0], str) else ""
    if not _valid_token(token):
        return Result(False, "Firefox is installed, but no valid new_bbs_serviceToken was found. Sign in to Xiaomi in Firefox and retry."), None
    return Result(True, f"Firefox capture found and validated ({len(token)} characters; value hidden)."), token


def chrome_capture_profile_dir() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_app_data / "THETECHGUY TOOL" / "MIBU" / "ChromeCapture"


def _capture_chrome_normal_profile(chrome: str, timeout_seconds: int = 25) -> tuple[Result, str | None]:
    if sys.platform != "win32":
        return Result(False, "Normal-profile Chrome automation is available on Windows only."), None

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    cf_unicode_text = 13
    gmem_moveable_zero = 0x0042
    keyeventf_keyup = 0x0002
    keyeventf_unicode = 0x0004
    input_keyboard = 1
    vk_control = 0x11
    vk_menu = 0x12
    vk_return = 0x0D
    vk_escape = 0x1B
    sw_restore = 9
    wm_close = 0x0010

    ulong_ptr = wintypes.WPARAM

    class KeybdInput(ctypes.Structure):
        _fields_ = (
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ulong_ptr),
        )

    class InputUnion(ctypes.Union):
        _fields_ = (("ki", KeybdInput),)

    class Input(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = (("type", wintypes.DWORD), ("value", InputUnion))

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = (wintypes.UINT,)
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
    user32.SetClipboardData.restype = wintypes.HANDLE
    kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalLock.restype = wintypes.LPVOID
    kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalFree.argtypes = (wintypes.HGLOBAL,)

    def open_clipboard() -> bool:
        for _ in range(20):
            if user32.OpenClipboard(None):
                return True
            time.sleep(0.05)
        return False

    def clipboard_text() -> str:
        if not open_clipboard():
            return ""
        try:
            handle = user32.GetClipboardData(cf_unicode_text)
            if not handle:
                return ""
            pointer = kernel32.GlobalLock(handle)
            if not pointer:
                return ""
            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    def set_clipboard_text(value: str) -> bool:
        encoded = value.encode("utf-16-le") + b"\0\0"
        handle = kernel32.GlobalAlloc(gmem_moveable_zero, len(encoded))
        if not handle:
            return False
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(pointer, encoded, len(encoded))
        kernel32.GlobalUnlock(handle)
        if not open_clipboard():
            kernel32.GlobalFree(handle)
            return False
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(cf_unicode_text, handle):
                kernel32.GlobalFree(handle)
                return False
            return True
        finally:
            user32.CloseClipboard()

    def send_virtual(key: int, up: bool = False) -> None:
        flags = keyeventf_keyup if up else 0
        item = Input(type=input_keyboard, value=InputUnion(ki=KeybdInput(key, 0, flags, 0, 0)))
        user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(Input))

    def chord(key: int) -> None:
        send_virtual(vk_control)
        send_virtual(key)
        send_virtual(key, True)
        send_virtual(vk_control, True)

    def type_unicode(value: str) -> None:
        for character in value:
            code = ord(character)
            down = Input(type=input_keyboard, value=InputUnion(ki=KeybdInput(0, code, keyeventf_unicode, 0, 0)))
            up = Input(type=input_keyboard, value=InputUnion(ki=KeybdInput(0, code, keyeventf_unicode | keyeventf_keyup, 0, 0)))
            user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(Input))
            user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(Input))

    windows: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_window(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.lower()
        if "xiaomi" in title and "chrome" in title:
            windows.append(hwnd)
        return True

    original_clipboard = clipboard_text()
    target_window = 0
    captured = False
    try:
        subprocess.Popen(
            [chrome, "--new-window", LOGIN_URL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + max(8, timeout_seconds)
        while time.monotonic() < deadline and not target_window:
            windows.clear()
            user32.EnumWindows(enum_window, 0)
            if windows:
                target_window = windows[-1]
                break
            time.sleep(0.25)
        if not target_window:
            return Result(False, "Chrome opened, but the Xiaomi Community window could not be focused."), None

        user32.ShowWindowAsync(target_window, sw_restore)
        send_virtual(vk_menu)
        send_virtual(vk_menu, True)
        user32.SetForegroundWindow(target_window)
        time.sleep(3)
        chord(ord("L"))
        type_unicode("javascript:" + CHROME_BOOKMARKLET_BODY)
        if not set_clipboard_text(""):
            return Result(False, "Chrome capture could not prepare the private clipboard handoff."), None
        send_virtual(vk_return)
        send_virtual(vk_return, True)
        time.sleep(1)
        chord(ord("A"))
        chord(ord("C"))
        time.sleep(0.3)
        candidate = clipboard_text().strip()
        send_virtual(vk_escape)
        send_virtual(vk_escape, True)
        if not _valid_token(candidate):
            state = f"no-candidate length={len(candidate)}"
            return Result(False, f"The normal Chrome profile did not expose popRunToken ({state}). The Xiaomi window remains open; finish login there and retry Auto Capture."), None
        captured = True
        return Result(True, f"Normal Chrome profile capture found ({len(candidate)} characters; value hidden)."), candidate
    except OSError as exc:
        return Result(False, f"Normal Chrome profile automation failed: {exc}"), None
    finally:
        set_clipboard_text(original_clipboard)
        if target_window and captured:
            user32.PostMessageW(target_window, wm_close, 0, 0)


def capture_chrome_pop_token(timeout_seconds: int = 180) -> tuple[Result, str | None]:
    chrome = browser_path("chrome")
    if not chrome:
        return Result(False, "Chrome is not installed."), None
    normal_result, normal_token = _capture_chrome_normal_profile(chrome, min(timeout_seconds, 30))
    if normal_result.ok and normal_token is not None:
        validation = validate_xiaomi_capture(normal_token, "Chrome lanes 2/4")
        if validation.ok:
            return Result(True, f"{normal_result.message}\n{validation.message}"), normal_token
    if "remains open" in normal_result.message:
        return normal_result, None
    profile = chrome_capture_profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    options = Options()
    options.binary_location = chrome
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--window-size=1000,700")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = None
    token = ""
    capture_name = ""
    seen: set[str] = set()
    refreshed_after_rejection = False
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(LOGIN_URL)
        deadline = time.monotonic() + max(3, timeout_seconds)
        while time.monotonic() < deadline:
            rejected = False
            for cookie_name in ("popRunToken", "new_bbs_serviceToken"):
                record = driver.get_cookie(cookie_name) or {}
                candidate = str(record.get("value") or "").strip()
                if not _valid_token(candidate):
                    continue
                fingerprint = hashlib.sha256(f"{cookie_name}\0{candidate}".encode("utf-8")).hexdigest()
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                validation = validate_xiaomi_capture(candidate, "Chrome lanes 2/4")
                if validation.ok:
                    token = candidate
                    capture_name = cookie_name
                    break
                rejected = True
            if token:
                break
            if rejected and not refreshed_after_rejection:
                driver.refresh()
                refreshed_after_rejection = True
            time.sleep(0.5)
    except WebDriverException as exc:
        return Result(False, f"MIBU could not start its controlled Chrome session: {exc.msg or exc.__class__.__name__}"), None
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass
    if not token:
        return Result(False, f"{normal_result.message}\nChrome fallback opened, but Xiaomi did not issue a valid session capture. Complete Xiaomi Community login in the MIBU Chrome window, then retry Auto Capture."), None
    source = "pop token" if capture_name == "popRunToken" else "service-token fallback"
    return Result(True, f"Chrome {source} found and Xiaomi-validated ({len(token)} characters; value hidden)."), token


def capture_browser_tokens() -> tuple[Result, BrowserCaptures | None]:
    firefox_result, service_token = capture_firefox_service_token()
    if not firefox_result.ok or service_token is None:
        return firefox_result, None
    chrome_result, pop_token = capture_chrome_pop_token()
    if not chrome_result.ok or pop_token is None:
        return Result(False, firefox_result.message + "\n" + chrome_result.message), None
    service_status = validate_xiaomi_capture(service_token, "Firefox lanes 1/3")
    if not service_status.ok:
        return service_status, None
    pop_status = validate_xiaomi_capture(pop_token, "Chrome lanes 2/4")
    if not pop_status.ok:
        return pop_status, None
    message = "\n".join((firefox_result.message, chrome_result.message, service_status.message, pop_status.message))
    return Result(True, message), BrowserCaptures(service_token, pop_token)
