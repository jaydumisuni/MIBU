from __future__ import annotations

import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str) -> Path:
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"Missing required file: {path}")
    return target


def require_text(path: str, *needles: str) -> None:
    text = require(path).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path} is missing required contract: {needle}")


def forbid_text(path: str, *needles: str) -> None:
    text = require(path).read_text(encoding="utf-8")
    for needle in needles:
        if needle in text:
            raise AssertionError(f"{path} contains outdated claim: {needle}")


def check_python(path: str) -> None:
    ast.parse(require(path).read_text(encoding="utf-8"), filename=path)


def check_svg(path: str, width: str, height: str) -> None:
    root = ET.parse(require(path)).getroot()
    if root.attrib.get("width") != width or root.attrib.get("height") != height:
        raise AssertionError(f"Unexpected SVG canvas for {path}: {root.attrib}")


def main() -> int:
    require_text(
        "android/app/src/main/AndroidManifest.xml",
        "android.permission.WAKE_LOCK", "android.permission.DUMP",
        ".CommunityCheckActivity", ".TokenImportActivity", ".StartWaitingActivity", ".MibuForegroundService",
    )
    require("android/app/src/main/res/drawable/ic_mibu.xml")
    require("android/app/src/main/res/drawable/mibu_hero_art.xml")
    require("android/app/src/test/java/com/thetechguy/mibu/MibuLaneTest.kt")

    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuLane.kt",
        'MibuLane(1, "Firefox service token", 1400)',
        'MibuLane(2, "Chrome pop token", 900)',
        'MibuLane(3, "Firefox service token", 400)',
        'MibuLane(4, "Chrome pop token", 100)',
        "fun nextTargetMidnight", "EARLIEST_OFFSET_MS = 1400L",
        "targetTimeForMidnight(nextTargetMidnight(nowChina))", "WINDOW_REACHED", "TIMING_WINDOW_REACHED",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MainActivity.kt",
        "uiHandler.postDelayed(this, 1000L)", '"Armed • $reached/4 windows reached"',
        '"Timing Stage", "COMPLETE"', "Details stay in Logs", "MIBU confirms timing state only",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/TokenStore.kt",
        "MAX_TOKEN_AGE_MS = 30L * 60L * 1000L", "serviceMillisRemaining", "popMillisRemaining",
        "minOf(serviceMillisRemaining(nowMs), popMillisRemaining(nowMs))", "expireStaleCaptures",
        "KEY_SERVICE_CAPTURED_AT", "KEY_POP_CAPTURED_AT", "hasRequiredCaptures()",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/TokenImportActivity.kt",
        "mibu_service_token_b64", "mibu_pop_token_b64", "Base64.URL_SAFE or Base64.NO_WRAP",
        "TWO_CAPTURES_IMPORTED", "SERVICE_CAPTURE_IMPORTED", "TYPE_TEXT_VARIATION_PASSWORD",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/StartWaitingActivity.kt",
        "if (!tokenStore.hasRequiredCaptures())", "waitMs > freshnessMs", "VerificationState.WAITING_ARMED",
        "WAITING_ACTIVITY_STARTED", "WAITING_REJECTED_TOKEN_EXPIRY",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        "handler.postDelayed(callback", "LaneStatus.WINDOW_REACHED", "VerificationState.TIMING_WINDOW_REACHED",
        "PowerManager.PARTIAL_WAKE_LOCK", "START_NOT_STICKY",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuUiHelpers.kt",
        "fun Activity.mibuPage", "fun Activity.mibuCard", "fun Activity.mibuButton",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/InstructionsActivity.kt",
        "MIBU does not claim request approval or unlock success by itself",
    )
    forbid_text("android/app/src/main/java/com/thetechguy/mibu/InstructionsActivity.kt", "After the request stage")

    for path in (
        "pc-helper/mibu_pc_helper.py", "pc-helper/qt6/mibu_actions.py", "pc-helper/qt6/dependency_check.py",
        "pc-helper/qt6/ui_geometry.py", "pc-helper/qt6/render_svg_assets.py",
        "pc-helper/qt6/validate_ui_contract.py", "pc-helper/qt6/mibu_pc_helper_v2.py",
        "pc-helper/qt6/test_contracts.py",
    ):
        check_python(path)

    require_text(
        "pc-helper/qt6/mibu_actions.py",
        "def push_two_tokens_to_phone", "mibu_service_token_b64", "base64.urlsafe_b64encode",
        "def _wait_for_log_marker", "TWO_CAPTURES_IMPORTED", "WAITING_ACTIVITY_STARTED",
        "def reboot_to_fastboot", "def check_fastboot_ready(wait_seconds: int = 30)", "time.monotonic()",
    )
    require_text(
        "pc-helper/qt6/ui_geometry.py",
        '"Device Check": (300, 668, 205, 84)',
        '"Paste Two Tokens": (620, 585, 300, 56)',
        '"Verify Fastboot": (540, 560, 230, 56)',
    )
    require_text(
        "pc-helper/qt6/validate_ui_contract.py",
        "from ui_geometry import SCREENS", "tolerance: int = 2", "no baked active glow",
    )
    require_text(
        "pc-helper/qt6/render_svg_assets.py",
        "from ui_geometry import SCREENS", "Expected exactly five required UI screens",
    )
    require_text(
        "pc-helper/qt6/test_contracts.py",
        "class DeviceParsingTests", "class TimingTests", "class GeometryTests",
    )
    require_text(
        "pc-helper/qt6/mibu_pc_helper_v2.py",
        "from ui_geometry import SCREENS, ScreenGeometry", "required_asset", "Paste Two Tokens",
        "Verify Fastboot", "QTimer", 'self.main_screen = SCREENS["main"]', "self.screen.normalized(label)",
    )
    require_text(
        "pc-helper/build_windows.ps1",
        "Resolve-Gradle", "Resolve-AndroidSdk", "mibu_pc_helper_v2.py", "validate_ui_contract.py",
        "python -m unittest -v test_contracts.py", "Hotspot UI assets verified.",
        "Release EXE, APK, platform-tools and hotspot assets verified.",
        "Android APK is required for a complete MIBU release", "AdbWinUsbApi.dll",
    )

    check_svg("resources/expected ui/pc/01_pc_main_four_button_workflow.svg", "1200", "800")
    for name in (
        "02_popup_device_check_guide.svg", "03_popup_install_apk.svg",
        "04_popup_login_get_token.svg", "05_popup_phone_guide.svg",
    ):
        check_svg(f"resources/expected ui/pc/{name}", "1000", "700")

    print("MIBU source-contract review passed for active v2 architecture.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
