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
            raise AssertionError(f"{path} is missing proof contract: {needle}")


def forbid(path: str, *needles: str) -> None:
    content = text(path)
    for needle in needles:
        if needle in content:
            raise AssertionError(f"{path} contains forbidden proof behavior: {needle}")


def main() -> int:
    for path in (
        "pc-helper/qt6/mibu_browser_capture.py",
        "pc-helper/qt6/mibu_phone_agent.py",
        "pc-helper/qt6/mibu_actions.py",
        "pc-helper/qt6/mibu_status.py",
    ):
        ast.parse(text(path), filename=path)

    require("android/app/src/main/java/com/thetechguy/mibu/ProofContract.kt", "const val VERSION = 3")
    require(
        "android/app/src/main/java/com/thetechguy/mibu/XiaomiUnlockClient.kt",
        "sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state",
        "sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth",
        'body = "{\\"is_retry\\":true}"',
        "clockOffsetMs",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        "client.checkStatus",
        "client.submit",
        "WAITING_SERVICE_ARMED",
        "WAITING_SERVICE_COMPLETE",
        "WAITING_SERVICE_PREFLIGHT_REJECTED",
        "isCellularReady",
        "PowerManager.PARTIAL_WAKE_LOCK",
    )
    forbid(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        "markWindowReached",
        "TIMING_WINDOW_REACHED)",
    )
    require(
        "android/app/src/main/java/com/thetechguy/mibu/VerificationStateRules.kt",
        "this == VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION",
    )
    require(
        "pc-helper/qt6/mibu_browser_capture.py",
        '"new_bbs_serviceToken"',
        "popRunToken",
        "webdriver.Chrome",
        "ChromeCapture",
        "validate_xiaomi_capture",
        "value hidden",
    )
    require(
        "pc-helper/qt6/mibu_phone_agent.py",
        '"svc", "data"',
        '"svc", "wifi"',
        "cellular_validated",
        "ready_for_xiaomi",
    )
    require(
        "pc-helper/qt6/mibu_actions.py",
        'EXPECTED_APP_VERSION = "0.3.0-dev"',
        '"WAITING_SERVICE_ARMED"',
        '"WAITING_SERVICE_PREFLIGHT_APPROVED"',
        '"WAITING_SERVICE_PREFLIGHT_REJECTED"',
    )
    require(
        "pc-helper/qt6/mibu_status.py",
        "EXPECTED_PROOF_PROTOCOL = 3",
        'self.verification == "READY_FOR_MI_UNLOCK_VERIFICATION"',
    )
    forbid("pc-helper/qt6/mibu_actions.py", '["logcat", "-c"]', "password")
    print("MIBU proof-v3 review passed: server outcomes, token origin, cellular state and correlated phone proof align.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"PROOF REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
