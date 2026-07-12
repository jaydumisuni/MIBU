from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenGeometry:
    svg: str
    png: str
    width: int
    height: int
    hotspots: dict[str, tuple[int, int, int, int]]

    def normalized(self, label: str) -> tuple[float, float, float, float]:
        x, y, w, h = self.hotspots[label]
        return x / self.width, y / self.height, w / self.width, h / self.height


SCREENS: dict[str, ScreenGeometry] = {
    "main": ScreenGeometry(
        "01_pc_main_four_button_workflow.svg", "01_pc_main_four_button_workflow.png", 1200, 800,
        {
            "Device Check": (300, 668, 205, 84),
            "Install APK": (522, 668, 205, 84),
            "Login & Get Token": (744, 668, 235, 84),
            "Phone Guide": (996, 668, 170, 84),
        },
    ),
    "device": ScreenGeometry(
        "02_popup_device_check_guide.svg", "02_popup_device_check_guide.png", 1000, 700,
        {
            "Open ADB Help": (420, 585, 210, 55),
            "Recheck Device": (650, 585, 250, 55),
        },
    ),
    "install": ScreenGeometry(
        "03_popup_install_apk.svg", "03_popup_install_apk.png", 1000, 700,
        {
            "Browse APK": (430, 558, 210, 60),
            "Install APK": (660, 558, 230, 60),
        },
    ),
    "login": ScreenGeometry(
        "04_popup_login_get_token.svg", "04_popup_login_get_token.png", 1000, 700,
        {
            "Open Browser": (180, 539, 200, 56),
            "Paste One": (405, 539, 190, 56),
            "Paste Two Tokens": (620, 539, 300, 56),
        },
    ),
    "phone": ScreenGeometry(
        "05_popup_phone_guide.svg", "05_popup_phone_guide.png", 1000, 700,
        {
            "Open MIBU": (80, 560, 200, 56),
            "Start Waiting": (300, 560, 220, 56),
            "Verify Fastboot": (540, 560, 230, 56),
            "Done": (790, 560, 120, 56),
        },
    ),
}
