from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ui_geometry import SCREENS


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


def close_enough(actual: tuple[int, int, int, int], expected: tuple[int, int, int, int], tolerance: int = 2) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


def validate(asset_dir: Path) -> None:
    errors: list[str] = []
    for screen_name, screen in SCREENS.items():
        svg_path = asset_dir / screen.svg
        if not svg_path.exists():
            errors.append(f"Missing required SVG: {svg_path}")
            continue
        root = ET.parse(svg_path).getroot()
        if int(float(root.attrib.get("width", 0))) != screen.width or int(float(root.attrib.get("height", 0))) != screen.height:
            errors.append(f"Wrong canvas size for {screen.svg}")
        rects, all_text = rects_and_text(svg_path)
        for label, expected in screen.hotspots.items():
            artwork_label = "LOGIN & GET TOKENS" if label == "Login & Get Token" else label.upper()
            if norm(artwork_label) not in all_text:
                errors.append(f"Missing button label {artwork_label!r} in {screen.svg}")
            if not any(close_enough(rect, expected) for rect in rects):
                errors.append(f"No artwork rectangle aligns with {label!r} hotspot in {screen.svg}: expected {expected}")
        if not screen.hotspots:
            errors.append(f"No hotspots defined for {screen_name}")
    if errors:
        raise RuntimeError("UI contract validation failed:\n- " + "\n- ".join(errors))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    asset_dir = repo_root / "resources" / "expected ui" / "pc"
    validate(asset_dir)
    print(f"UI contract valid for {len(SCREENS)} screens from one geometry source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
