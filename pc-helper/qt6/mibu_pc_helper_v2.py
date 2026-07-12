#!/usr/bin/env python3
from __future__ import annotations

import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # pragma: no cover
    QSoundEffect = None  # type: ignore

from dependency_check import format_checks, run_all_checks
from mibu_actions import (
    check_device_ready,
    check_fastboot_ready,
    fastboot_oem_info,
    install_package,
    launch_phone_app,
    push_session_to_phone,
    push_two_tokens_to_phone,
    reboot_to_fastboot,
    start_phone_waiting,
)

BEIJING_ZONE = ZoneInfo("Asia/Shanghai")
TARGET_TIME = time(23, 59, 58, 600000)
LOGIN_URL = "https://account.xiaomi.com/"


def app_base_dir() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def asset_roots() -> list[Path]:
    base = app_base_dir()
    cwd = Path.cwd()
    roots = [base, cwd]
    expanded: list[Path] = []
    for root in roots:
        expanded.extend([
            root,
            root / "dist",
            root / "resources",
            root / "resources" / "expected ui",
            root / "resources" / "expected ui" / "pc",
            root / "_internal",
            root / "_internal" / "dist",
            root / "_internal" / "resources" / "expected ui" / "pc",
        ])
    return expanded


def find_asset(*names: str) -> str:
    for root in asset_roots():
        for name in names:
            candidate = root / name
            if candidate.is_file():
                return str(candidate)
    return ""


def required_asset(name: str) -> str:
    path = find_asset(name)
    if not path:
        raise FileNotFoundError(f"Required MIBU UI asset missing: {name}")
    return path


def next_target() -> datetime:
    now = datetime.now(BEIJING_ZONE)
    target = datetime.combine(now.date(), TARGET_TIME, tzinfo=BEIJING_ZONE)
    return target if target > now else target + timedelta(days=1)


@dataclass
class AppState:
    device_ok: bool = False
    apk_ok: bool = False
    tokens_ok: bool = False
    fastboot_ok: bool = False


class HotspotButton(QPushButton):
    def __init__(self, label: str, parent: QWidget, active: bool = False) -> None:
        super().__init__(label, parent)
        self.setObjectName("hotspotActive" if active else "hotspot")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(label)


