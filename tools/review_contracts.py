from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str) -> Path:
    target = ROOT / path
    if not target.is_file() or target.stat().st_size <= 0:
        raise AssertionError(f"Missing or empty required file: {path}")
    return target


def require_text(path: str, *needles: str) -> None:
    content = require(path).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in content:
            raise AssertionError(f"{path} is missing required contract: {needle}")


def forbid_path(path: str) -> None:
    if (ROOT / path).exists():
        raise AssertionError(f"Obsolete UI source still exists: {path}")


def compile_python(path: str) -> None:
    ast.parse(require(path).read_text(encoding="utf-8"), filename=path)


def forbid_text(path: str, *needles: str) -> None:
    content = require(path).read_text(encoding="utf-8")
    for needle in needles:
        if needle in content:
            raise AssertionError(f"{path} contains obsolete contract: {needle}")


def main() -> int:
    python_files = (
        "pc-helper/qt6/mibu_actions.py",
        "pc-helper/qt6/mibu_runtime.py",
        "pc-helper/qt6/mibu_status.py",
        "pc-helper/qt6/dependency_check.py",
        "pc-helper/qt6/mibu_pc_helper_v3.py",
        "pc-helper/qt6/test_contracts.py",
        "pc-helper/qt6/test_install_contracts.py",
        "tools/extract_live_ui_assets.py",
    )
    for path in python_files:
        compile_python(path)

    for path in (
        "pc-helper/qt6/mibu_pc_helper_final.py",
        "pc-helper/qt6/mibu_pc_helper_ui.py",
        "pc-helper/qt6/mibu_pc_helper_v2.py",
        "pc-helper/qt6/ui_geometry.py",
        "pc-helper/qt6/render_svg_assets.py",
        "pc-helper/qt6/validate_ui_contract.py",
    ):
        forbid_path(path)

    require_text(
        "pc-helper/qt6/mibu_pc_helper_v3.py",
        "WINDOW_SIZE = QSize(760, 560)",
        "MINIMUM_SIZE = QSize(720, 520)",
        "Qt.FramelessWindowHint",
        "class TitleBar",
        "class LiveDialog",
        "class AssistantOverlay",
        'QPushButton("Need help?")',
        'QPushButton("START")',
        "close.clicked.connect(self.reject)",
        'self.maximize = self._control("\\u25a1", "Maximize", self.toggle_maximize)',
        "check_binding_recovery_compatibility",
        "Open Firefox",
        "Open Chrome",
        "Firefox feeds lanes 1 and 3",
        "Chrome feeds lanes 2 and 4",
        "open_local_guide",
        "QGraphicsDropShadowEffect",
        "QSoundEffect",
        "TTG_v4_clean_connected_success.wav",
        "TTG_v4_clean_speaker_turn_on.wav",
        "SetCurrentProcessExplicitAppUserModelID",
    )
    require_text(
        "pc-helper/qt6/mibu_runtime.py",
        'LOGIN_URL = "https://account.xiaomi.com/"',
        '"chrome": "Google.Chrome"',
        '"firefox": "Mozilla.Firefox"',
        "def next_target",
        "class AppState",
    )
    forbid_text("pc-helper/qt6/dependency_check.py", "Brave browser", 'name == "brave"')
    require_text(
        "pc-helper/qt6/mibu_actions.py",
        "def check_device_ready",
        "def install_package",
        "def launch_phone_app",
        "def push_two_tokens_to_phone",
        "def start_phone_waiting",
        "def launch_mi_unlock_status",
        "def check_binding_recovery_compatibility",
        "Legacy binding recovery is not enabled by One Click",
        'EXPECTED_APP_VERSION = "0.2.0-dev"',
    )

    manifest = "android/app/src/main/AndroidManifest.xml"
    require_text(
        manifest,
        ".MainActivity",
        ".GuideActivity",
        ".CommunityCheckActivity",
        ".InstructionsActivity",
        ".LogsActivity",
        ".TokenImportActivity",
        ".VerificationResultActivity",
        ".UnlockMethodsActivity",
        ".MibuForegroundService",
        "@mipmap/ic_launcher",
        'android:allowBackup="false"',
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuUiHelpers.kt",
        "mibu_logo_live",
        "mibu_wordmark_live",
        "fun Activity.mibuAction",
        "fun Activity.mibuButton",
        "fun Activity.neonBackground",
        "WindowInsets.Type.systemBars",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/UnlockMethodsActivity.kt",
        "Method 1 - Official Xiaomi",
        "Method 2 - Binding Recovery",
        "Method 3 - Legacy Compatibility",
        "Open Mi Unlock Status",
        "Record Official Result",
        "never part of automatic One Click",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MainActivity.kt",
        "postDelayed(this, 1000L)",
        "Start Waiting",
        "MibuForegroundService",
        "requestNotificationPermissionIfNeeded",
    )

    for path in (
        "resources/logo.png",
        "resources/live_ui/mibu_logo.png",
        "resources/live_ui/mibu_hood.png",
        "resources/live_ui/mibu_app_icon.ico",
        "resources/live_ui/firefox.png",
        "resources/live_ui/chrome.png",
        "resources/guide/index.html",
        "android/app/src/main/res/drawable-nodpi/mibu_logo_live.png",
        "android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml",
        "pc-helper/qt6/version_info.txt",
    ):
        require(path)

    require_text(
        "resources/guide/index.html",
        "One-Click Assist",
        "Firefox: lanes 1 and 3",
        "Chrome: lanes 2 and 4",
        "droidwin.com/how-to-unlock-bootloader-on-xiaomi-hyperos-2-android-15",
    )
    require_text(
        "pc-helper/build_windows.ps1",
        "tools\\extract_live_ui_assets.py",
        "resources\\live_ui\\mibu_app_icon.ico",
        "--version-file",
        "SHA256SUMS.txt",
    )

    print("MIBU live-source review passed: compact PC UI, Android workflow, branding, controls and release contracts align.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
