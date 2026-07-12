from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ButtonContract:
    label: str
    rect: tuple[int, int, int, int]


@dataclass(frozen=True)
class ScreenContract:
    svg: str
    png: str
    width: int
    height: int
    buttons: tuple[ButtonContract, ...]


SCREENS = (
    ScreenContract(
        "01_pc_main_four_button_workflow.svg", "01_pc_main_four_button_workflow.png", 1200, 800,
        (
            ButtonContract("DEVICE CHECK", (300, 668, 205, 84)),
            ButtonContract("INSTALL APK", (522, 668, 205, 84)),
            ButtonContract("LOGIN & GET TOKENS", (744, 668, 235, 84)),
            ButtonContract("PHONE GUIDE", (996, 668, 170, 84)),
        ),
    ),
    ScreenContract(
        "02_popup_device_check_guide.svg", "02_popup_device_check_guide.png", 1000, 700,
        (ButtonContract("OPEN ADB HELP", (420, 585, 210, 55)), ButtonContract("RECHECK DEVICE", (650, 585, 250, 55))),
    ),
    ScreenContract(
        "03_popup_install_apk.svg", "03_popup_install_apk.png", 1000, 700,
        (ButtonContract("BROWSE APK", (430, 558, 210, 60)), ButtonContract("INSTALL APK", (660, 558, 230, 60))),
    ),
    ScreenContract(
        "04_popup_login_get_token.svg", "04_popup_login_get_token.png", 1000, 700,
        (
            ButtonContract("OPEN BROWSER", (180, 575, 200, 58)),
            ButtonContract("PASTE ONE", (405, 575, 190, 58)),
            ButtonContract("PASTE TWO TOKENS", (620, 575, 260, 58)),
        ),
    ),
    ScreenContract(
        "05_popup_phone_guide.svg", "05_popup_phone_guide.png", 1000, 700,
        (
            ButtonContract("OPEN MIBU", (80, 565, 200, 58)),
            ButtonContract("START WAITING", (310, 565, 220, 58)),
            ButtonContract("VERIFY FASTBOOT", (560, 565, 230, 58)),
            ButtonContract("DONE", (820, 565, 110, 58)),
        ),
    ),
)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).upper()


def rects_and_text(svg_path: Path) -> tuple[list[tuple[int, int, int, int]], str]:
    root = ET.parse(svg_path).getroot()
    rects: list[tuple[int, int, int, int]] = []
    text_parts: list[str] = []
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "rect" and all(key in elem.attrib for key in ("x", "y", "width", "height")):
            rects.append(tuple(int(round(float(elem.attrib[key]))) for key in ("x", "y", "width", "height")))
        if tag == "text" and elem.text:
            text_parts.append(elem.text)
    return rects, norm(" ".join(text_parts))


def close_enough(actual: tuple[int, int, int, int], expected: tuple[int, int, int, int], tolerance: int = 6) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


def validate(asset_dir: Path) -> None:
    errors: list[str] = []
    for screen in SCREENS:
        svg_path = asset_dir / screen.svg
        if not svg_path.exists():
            errors.append(f"Missing required SVG: {svg_path}")
            continue
        root = ET.parse(svg_path).getroot()
        if int(float(root.attrib.get("width", 0))) != screen.width or int(float(root.attrib.get("height", 0))) != screen.height:
            errors.append(f"Wrong canvas size for {screen.svg}")
        rects, all_text = rects_and_text(svg_path)
        for button in screen.buttons:
            if norm(button.label) not in all_text:
                errors.append(f"Missing button label {button.label!r} in {screen.svg}")
            if not any(close_enough(rect, button.rect) for rect in rects):
                errors.append(f"No artwork rectangle aligns with {button.label!r} hotspot in {screen.svg}: expected {button.rect}")
    if errors:
        raise RuntimeError("UI contract validation failed:\n- " + "\n- ".join(errors))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    asset_dir = repo_root / "resources" / "expected ui" / "pc"
    validate(asset_dir)
    print(f"UI contract valid for {len(SCREENS)} screens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
