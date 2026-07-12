from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        raise AssertionError(f"Missing required file: {path}")
    return target.read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    content = text(path)
    for needle in needles:
        if needle not in content:
            raise AssertionError(f"{path} is missing proof-v2 contract: {needle}")


def forbid(path: str, *needles: str) -> None:
    content = text(path)
    for needle in needles:
        if needle in content:
            raise AssertionError(f"{path} contains forbidden proof-v2 contract: {needle}")


def compile_python(path: str) -> None:
    ast.parse(text(path), filename=path)


def main() -> int:
    require(
        "android/app/build.gradle.kts",
        'versionName = "0.2.0-dev"',
        "versionCode = 2",
        "JavaVersion.VERSION_17",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/ProofContract.kt",
        "const val VERSION = 2",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/StatusActivity.kt",
        'append(" protocol=").append(ProofContract.VERSION)',
        'append(" app=").append(BuildConfig.VERSION_NAME)',
        'append("STATUS nonce=")',
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        'startForeground(NOTIFICATION_ID, buildNotification("Checking saved waiting state…"))',
        "WAITING_LANE_IGNORED_AUTHORITATIVE",
        "WAITING_LANE_IGNORED_COMPLETE",
        "before.isAuthoritativeResult()",
        "before.isTimingComplete()",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/StartWaitingActivity.kt",
        "startCompletedProofService()",
        "WAITING_ACTIVITY_RESUMED",
        "startForegroundService(serviceIntent)",
        "currentState.blocksNewWaitingCycle()",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/VerificationResultActivity.kt",
        "stopTimingService()",
        "stopService(Intent(this, MibuForegroundService::class.java))",
        "stateStore.completeVerification(state)",
        "stateStore.resetWorkflow()",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/TokenStore.kt",
        "remainingMillis(prefs.getLong(timestampKey, 0L), nowMs)",
        "if (ageMs < 0L) return 0L",
        "MAX_TOKEN_LENGTH = 8_192",
    )
    require(
        "android/app/src/main/AndroidManifest.xml",
        "android.permission.POST_NOTIFICATIONS",
        ".VerificationResultActivity",
        'android:allowBackup="false"',
    )

    for path in (
        "pc-helper/qt6/mibu_actions.py",
        "pc-helper/qt6/mibu_status.py",
        "pc-helper/qt6/test_contracts.py",
        "pc-helper/qt6/test_install_contracts.py",
    ):
        compile_python(path)

    require(
        "pc-helper/qt6/mibu_status.py",
        "EXPECTED_PROOF_PROTOCOL = 2",
        "protocol: int",
        "app_version: str",
        "contract_current",
        "parsed.protocol != EXPECTED_PROOF_PROTOCOL",
        "parsed.app_version != EXPECTED_APP_VERSION",
    )
    require(
        "pc-helper/qt6/mibu_actions.py",
        'EXPECTED_APP_VERSION = "0.2.0-dev"',
        "def parse_package_version",
        "def parse_fastboot_devices",
        "nonce_marker",
        '"WAITING_SERVICE_RECOVERED_COMPLETE"',
        '"WAITING_SERVICE_COMPLETE"',
    )
    forbid(
        "pc-helper/qt6/mibu_actions.py",
        '["logcat", "-c"]',
        '_wait_for_log_marker("MIBU_WAIT", "WAITING_ACTIVITY_STARTED")',
    )
    require(
        "pc-helper/qt6/test_contracts.py",
        "test_completed_race_marker_is_accepted_from_success_tuple",
        "test_status_parser_accepts_matching_current_contract",
        "test_old_protocol_parses_but_is_not_current",
        "test_old_app_version_parses_but_is_not_current",
    )

    require(
        "pc-helper/build_windows.ps1",
        "[switch]$UseExistingApk",
        "rebuild from current Android source",
        ":android:app:clean",
        "Use -UseExistingApk only for an APK already produced by the current CI commit",
        "python -m unittest discover -v",
        "Get-FileHash -Algorithm SHA256",
        '"SHA256SUMS.txt"',
    )
    require(
        ".github/workflows/build.yml",
        "python tools/review_proof_v2.py",
        ":android:app:lintDebug",
        "python -m unittest discover -v",
        ".\\pc-helper\\build_windows.ps1 -UseExistingApk",
        '"$root\\SHA256SUMS.txt"',
    )
    require(
        ".gitignore",
        "!resources/expected ui/android/README.md",
        "!resources/expected ui/android/approved_android_ui_baseline_sheet.svg",
        "!resources/expected ui/pc/*.svg",
    )
    require(
        "README.md",
        "does **not** send or replay Xiaomi request traffic",
        "random correlation nonce",
        "SHA256SUMS.txt",
    )
    require(
        "docs/ARCHITECTURE.md",
        "Proof correlation",
        "must start foreground immediately on every service path",
        "SHA256SUMS.txt",
    )

    print("MIBU proof-v2 review passed: correlated status, service authority and source-fresh release contracts align.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"PROOF-V2 REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