class WorkflowDialog(QDialog):
    def __init__(self, parent: "Window", title: str, image_name: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(900, 650)
        self.resize(1000, 700)
        self.image_path = required_asset(image_name)
        self.bg = QLabel(self)
        self.bg.setScaledContents(True)
        self.bg.setPixmap(QPixmap(self.image_path))
        self.bg.lower()
        self.status = QLabel("Ready", self)
        self.status.setObjectName("dialogStatus")
        self.status.setWordWrap(False)
        self.hotspots: list[tuple[QPushButton, tuple[float, float, float, float]]] = []
        close = HotspotButton("Close", self)
        close.clicked.connect(self.reject)
        self.hotspots.append((close, (0.925, 0.035, 0.050, 0.065)))

    def add_hotspot(
        self,
        label: str,
        rect: tuple[float, float, float, float],
        callback: Callable[[], None],
        active: bool = False,
    ) -> None:
        button = HotspotButton(label, self, active)
        button.clicked.connect(callback)
        self.hotspots.append((button, rect))

    def set_status(self, message: str) -> None:
        one_line = "  •  ".join(part.strip() for part in message.splitlines() if part.strip())
        self.status.setText(one_line or "Done")
        self.status.setToolTip(message)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.bg.setGeometry(0, 0, self.width(), self.height())
        for button, (x, y, w, h) in self.hotspots:
            button.setGeometry(int(self.width() * x), int(self.height() * y), int(self.width() * w), int(self.height() * h))
        self.status.setGeometry(int(self.width() * 0.07), int(self.height() * 0.745), int(self.width() * 0.86), int(self.height() * 0.045))


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MIBU PC Helper — THETECHGUY TOOL")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.state = AppState()
        self.buttons: dict[str, QPushButton] = {}
        self.hotspots: list[tuple[QPushButton, tuple[float, float, float, float]]] = []
        self.main_image = required_asset("01_pc_main_four_button_workflow.png")
        self.sound_ok = self._sound("TTG_v4_clean_connected_success.wav")
        self.sound_fail = self._sound("TTG_v4_clean_speaker_turn_on.wav")
        self._build_ui()
        self._theme()
        self._update_time()
        self._dependency_review()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)

    def _sound(self, name: str):
        path = find_asset(name)
        if not path or QSoundEffect is None:
            return None
        sound = QSoundEffect(self)
        sound.setSource(QUrl.fromLocalFile(path))
        sound.setVolume(0.7)
        return sound

    def _play(self, ok: bool) -> None:
        sound = self.sound_ok if ok else self.sound_fail
        if sound:
            sound.play()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        self.bg = QLabel(root)
        self.bg.setScaledContents(True)
        self.bg.setPixmap(QPixmap(self.main_image))
        self.bg.lower()
        self.output = QPlainTextEdit(root)
        self.output.setObjectName("floatingOutput")
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(250)
        self.status = QLabel(root)
        self.status.setObjectName("floatingStatus")
        self.time_label = QLabel(root)
        self.time_label.setObjectName("floatingTime")

        specs = [
            ("Device Check", (0.250, 0.835, 0.171, 0.105), self.show_device_check),
            ("Install APK", (0.435, 0.835, 0.171, 0.105), self.show_install_apk),
            ("Login & Get Token", (0.620, 0.835, 0.196, 0.105), self.show_login_token),
            ("Phone Guide", (0.830, 0.835, 0.142, 0.105), self.show_phone_guide),
        ]
        for name, rect, handler in specs:
            button = HotspotButton(name, root)
            button.clicked.connect(handler)
            self.buttons[name] = button
            self.hotspots.append((button, rect))
        self._update_status()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        root = self.centralWidget()
        self.bg.setGeometry(0, 0, root.width(), root.height())
        for button, (x, y, w, h) in self.hotspots:
            button.setGeometry(int(root.width() * x), int(root.height() * y), int(root.width() * w), int(root.height() * h))
        self.status.setGeometry(int(root.width() * 0.083), int(root.height() * 0.382), int(root.width() * 0.834), int(root.height() * 0.055))
        self.time_label.setGeometry(int(root.width() * 0.083), int(root.height() * 0.705), int(root.width() * 0.834), int(root.height() * 0.045))
        self.output.setGeometry(int(root.width() * 0.083), int(root.height() * 0.535), int(root.width() * 0.834), int(root.height() * 0.145))

    def _theme(self) -> None:
        self.setStyleSheet("""
        QWidget { background:#050913; color:#f5f7fb; font-family:'Segoe UI',Arial; }
        #hotspot { background:rgba(0,0,0,0); border:0; color:rgba(0,0,0,0); }
        #hotspot:hover { background:rgba(83,168,255,28); border:1px solid #53a8ff; border-radius:16px; color:rgba(0,0,0,0); }
        #hotspotActive { background:rgba(255,122,43,24); border:2px solid #ff7a2b; border-radius:16px; color:rgba(0,0,0,0); }
        #floatingOutput { background:rgba(6,11,21,210); border:1px solid #243b67; border-radius:12px; color:#d9e6fb; font-family:Consolas; font-size:11px; padding:8px; }
        #floatingStatus, #floatingTime, #dialogStatus { background:rgba(6,11,21,215); border:1px solid #243b67; border-radius:9px; color:#d9e6fb; padding:6px; font-size:11px; }
        """)

    def _set_active(self, name: str) -> None:
        for key, button in self.buttons.items():
            button.setObjectName("hotspotActive" if key == name else "hotspot")
            button.style().unpolish(button)
            button.style().polish(button)

    def _log(self, message: str) -> None:
        self.output.appendPlainText(message)
        bar = self.output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _dependency_review(self) -> None:
        checks = run_all_checks()
        self._log(format_checks(checks))
        if not all(item.ok for item in checks):
            self._log("Dependencies need attention before device actions.")

    def _update_time(self) -> None:
        target = next_target()
        local = target.astimezone()
        remaining = max(0, int((target - datetime.now(BEIJING_ZONE)).total_seconds()))
        h, rem = divmod(remaining, 3600)
        m, s = divmod(rem, 60)
        self.time_label.setText(
            f"Beijing target: {target:%Y-%m-%d %H:%M:%S.%f %Z}   |   Local: {local:%Y-%m-%d %H:%M:%S.%f %Z}   |   Remaining: {h:02d}:{m:02d}:{s:02d}"
        )

    def _update_status(self) -> None:
        self.status.setText(
            f"Device: {'Online' if self.state.device_ok else 'Waiting'}   "
            f"ADB: {'Authorized' if self.state.device_ok else 'Not authorized'}   "
            f"APK: {'Installed' if self.state.apk_ok else 'Not installed'}   "
            f"Tokens: {'Imported' if self.state.tokens_ok else 'Not imported'}   "
            f"Verify: {'Fastboot detected' if self.state.fastboot_ok else 'Not started'}"
        )

    def show_device_check(self) -> None:
        self._set_active("Device Check")
        dialog = WorkflowDialog(self, "Device Check", "02_popup_device_check_guide.png")

        def recheck() -> None:
            result = check_device_ready()
            self.state.device_ok = result.ok
            self._update_status()
            self._log(result.message)
            dialog.set_status(result.message)
            self._play(result.ok)

        dialog.add_hotspot("Open ADB Help", (0.420, 0.835, 0.210, 0.075), lambda: webbrowser.open("https://developer.android.com/tools/adb"))
        dialog.add_hotspot("Recheck Device", (0.650, 0.835, 0.250, 0.075), recheck, True)
        dialog.exec()

    def show_install_apk(self) -> None:
        self._set_active("Install APK")
        dialog = WorkflowDialog(self, "Install MIBU APK", "03_popup_install_apk.png")
        selected = {"path": find_asset("MIBU.apk", "app-debug.apk")}

        def browse() -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Select MIBU APK", "", "Android APK (*.apk)")
            if path:
                selected["path"] = path
                dialog.set_status(f"Selected: {path}")

        def install() -> None:
            path = selected["path"]
            if not path:
                message = "No APK found. Build Android or browse to the APK."
                dialog.set_status(message)
                self._log(message)
                self._play(False)
                return
            result = install_package(path)
            self.state.apk_ok = result.ok
            self._update_status()
            self._log(result.message)
            dialog.set_status(result.message)
            if result.ok:
                launched = launch_phone_app()
                self._log(f"Open app: {launched.message}")
            self._play(result.ok)

        dialog.add_hotspot("Browse APK", (0.430, 0.795, 0.210, 0.075), browse)
        dialog.add_hotspot("Install APK", (0.660, 0.795, 0.230, 0.075), install, True)
        dialog.exec()

    def show_login_token(self) -> None:
        self._set_active("Login & Get Token")
        dialog = WorkflowDialog(self, "Login & Get Tokens", "04_popup_login_get_token.png")

        def open_browser() -> None:
            opened = webbrowser.open(LOGIN_URL)
            message = f"Browser open result: {opened}. User logs in themselves."
            self._log(message)
            dialog.set_status(message)

        def paste_one() -> None:
            token, accepted = QInputDialog.getText(self, "Single Token Import", "Paste one token/session:", QLineEdit.Password)
            if not accepted:
                return
            result = push_session_to_phone(token)
            self.state.tokens_ok = result.ok
            self._update_status()
            self._log(result.message)
            dialog.set_status(result.message)
            self._play(result.ok)

        def paste_two() -> None:
            service, accepted = QInputDialog.getText(self, "Firefox Service Token", "Paste Firefox new_bbs_serviceToken:", QLineEdit.Password)
            if not accepted:
                return
            pop, accepted = QInputDialog.getText(self, "Chrome Pop Token", "Paste Chrome popRunToken:", QLineEdit.Password)
            if not accepted:
                return
            result = push_two_tokens_to_phone(service, pop)
            self.state.tokens_ok = result.ok
            self._update_status()
            self._log(result.message)
            dialog.set_status(result.message)
            self._play(result.ok)

        dialog.add_hotspot("Open Browser", (0.180, 0.820, 0.200, 0.083), open_browser)
        dialog.add_hotspot("Paste One", (0.405, 0.820, 0.190, 0.083), paste_one)
        dialog.add_hotspot("Paste Two Tokens", (0.620, 0.820, 0.300, 0.083), paste_two, True)
        dialog.exec()

    def show_phone_guide(self) -> None:
        self._set_active("Phone Guide")
        dialog = WorkflowDialog(self, "Continue on Phone", "05_popup_phone_guide.png")

        def report(result) -> None:
            self._log(result.message)
            dialog.set_status(result.message)
            self._play(result.ok)

        def open_app() -> None:
            report(launch_phone_app())

        def start_wait() -> None:
            report(start_phone_waiting())

        def verify_fastboot() -> None:
            reboot = reboot_to_fastboot()
            report(reboot)
            if not reboot.ok:
                return
            detected = check_fastboot_ready()
            self.state.fastboot_ok = detected.ok
            self._update_status()
            report(detected)
            if not detected.ok:
                return
            info = fastboot_oem_info()
            self._log(info.message)
            dialog.set_status("Fastboot detected. Continue with the official Mi Unlock Tool.")

        dialog.add_hotspot("Open MIBU", (0.080, 0.800, 0.200, 0.083), open_app)
        dialog.add_hotspot("Start Waiting", (0.300, 0.800, 0.220, 0.083), start_wait, True)
        dialog.add_hotspot("Verify Fastboot", (0.540, 0.800, 0.230, 0.083), verify_fastboot)
        dialog.add_hotspot("Done", (0.790, 0.800, 0.120, 0.083), dialog.accept)
        dialog.exec()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MIBU PC Helper")
    app.setFont(QFont("Segoe UI", 9))
    try:
        window = Window()
    except Exception as exc:
        print(f"MIBU startup failed: {exc}", file=sys.stderr)
        return 2
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
