from __future__ import annotations

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
            raise AssertionError(f"{path} is missing proof contract: {needle}")


def forbid(path: str, *needles: str) -> None:
    content = text(path)
    for needle in needles:
        if needle in content:
            raise AssertionError(f"{path} contains forbidden proof behavior: {needle}")


def main() -> int:
    require(
        "android/app/src/main/java/com/thetechguy/mibu/ProofContract.kt",
        "const val VERSION = 2",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/TokenStore.kt",
        "MAX_TOKEN_AGE_MS = 30L * 60L * 1000L",
        "MAX_TOKEN_LENGTH = 8_192",
        "if (ageMs < 0L) return 0L",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        "WAITING_SERVICE_ARMED",
        "WAITING_SERVICE_COMPLETE",
        "WAITING_SERVICE_REJECTED_MISSING_CAPTURES",
        "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY",
        "PowerManager.PARTIAL_WAKE_LOCK",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/StatusActivity.kt",
        'append(" protocol=")',
        'append(" app=")',
        'append("STATUS nonce=")',
    )
    require(
        "pc-helper/qt6/mibu_actions.py",
        'EXPECTED_APP_VERSION = "0.2.0-dev"',
        "nonce_marker",
        '"WAITING_SERVICE_ARMED"',
        '"WAITING_SERVICE_COMPLETE"',
        '["install", "-r", path]',
    )
    forbid(
        "pc-helper/qt6/mibu_actions.py",
        '["logcat", "-c"]',
        "browser_cookie",
        "password",
    )
    require(
        "pc-helper/qt6/mibu_status.py",
        "EXPECTED_PROOF_PROTOCOL = 2",
        "expected_nonce",
        "contract_current",
        "captures_ready",
        "timing_complete",
    )
    require(
        "pc-helper/qt6/test_contracts.py",
        "test_stale_success_marker_with_wrong_nonce_is_rejected",
        "test_activity_started_marker_is_not_service_proof",
        "test_status_parser_accepts_matching_current_contract",
        "test_next_day_target_after_window",
    )
    require(
        "pc-helper/build_windows.ps1",
        ":android:app:clean",
        ":android:app:lintDebug",
        "python -m unittest discover -v",
        "Get-FileHash -Algorithm SHA256",
        '"SHA256SUMS.txt"',
    )
    print("MIBU proof-v2 review passed: capture freshness, correlated phone proof and source-fresh release rules align.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"PROOF REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
