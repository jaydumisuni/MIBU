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
        ".CommunityCheckActivity", ".TokenImportActivity", ".StartWaitingActivity",
        ".StatusActivity", ".MibuForegroundService",
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
        "stateStore.reconcileTimingState(nowChina)", "stateStore.waitingTargetMidnight()",
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
        "stateStore.reconcileTimingState()", "WAITING_ALREADY_COMPLETE", "if (!tokenStore.hasRequiredCaptures())",
        "waitMs > freshnessMs", "stateStore.armWaiting(targetMidnight)", "WAITING_ACTIVITY_STARTED",
        "WAITING_REJECTED_TOKEN_EXPIRY", "PC helper confirms when the service is actually armed",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuStateStore.kt",
        "fun reconcileTimingState", "KEY_TARGET_MIDNIGHT_EPOCH_MS", "waitingTargetMidnight()",
        "VerificationState.TIMING_WINDOW_REACHED", "LaneStatus.WINDOW_REACHED",
        "isAuthoritativeResult()", "completeVerification", "Unknown lane number",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        "handler.postDelayed(callback", "LaneStatus.WINDOW_REACHED", "VerificationState.TIMING_WINDOW_REACHED",
        "PowerManager.PARTIAL_WAKE_LOCK", "START_NOT_STICKY", "stateStore.reconcileTimingState(nowChina)",
        "waitingTargetMidnight()", "WAITING_SERVICE_ARMED", "WAITING_SERVICE_REJECTED_MISSING_CAPTURES",
        "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY", "WAITING_SERVICE_RECOVERED_COMPLETE", "WAITING_SERVICE_COMPLETE",
        "private fun isAuthoritativeResult", "current != VerificationState.TIMING_WINDOW_REACHED",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/StatusActivity.kt",
        "stateStore.reconcileTimingState()", 'append("captures=")', 'append(" verification=")',
        'append(" lanes=")', '"MIBU_STATUS"',
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/LogsActivity.kt",
        "stateStore.reconcileTimingState()", 'mibuCard("Persisted target"',
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

    active_python = (
        "pc-helper/mibu_pc_helper.py", "pc-helper/qt6/mibu_actions.py", "pc-helper/qt6/mibu_status.py",
        "pc-helper/qt6/dependency_check.py", "pc-helper/qt6/ui_geometry.py",
        "pc-helper/qt6/render_svg_assets.py", "pc-helper/qt6/validate_ui_contract.py",
        "pc-helper/qt6/mibu_pc_helper_v2.py", "pc-helper/qt6/mibu_pc_helper_v3.py",
        "pc-helper/qt6/test_contracts.py", "tools/validate_android_ui_baseline.py",
    )
    for path in active_python:
        check_python(path)

    require_text(
        "pc-helper/qt6/mibu_actions.py",
        "def parse_devices", "Multiple ADB devices are connected", "def _open_system_installer",
        "system installer", "def push_two_tokens_to_phone", "mibu_service_token_b64",
        "def _wait_for_log_outcome", "def _wait_for_log_marker", "TWO_CAPTURES_IMPORTED",
        '"MIBU_SERVICE"', '"WAITING_SERVICE_ARMED"', '"WAITING_SERVICE_FAILED"',
        "foreground service was not proven armed", "def check_fastboot_ready(wait_seconds: int = 30)",
        "Multiple fastboot devices are connected",
    )
    forbid_text("pc-helper/qt6/mibu_actions.py", '_wait_for_log_marker("MIBU_WAIT", "WAITING_ACTIVITY_STARTED")')
    require_text(
        "pc-helper/qt6/mibu_status.py",
        "class PhoneStatus", "def query_phone_status", "captures_ready", "timing_complete", "MIBU_STATUS",
    )
    require_text(
        "pc-helper/qt6/dependency_check.py",
        "from mibu_actions import adb_path, fastboot_path", "Fastboot platform-tools",
    )
    require_text(
        "pc-helper/qt6/ui_geometry.py",
        "POPUP_CLOSE_RECT = (925, 30, 50, 50)", "POPUP_CLOSE_ART_BOUNDS = (930, 35, 40, 40)",
        '"Device Check": (300, 668, 205, 84)',
        '"Paste Two Tokens": (620, 585, 300, 56)',
        '"Verify Fastboot": (540, 560, 230, 56)',
    )
    require_text(
        "pc-helper/qt6/validate_ui_contract.py",
        "POPUP_CLOSE_ART_BOUNDS, POPUP_CLOSE_RECT, SCREENS", "tolerance: int = 2",
        "def contains", "visible close artwork is fully clickable",
    )
    require_text(
        "pc-helper/qt6/render_svg_assets.py",
        "from ui_geometry import SCREENS", "render_icon", "mibu_app_icon.ico", "Expected exactly five required UI screens",
    )
    require_text(
        "pc-helper/qt6/test_contracts.py",
        "class DeviceParsingTests", "class ServiceProofTests", "class PhoneStatusTests",
        "class TimingTests", "class GeometryTests", "test_activity_started_marker_is_not_service_proof",
    )
    require_text(
        "pc-helper/qt6/mibu_pc_helper_v3.py",
        "class WorkflowDialog(V2WorkflowDialog)", "POPUP_CLOSE_RECT", "base_ui.WorkflowDialog = WorkflowDialog",
        "class Window(V2Window)", "query_phone_status", "captures_ready", "timing_complete",
        "mibu_app_icon.png", "Phone timing stage is already complete", "Foreground service proof succeeded",
        "Phone timing proof is not complete yet",
    )

    require_text(
        "docs/ARCHITECTURE.md",
        "MIBU PC Helper v3", "WAITING_SERVICE_ARMED", "does **not** currently submit or replay Xiaomi network requests",
        "Timing reconciliation must never overwrite an authoritative external result",
        "A physical-device run remains necessary to prove external facts",
    )
    forbid_text(
        "docs/ARCHITECTURE.md",
        "Missing pieces to implement later", "Later: prepares a secure handoff package",
    )

    require_text(
        "resources/expected ui/android/README.md",
        "approved_android_ui_baseline_sheet.svg", "Recovered source identities",
        "Welcome / entry", "Dashboard / status", "Dashboard / waiting",
        "Step-by-step guide", "Approved MIBU logo", "redrawn from memory",
    )
    check_svg("resources/expected ui/android/approved_android_ui_baseline_sheet.svg", "720", "560")
    require_text(
        "tools/validate_android_ui_baseline.py",
        "EXPECTED_LABELS", "EXPECTED_IMAGE_COUNT = 5", "EXPECTED_SOURCE_HASHES", "MIN_EMBEDDED_IMAGE_BYTES",
        "expected 5 embedded approved images", "self-contained image data URI",
        "Android expected-UI baseline validated",
    )
    require_text(
        ".github/workflows/android-ui-baseline.yml",
        "Validate recovered approved Android UI", "python tools/validate_android_ui_baseline.py",
        'test -s "resources/expected ui/android/approved_android_ui_baseline_sheet.svg"',
    )
    require_text(
        ".github/workflows/build.yml",
        "Validate restored approved Android UI baseline", "python tools/validate_android_ui_baseline.py",
        'resources/expected ui/android/approved_android_ui_baseline_sheet.svg',
        'resources\\expected ui\\android\\approved_android_ui_baseline_sheet.svg',
    )
    require_text(
        "pc-helper/build_windows.ps1",
        "Resolve-Gradle", "Resolve-AndroidSdk", "mibu_pc_helper_v3.py", "--icon $IconPath",
        "validate_ui_contract.py", "validate_android_ui_baseline.py", "python -m unittest -v test_contracts.py",
        "mibu_app_icon.ico", "Android approved baseline", "approved_android_ui_baseline_sheet.svg",
        "Android APK is required for a complete MIBU release", "AdbWinUsbApi.dll",
    )

    check_svg("resources/expected ui/pc/01_pc_main_four_button_workflow.svg", "1200", "800")
    check_svg("resources/expected ui/pc/mibu_app_icon.svg", "512", "512")
    for name in (
        "02_popup_device_check_guide.svg", "03_popup_install_apk.svg",
        "04_popup_login_get_token.svg", "05_popup_phone_guide.svg",
    ):
        check_svg(f"resources/expected ui/pc/{name}", "1000", "700")

    print("MIBU source-contract review passed for proof-gated v3 architecture and restored Android UI baseline.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
