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


def check_python(path: str) -> None:
    source = require(path).read_text(encoding="utf-8")
    ast.parse(source, filename=path)


def check_svg(path: str, width: str, height: str) -> None:
    root = ET.parse(require(path)).getroot()
    if root.attrib.get("width") != width or root.attrib.get("height") != height:
        raise AssertionError(f"Unexpected SVG canvas for {path}: {root.attrib}")


def main() -> int:
    # Android compile/resource contracts.
    require_text(
        "android/app/src/main/AndroidManifest.xml",
        ".CommunityCheckActivity",
        ".TokenImportActivity",
        ".StartWaitingActivity",
        ".MibuForegroundService",
    )
    require("android/app/src/main/res/drawable/ic_mibu.xml")
    require("android/app/src/main/res/drawable/mibu_hero_art.xml")
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuLane.kt",
        'MibuLane(1, "Firefox service token", 1400)',
        'MibuLane(2, "Chrome pop token", 900)',
        'MibuLane(3, "Firefox service token", 400)',
        'MibuLane(4, "Chrome pop token", 100)',
        "midnightToday.plusDays(1).minusNanos",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MainActivity.kt",
        "uiHandler.postDelayed(this, 1000L)",
        '"Armed • 4 lanes"',
        "Details stay in Logs",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/TokenStore.kt",
        "MAX_TOKEN_AGE_MS = 30L * 60L * 1000L",
        "expireIfStale()",
        "hasRequiredCaptures()",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/StartWaitingActivity.kt",
        "if (!tokenStore.hasRequiredCaptures())",
        "stateStore.armWaiting()",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuForegroundService.kt",
        "if (!tokenStore.hasRequiredCaptures())",
        "START_NOT_STICKY",
    )
    require_text(
        "android/app/src/main/java/com/thetechguy/mibu/MibuUiHelpers.kt",
        "fun Activity.mibuPage",
        "fun Activity.mibuCard",
        "fun Activity.mibuButton",
    )

    # PC helper action and hotspot contracts.
    for path in (
        "pc-helper/mibu_pc_helper.py",
        "pc-helper/qt6/mibu_pc_helper_ui.py",
        "pc-helper/qt6/mibu_pc_helper_final.py",
        "pc-helper/qt6/mibu_actions.py",
        "pc-helper/qt6/dependency_check.py",
        "pc-helper/qt6/render_svg_assets.py",
    ):
        check_python(path)
    require_text(
        "pc-helper/qt6/mibu_actions.py",
        "def push_two_tokens_to_phone",
        "def reboot_to_fastboot",
        "def check_fastboot_ready",
    )
    require_text(
        "pc-helper/qt6/mibu_pc_helper_final.py",
        "Paste Two Tokens",
        "Verify Fastboot",
        "01_pc_main_four_button_workflow.png",
        "05_popup_phone_guide.png",
    )
    require_text(
        "pc-helper/build_windows.ps1",
        "render_svg_assets.py",
        "Hotspot UI assets verified.",
        "Release hotspot assets verified.",
    )

    check_svg("resources/expected ui/pc/01_pc_main_four_button_workflow.svg", "1200", "800")
    for name in (
        "02_popup_device_check_guide.svg",
        "03_popup_install_apk.svg",
        "04_popup_login_get_token.svg",
        "05_popup_phone_guide.svg",
    ):
        check_svg(f"resources/expected ui/pc/{name}", "1000", "700")

    print("MIBU source-contract review passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"REVIEW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
