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
            raise AssertionError(f"{path} contains forbidden/outdated contract: {needle}")


def check_python(path: str) -> None:
    ast.parse(require(path).read_text(encoding="utf-8"), filename=path)


def check_svg(path: str, width: str, height: str) -> None:
    root = ET.parse(require(path)).getroot()
    if root.attrib.get("width") != width or root.attrib.get("height") != height:
        raise AssertionError(f"Unexpected SVG canvas for {path}: {root.attrib}")


def main() -> int:
    manifest = "android/app/src/main/AndroidManifest.xml"
    require_text(
        manifest,
        "android.permission.POST_NOTIFICATIONS",
        "android.permission.FOREGROUND_SERVICE_DATA_SYNC",
        "android.permission.WAKE_LOCK",
        "android.permission.DUMP",
        ".CommunityCheckActivity",
        ".VerificationResultActivity",
        ".TokenImportActivity",
        ".StartWaitingActivity",
        ".StatusActivity",
        ".MibuForegroundService",
        'android:allowBackup="false"',
        'android:usesCleartextTraffic="false"',
    )
    require_text(
        "android/app/build.gradle.kts",
        'versionCode = 2',
        'versionName = "0.2.0-dev"',
        "JavaVersion.VERSION_17",
        'jvmTarget = "17"',
        'testImplementation("junit:junit:4.13.2")',
    )
    require("android/app/src/main/res/drawable/ic_mibu.xml")
    require("android/app/src/main/res/drawable/mibu_hero_art.xml")

    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuLane.kt",
        'MibuLane(1, "Firefox service token", 1400)',
        'MibuLane(2, "Chrome pop token", 900)',
        'MibuLane(3, "Firefox service token", 400)',
        'MibuLane(4, "Chrome pop token", 100)',
        "fun nextTargetMidnight",
        "EARLIEST_OFFSET_MS = 1400L",
        "targetTimeForMidnight(nextTargetMidnight(nowChina))",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/VerificationStateRules.kt",
        "fun VerificationState.isAuthoritativeResult()",
        "fun VerificationState.isTimingComplete()",
        "fun VerificationState.blocksNewWaitingCycle()",
        "VerificationState.WAIT_TIME_SHOWN",
        "VerificationState.UNLOCKED",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/ProofNonce.kt",
        'const val EXTRA = "mibu_proof_nonce"',
        'Regex("^[A-Za-z0-9_-]{8,64}$")',
        'else "none"',
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/TokenStore.kt",
        "MAX_TOKEN_AGE_MS = 30L * 60L * 1000L",
        "MAX_TOKEN_LENGTH = 8_192",
        "fun isAcceptableToken",
        "fun remainingMillis",
        "if (ageMs < 0L) return 0L",
        "remainingMillis(prefs.getLong(timestampKey, 0L), nowMs)",
        "minOf(serviceMillisRemaining(nowMs), popMillisRemaining(nowMs))",
        "expireStaleCaptures",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/TokenImportActivity.kt",
        "ProofNonce.from(intent)",
        "MAX_ENCODED_EXTRA_LENGTH = 12_000",
        "TokenStore.isAcceptableToken",
        "InputFilter.LengthFilter(TokenStore.MAX_TOKEN_LENGTH)",
        '"TWO_CAPTURES_IMPORTED nonce=$proofNonce"',
        '"SERVICE_CAPTURE_IMPORTED nonce=$proofNonce"',
        "Base64.URL_SAFE or Base64.NO_WRAP",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuStateStore.kt",
        "fun reconcileTimingState",
        "currentVerification.isAuthoritativeResult()",
        "currentVerification.isTimingComplete()",
        "fun completeVerification",
        "fun resetWorkflow",
        "KEY_TARGET_MIDNIGHT_EPOCH_MS",
        "Unknown lane number",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/StartWaitingActivity.kt",
        "ProofNonce.from(intent)",
        "currentState.blocksNewWaitingCycle()",
        "currentState.isTimingComplete()",
        "startCompletedProofService()",
        "WAITING_ACTIVITY_RESUMED",
        "WAITING_ACTIVITY_STARTED",
        "WAITING_REJECTED_TOKEN_EXPIRY",
        "remainingLanes",
        "stateStore.armWaiting(targetMidnight)",
        "putExtra(ProofNonce.EXTRA, proofNonce)",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        'startForeground(NOTIFICATION_ID, buildNotification("Checking saved waiting state…"))',
        "reconciled.isTimingComplete()",
        "reconciled.isAuthoritativeResult()",
        "WAITING_SERVICE_ARMED",
        "WAITING_SERVICE_RECOVERED_COMPLETE",
        "WAITING_SERVICE_COMPLETE",
        "WAITING_SERVICE_REJECTED_MISSING_CAPTURES",
        "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY",
        "WAITING_SERVICE_FAILED",
        "PowerManager.PARTIAL_WAKE_LOCK",
        "handler.postDelayed(callback",
        "private fun updateNotification",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/StatusActivity.kt",
        "ProofNonce.from(intent)",
        'append("STATUS nonce=")',
        'append(" captures=")',
        'append(" verification=")',
        'append(" community=")',
        'append(" lanes=")',
        'private const val LOG_TAG = "MIBU_STATUS"',
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MainActivity.kt",
        "Manifest.permission.POST_NOTIFICATIONS",
        "requestNotificationPermissionIfNeeded",
        "stateStore.reconcileTimingState(nowChina)",
        '"Resume Waiting"',
        '"No active target"',
        "verification.blocksNewWaitingCycle()",
        "friendlyVerification",
        "verificationGuidance",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/VerificationResultActivity.kt",
        "Record only what the official tool showed",
        "stateStore.completeVerification(state)",
        "stateStore.resetWorkflow()",
        "tokenStore.clear()",
        "WORKFLOW_RESET",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/LogsActivity.kt",
        "stateStore.reconcileTimingState()",
        'mibuCard("Persisted target"',
        '"Record Official Mi Unlock Result"',
        "VerificationResultActivity::class.java",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/InstructionsActivity.kt",
        "MIBU does not claim request approval or unlock success by itself",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuUiHelpers.kt",
        "fun Activity.mibuPage",
        "fun Activity.mibuCard",
        "fun Activity.mibuButton",
    )

    for test_path in (
        "android/app/src/test/java/com/thetechguy/mibu/MibuLaneTest.kt",
        "android/app/src/test/java/com/thetechguy/mibu/TokenStoreContractTest.kt",
        "android/app/src/test/java/com/thetechguy/mibu/VerificationStateRulesTest.kt",
    ):
        require(test_path)
    require_text(
        "android/app/src/test/java/com/thetechguy/mibu/TokenStoreContractTest.kt",
        "wallClockRollbackFailsClosedInsteadOfExtendingLifetime",
        "tokenValidationRejectsControlsAndOversizeValues",
    )
    require_text(
        "android/app/src/test/java/com/thetechguy/mibu/VerificationStateRulesTest.kt",
        "everyOfficialResultIsAuthoritativeAndBlocksRearm",
        "timingCompletionBlocksASecondWaitingCycle",
    )

    active_python = (
        "pc-helper/mibu_pc_helper.py",
        "pc-helper/qt6/mibu_actions.py",
        "pc-helper/qt6/mibu_status.py",
        "pc-helper/qt6/dependency_check.py",
        "pc-helper/qt6/ui_geometry.py",
        "pc-helper/qt6/render_svg_assets.py",
        "pc-helper/qt6/validate_ui_contract.py",
        "pc-helper/qt6/mibu_pc_helper_v2.py",
        "pc-helper/qt6/mibu_pc_helper_v3.py",
        "pc-helper/qt6/test_contracts.py",
        "pc-helper/qt6/test_install_contracts.py",
        "tools/validate_android_ui_baseline.py",
    )
    for path in active_python:
        check_python(path)

    require_text(
        "pc-helper/qt6/mibu_actions.py",
        'EXPECTED_APP_VERSION = "0.2.0-dev"',
        "def parse_devices",
        "def parse_fastboot_devices",
        "def parse_package_version",
        "def installed_package_version",
        "def _valid_token",
        "MAX_TOKEN_LENGTH = 8_192",
        "def _proof_nonce",
        "def _wait_for_log_outcome",
        "nonce_marker",
        '"WAITING_SERVICE_ARMED"',
        '"WAITING_SERVICE_RECOVERED_COMPLETE"',
        '"WAITING_SERVICE_COMPLETE"',
        "version verification",
        "Multiple ADB devices are connected",
        "Multiple fastboot devices are connected",
    )
    forbid_text(
        "pc-helper/qt6/mibu_actions.py",
        '["logcat", "-c"]',
        '_wait_for_log_marker("MIBU_WAIT", "WAITING_ACTIVITY_STARTED")',
    )
    require_text(
        "pc-helper/qt6/mibu_status.py",
        "nonce: str",
        "expected_nonce",
        "PROOF_NONCE_EXTRA",
        "def query_phone_status",
        "captures_ready",
        "timing_complete",
    )
    require_text(
        "pc-helper/qt6/dependency_check.py",
        "from mibu_actions import adb_path, fastboot_path",
        "Fastboot platform-tools",
    )
    require_text(
        "pc-helper/qt6/test_contracts.py",
        "class DeviceParsingTests",
        "class ServiceProofTests",
        "class PhoneStatusTests",
        "test_stale_success_marker_with_wrong_nonce_is_rejected",
        "test_activity_started_marker_is_not_service_proof",
        "test_fastboot_parser_requires_real_device_rows",
    )
    require_text(
        "pc-helper/qt6/test_install_contracts.py",
        "class PackageVersionTests",
        "test_old_installed_version_is_updated_and_reverified",
        "test_version_mismatch_after_install_is_failure",
    )
    require_text(
        "pc-helper/qt6/mibu_pc_helper_v3.py",
        "class WorkflowDialog(V2WorkflowDialog)",
        "POPUP_CLOSE_RECT",
        "base_ui.WorkflowDialog = WorkflowDialog",
        "query_phone_status",
        "timing_complete",
        "Phone timing stage is already complete",
        "Phone timing proof is not complete yet",
    )

    require_text(
        "pc-helper/qt6/ui_geometry.py",
        "POPUP_CLOSE_RECT = (925, 30, 50, 50)",
        "POPUP_CLOSE_ART_BOUNDS = (930, 35, 40, 40)",
        '"Device Check": (300, 668, 205, 84)',
        '"Paste Two Tokens": (620, 585, 300, 56)',
        '"Verify Fastboot": (540, 560, 230, 56)',
    )
    require_text(
        "pc-helper/qt6/validate_ui_contract.py",
        "POPUP_CLOSE_ART_BOUNDS, POPUP_CLOSE_RECT, SCREENS",
        "visible close artwork is fully clickable",
    )
    require_text(
        "pc-helper/qt6/render_svg_assets.py",
        "from ui_geometry import SCREENS",
        "render_icon",
        "mibu_app_icon.ico",
        "Expected exactly five required UI screens",
    )

    require_text(
        "README.md",
        "Android app — `0.2.0-dev`",
        "random correlation nonce",
        "never clears the phone's whole logcat",
        "SHA256SUMS.txt",
        "does **not** send or replay Xiaomi request traffic",
        "python -m unittest discover -v",
    )
    require_text(
        "docs/ARCHITECTURE.md",
        "Proof correlation",
        "VerificationStateRules.kt",
        "start foreground immediately on every service path",
        "SHA256SUMS.txt",
        "does not claim that reaching a timing window means Xiaomi approved a request",
        "physical-device run remains necessary",
    )
    forbid_text(
        "docs/ARCHITECTURE.md",
        "Missing pieces to implement later",
        "Later: prepares a secure handoff package",
    )

    require_text(
        "resources/expected ui/android/README.md",
        "approved_android_ui_baseline_sheet.svg",
        "Recovered source identities",
        "Welcome / entry",
        "Dashboard / status",
        "Dashboard / waiting",
        "Step-by-step guide",
        "Approved MIBU logo",
        "redrawn from memory",
    )
    check_svg("resources/expected ui/android/approved_android_ui_baseline_sheet.svg", "720", "560")
    require_text(
        "tools/validate_android_ui_baseline.py",
        "EXPECTED_LABELS",
        "EXPECTED_IMAGE_COUNT = 5",
        "EXPECTED_SOURCE_HASHES",
        "expected 5 embedded approved images",
        "self-contained image data URI",
    )
    require_text(
        ".github/workflows/android-ui-baseline.yml",
        "Validate recovered approved Android UI",
        "python tools/validate_android_ui_baseline.py",
    )
    require_text(
        ".github/workflows/build.yml",
        ":android:app:lintDebug",
        "python -m unittest discover -v",
        "test_install_contracts.py",
        "EXPECTED_APP_VERSION == '0.2.0-dev'",
        '"$root\\SHA256SUMS.txt"',
        "Complete Windows release proof",
    )
    require_text(
        "pc-helper/build_windows.ps1",
        ":android:app:lintDebug",
        "tools\\review_contracts.py",
        "python -m unittest discover -v",
        "--clean --noconfirm --windowed",
        "EXPECTED_APP_VERSION == '0.2.0-dev'",
        "Get-FileHash -Algorithm SHA256",
        '"SHA256SUMS.txt"',
        "Release checksum manifest count",
        "approved_android_ui_baseline_sheet.svg",
        "AdbWinUsbApi.dll",
    )

    check_svg("resources/expected ui/pc/01_pc_main_four_button_workflow.svg", "1200", "800")
    check_svg("resources/expected ui/pc/mibu_app_icon.svg", "512", "512")
    for name in (
        "02_popup_device_check_guide.svg",
        "03_popup_install_apk.svg",
        "04_popup_login_get_token.svg",
        "05_popup_phone_guide.svg",
    ):
        check_svg(f"resources/expected ui/pc/{name}", "1000", "700")

    print("MIBU 0.2 source-contract review passed: state, proof, UI and release contracts are aligned.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
