from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from ui_geometry import SCREENS


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
    if not png_path.is_file() or png_path.stat().st_size <= 0:
        raise RuntimeError(f"Rendered PNG is missing or empty: {png_path}")
    print(f"Rendered {svg_path.name} -> {png_path.name} ({png_path.stat().st_size} bytes)")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    asset_dir = repo_root / "resources" / "expected ui" / "pc"
    seen_outputs: set[str] = set()
    for screen_name, screen in SCREENS.items():
        if screen.png in seen_outputs:
            raise RuntimeError(f"Duplicate PNG output in geometry contract: {screen.png}")
        seen_outputs.add(screen.png)
        svg_path = asset_dir / screen.svg
        if not svg_path.is_file():
            raise FileNotFoundError(f"Required hotspot SVG missing for {screen_name}: {svg_path}")
        render(svg_path, asset_dir / screen.png, screen.width, screen.height)
    if len(seen_outputs) != 5:
        raise RuntimeError(f"Expected exactly five required UI screens, found {len(seen_outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
