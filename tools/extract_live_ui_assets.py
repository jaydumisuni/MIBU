from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "resources" / "expected ui"
SHARED_OUT = ROOT / "resources" / "live_ui"
ANDROID_OUT = ROOT / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi"


def neon_cutout_rect(
    source: Path,
    box: tuple[int, int, int, int],
    output: Path,
    output_size: tuple[int, int],
) -> None:
    image = Image.open(source).convert("RGBA").crop(box)
    pixels = []
    for red, green, blue, source_alpha in image.getdata():
        peak = max(red, green, blue)
        floor = min(red, green, blue)
        chroma = peak - floor
        # Mockup artwork sits on near-black. Convert that black plate into a
        # soft alpha matte while retaining colored neon glow and white detail.
        strength = max(0, peak - 20) + int(max(0, chroma - 4) * 0.5)
        alpha = min(255, strength * 5)
        pixels.append((red, green, blue, min(source_alpha, alpha)))
    image.putdata(pixels)
    alpha = image.getchannel("A")
    bounds = alpha.getbbox()
    if bounds:
        image = image.crop(bounds)
    image.thumbnail(output_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", output_size, (0, 0, 0, 0))
    canvas.alpha_composite(image, ((output_size[0] - image.width) // 2, (output_size[1] - image.height) // 2))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, "PNG", optimize=True)


def neon_cutout(source: Path, box: tuple[int, int, int, int], output: Path, size: int) -> None:
    neon_cutout_rect(source, box, output, (size, size))


def copy_approved_logo() -> None:
    source_path = ROOT / "resources" / "logo.png"
    if not source_path.is_file():
        source_path = EXPECTED / "logo 1_transparent.png"
    source = Image.open(source_path).convert("RGBA")
    source.thumbnail((512, 512), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.alpha_composite(source, ((512 - source.width) // 2, (512 - source.height) // 2))
    for output in (SHARED_OUT / "mibu_logo.png", ANDROID_OUT / "mibu_logo_live.png"):
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, "PNG", optimize=True)
    canvas.save(
        SHARED_OUT / "mibu_app_icon.ico",
        "ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> int:
    pc = EXPECTED / "01_pc_main_four_button_workflow.png"
    dashboard = EXPECTED / "02_android_dashboard_waiting.png"

    copy_approved_logo()
    neon_cutout(pc, (925, 58, 1428, 690), SHARED_OUT / "mibu_hood.png", 640)
    neon_cutout(pc, (925, 58, 1428, 690), ANDROID_OUT / "mibu_hood_live.png", 640)
    neon_cutout_rect(dashboard, (305, 135, 595, 240), ANDROID_OUT / "mibu_wordmark_live.png", (420, 132))

    pc_icons = {
        "device": (372, 199, 456, 283),
        "install": (372, 323, 456, 407),
        "account": (372, 448, 456, 532),
        "guide": (372, 575, 456, 659),
    }
    for name, box in pc_icons.items():
        neon_cutout(pc, box, SHARED_OUT / f"icon_{name}.png", 128)
        neon_cutout(pc, box, ANDROID_OUT / f"mibu_icon_{name}.png", 128)

    android_icons = {
        "check": (116, 493, 200, 580),
        "session": (116, 604, 200, 692),
        "clock": (485, 725, 560, 802),
        "signal": (112, 1138, 198, 1217),
        "shield": (112, 1250, 198, 1338),
        "logs": (116, 1505, 196, 1590),
        "info": (492, 1505, 570, 1590),
        "settings": (772, 122, 846, 198),
    }
    for name, box in android_icons.items():
        neon_cutout(dashboard, box, ANDROID_OUT / f"mibu_icon_{name}.png", 128)

    print(f"Live UI assets written to {SHARED_OUT} and {ANDROID_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
