from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def render(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {svg_path}")
    image = QImage(QSize(width, height), QImage.Format_ARGB32)
    image.fill(QColor(5, 9, 19))
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(png_path), "PNG"):
        raise RuntimeError(f"Could not write PNG: {png_path}")
    print(f"Rendered {svg_path.name} -> {png_path.name}")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    asset_dir = repo_root / "resources" / "expected ui" / "pc"
    jobs = [
        ("01_pc_main_four_button_workflow.svg", "01_pc_main_four_button_workflow.png", 1200, 800),
        ("02_popup_device_check_guide.svg", "02_popup_device_check_guide.png", 1000, 700),
        ("03_popup_install_apk.svg", "03_popup_install_apk.png", 1000, 700),
        ("04_popup_login_get_token.svg", "04_popup_login_get_token.png", 1000, 700),
        ("05_popup_phone_guide.svg", "05_popup_phone_guide.png", 1000, 700),
    ]
    for svg_name, png_name, width, height in jobs:
        svg_path = asset_dir / svg_name
        if not svg_path.exists():
            raise FileNotFoundError(f"Required hotspot SVG missing: {svg_path}")
        render(svg_path, asset_dir / png_name, width, height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
