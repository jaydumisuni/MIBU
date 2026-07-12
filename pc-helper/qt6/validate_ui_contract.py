from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ui_geometry import SCREENS

ACTIVE_ORANGE = {"#ff7a2b", "#FF7A2B"}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).upper()


def element_rect(elem: ET.Element) -> tuple[int, int, int, int] | None:
    if all(key in elem.attrib for key in ("x", "y", "width", "height")):
        return tuple(int(round(float(elem.attrib[key]))) for key in ("x", "y", "width", "height"))
    return None


def inspect_svg(svg_path: Path) -> tuple[list[tuple[tuple[int, int, int, int], dict[str, str]]], str, bool]:
    root = ET.parse(svg_path).getroot()
    rects: list[tuple[tuple[int, int, int, int], dict[str, str]]] = []
    text_parts: list[str] = []
    close_circle = False
    close_cross = False
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "rect":
            rect = element_rect(elem)
            if rect is not None:
                rects.append((rect, dict(elem.attrib)))
        elif tag == "text" and elem.text:
            text_parts.append(elem.text)
        elif tag == "circle":
            close_circle = (
                abs(float(elem.attrib.get("cx", 0)) - 950.0) <= 3
                and abs(float(elem.attrib.get("cy", 0)) - 55.0) <= 3
                and float(elem.attrib.get("r", 0)) >= 16
            ) or close_circle
        elif tag == "path":
            path_data = elem.attrib.get("d", "")
            if "M942 47" in path_data and "L958 63" in path_data and "M958 47" in path_data:
                close_cross = True
    return rects, norm(" ".join(text_parts)), close_circle and close_cross


def close_enough(actual: tuple[int, int, int, int], expected: tuple[int, int, int, int], tolerance: int = 2) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(actual, expected))


def validate(asset_dir: Path) -> None:
    errors: list[str] = []
    if len(SCREENS) != 5:
        errors.append(f"Expected five screens in geometry contract, found {len(SCREENS)}")

    seen_svgs: set[str] = set()
    seen_pngs: set[str] = set()
    for screen_name, screen in SCREENS.items():
        if screen.svg in seen_svgs:
            errors.append(f"Duplicate SVG contract: {screen.svg}")
        if screen.png in seen_pngs:
            errors.append(f"Duplicate PNG contract: {screen.png}")
        seen_svgs.add(screen.svg)
        seen_pngs.add(screen.png)

        svg_path = asset_dir / screen.svg
        if not svg_path.is_file():
            errors.append(f"Missing required SVG: {svg_path}")
            continue
        root = ET.parse(svg_path).getroot()
        if int(float(root.attrib.get("width", 0))) != screen.width or int(float(root.attrib.get("height", 0))) != screen.height:
            errors.append(f"Wrong canvas size for {screen.svg}")

        rects, all_text, visible_close = inspect_svg(svg_path)
        if screen_name != "main" and not visible_close:
            errors.append(f"Popup {screen.svg} has no visible close affordance aligned with the Qt close hotspot")

        for label, expected in screen.hotspots.items():
            artwork_label = "LOGIN & GET TOKENS" if label == "Login & Get Token" else label.upper()
            if norm(artwork_label) not in all_text:
                errors.append(f"Missing button label {artwork_label!r} in {screen.svg}")

            matches = [(rect, attrs) for rect, attrs in rects if close_enough(rect, expected)]
            if len(matches) != 1:
                errors.append(
                    f"Expected exactly one artwork rectangle for {label!r} in {screen.svg}; "
                    f"found {len(matches)} at expected {expected}"
                )
                continue
            _, attrs = matches[0]
            if attrs.get("stroke") in ACTIVE_ORANGE:
                errors.append(
                    f"Button {label!r} in {screen.svg} has baked orange active styling. "
                    "Active glow must come only from the clicked Qt hotspot."
                )

        if not screen.hotspots:
            errors.append(f"No hotspots defined for {screen_name}")

    if errors:
        raise RuntimeError("UI contract validation failed:\n- " + "\n- ".join(errors))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    asset_dir = repo_root / "resources" / "expected ui" / "pc"
    validate(asset_dir)
    print(f"UI contract valid for {len(SCREENS)} screens; close affordances align and active glow is not baked in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
