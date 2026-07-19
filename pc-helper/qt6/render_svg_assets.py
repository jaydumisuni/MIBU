from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from ui_geometry import SCREENS


def render(svg_path: Path, png_path: Path, width: int, height: int, background: QColor | None = None) -> None:
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {svg_path}")
    image = QImage(QSize(width, height), QImage.Format_ARGB32)
    image.fill(background or QColor(5, 9, 19))
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


def render_icon(asset_dir: Path) -> None:
    approved_logo = asset_dir.parent / "logo 1_transparent.png"
    svg_path = asset_dir / "mibu_app_icon.svg"
    png_path = asset_dir / "mibu_app_icon.png"
    ico_path = asset_dir / "mibu_app_icon.ico"
    if approved_logo.is_file():
        with Image.open(approved_logo) as logo:
            logo = logo.convert("RGBA")
            logo.thumbnail((512, 512), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            x = (512 - logo.width) // 2
            y = (512 - logo.height) // 2
            canvas.alpha_composite(logo, (x, y))
            canvas.save(png_path, "PNG")
        print(f"Rendered approved logo -> {png_path.name} ({png_path.stat().st_size} bytes)")
    else:
        if not svg_path.is_file():
            raise FileNotFoundError(f"Required app icon SVG missing: {svg_path}")
        render(svg_path, png_path, 512, 512, QColor(0, 0, 0, 0))
    with Image.open(png_path) as source:
        source = source.convert("RGBA")
        source.save(
            ico_path,
            format="ICO",
            sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    if not ico_path.is_file() or ico_path.stat().st_size <= 0:
        raise RuntimeError(f"Generated ICO is missing or empty: {ico_path}")
    print(f"Rendered {svg_path.name} -> {ico_path.name} ({ico_path.stat().st_size} bytes)")


def main() -> int:
    existing_app = QGuiApplication.instance()
    app = existing_app or QGuiApplication(sys.argv[:1])
    owns_app = existing_app is None
    try:
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
        render_icon(asset_dir)
        return 0
    finally:
        if owns_app:
            app.quit()


if __name__ == "__main__":
    raise SystemExit(main())
