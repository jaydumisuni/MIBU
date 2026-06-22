#!/usr/bin/env python3
from __future__ import annotations

import sys
import traceback
import webbrowser
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # pragma: no cover
    QSoundEffect = None  # type: ignore

from dependency_check import format_checks, run_all_checks
from mibu_actions import (
    check_device_ready,
    install_package,
    launch_phone_app,
    push_session_to_phone,
    start_phone_waiting,
)

BEIJING_ZONE = ZoneInfo('Asia/Shanghai')
TARGET_TIME = time(23, 59, 58, 600000)
LOGIN_URL = 'https://account.xiaomi.com/'


class AppState:
    device_ok = False
    apk_ok = False
    token_ok = False


def app_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def asset_roots() -> list[Path]:
    base = app_base_dir()
    cwd = Path.cwd()
    return [
        base,
        base / 'dist',
        base / 'resources',
        base / 'resources' / 'expected ui',
        base / 'resources' / 'expected ui' / 'pc',
        base / 'resources' / 'expected ui' / 'android',
        base / '_internal',
        base / '_internal' / 'dist',
        base / '_internal' / 'resources',
        base / '_internal' / 'resources' / 'expected ui',
        base / '_internal' / 'resources' / 'expected ui' / 'pc',
        cwd,
        cwd / 'dist',
        cwd / 'resources',
        cwd / 'resources' / 'expected ui',
        cwd / 'resources' / 'expected ui' / 'pc',
        cwd / 'resources' / 'expected ui' / 'android',
    ]


def find_asset(*names: str) -> str:
    for root in asset_roots():
        for name in names:
            candidate = root / name
            if candidate.exists():
                return str(candidate)
    return ''


def bundled_apk_path() -> str:
    return find_asset('MIBU.apk', 'app-debug.apk')


def target_times() -> tuple[str, str]:
    now = datetime.now(BEIJING_ZONE)
    target = datetime.combine(now.date(), TARGET_TIME, tzinfo=BEIJING_ZONE)
    if target <= now:
        target += timedelta(days=1)
    local = target.astimezone()
    return target.strftime('%Y-%m-%d %H:%M:%S.%f %Z'), local.strftime('%Y-%m-%d %H:%M:%S.%f %Z')


class ImageButton(QPushButton):
    def __init__(self, text: str, parent: QWidget, active: bool = False) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName('hotspotActive' if active else 'hotspot')
        self.setToolTip(text)


class ImageDialog(QDialog):
    def __init__(self, parent: 'Window', title: str, image_names: tuple[str, ...]) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(900, 650)
        self.resize(980, 735)
        self.image_path = find_asset(*image_names)
        self.bg = QLabel(self)
        self.bg.setAlignment(Qt.AlignCenter)
        self.bg.setScaledContents(True)
        self.bg.lower()
        self.output = QTextEdit(self)
        self.output.setObjectName('floatingOutput')
        self.output.setReadOnly(True)
        self.output.hide()
        self.hotspots: list[tuple[QPushButton, tuple[float, float, float, float]]] = []
        self.close_btn = ImageButton('×', self, False)
        self.close_btn.clicked.connect(self.reject)
        self.hotspots.append((self.close_btn, (0.925, 0.040, 0.045, 0.060)))
        if not self.image_path:
            self.setObjectName('dialogFallback')
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(24, 22, 24, 18)
            h = QLabel(title)
            h.setObjectName('dialogTitle')
            self.layout.addWidget(h)
            self.fallback_text = QLabel('Image resource missing. Restore resources/expected ui/pc then rebuild. Functional fallback controls are still available.')
            self.fallback_text.setObjectName('dialogCard')
            self.fallback_text.setWordWrap(True)
            self.layout.addWidget(self.fallback_text)
            self.layout.addWidget(self.output)
            self.output.show()

    def add_hotspot(self, text: str, rect: tuple[float, float, float, float], handler, active: bool = False) -> QPushButton:
        button = ImageButton(text, self, active)
        button.clicked.connect(handler)
        self.hotspots.append((button, rect))
        if not self.image_path and hasattr(self, 'layout'):
            self.layout.addWidget(button)
        return button

    def log(self, text: str) -> None:
        self.output.show()
        self.output.append(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.bg.setGeometry(0, 0, self.width(), self.height())
        if self.image_path:
            self.bg.setPixmap(QPixmap(self.image_path))
        for button, rect in self.hotspots:
            x, y, w, h = rect
            button.setGeometry(int(self.width() * x), int(self.height() * y), int(self.width() * w), int(self.height() * h))
        self.output.setGeometry(int(self.width() * 0.10), int(self.height() * 0.68), int(self.width() * 0.80), int(self.height() * 0.14))


class TextFallbackDialog(QDialog):
    def __init__(self, parent: 'Window', title: str, subtitle: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(620)
        self.setObjectName('dialogFallback')
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(24, 22, 24, 18)
        self.v.setSpacing(14)
        h = QLabel(title)
        h.setObjectName('dialogTitle')
        s = QLabel(subtitle)
        s.setObjectName('small')
        self.v.addWidget(h)
        self.v.addWidget(s)

    def card(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName('dialogCard')
        lab.setWordWrap(True)
        lab.setMinimumHeight(46)
        return lab

    def add_buttons(self, buttons: list[tuple[str, callable, bool]]) -> None:
        row = QHBoxLayout()
        row.setSpacing(10)
        for text, handler, primary in buttons:
            b = QPushButton(text)
            b.setObjectName('activeButton' if primary else 'button')
            b.clicked.connect(handler)
            row.addWidget(b)
        self.v.addLayout(row)


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('MIBU PC Helper - THETECHGUY TOOL')
        self.resize(1060, 720)
        self.setMinimumSize(820, 560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._center_once = True
        self.state = AppState()
        self.buttons: dict[str, QPushButton] = {}
        self.hotspots: list[tuple[QPushButton, tuple[float, float, float, float]]] = []
        self.main_image = find_asset(
            '01_pc_main_four_button_workflow.png',
            'futuristic_neon_desktop_app_interface.png',
            'visual-final-four-button-helper.png',
        )
        self.sound_ok = self._sound('TTG_v4_clean_connected_success.wav')
        self.sound_fail = self._sound('TTG_v4_clean_speaker_turn_on.wav')
        if self.main_image:
            self.build_image_ui()
        else:
            self.build_fallback_ui()
        self.theme()
        self.refresh_time(show_log=False)
        self.run_dependency_check(show_log=False)
        self.log('Ready. Image-hotspot mode is active.' if self.main_image else 'Ready. Fallback UI active because main image resource is missing.')

    def _sound(self, filename: str):
        path = find_asset(filename)
        if QSoundEffect and path:
            snd = QSoundEffect(self)
            snd.setSource(QUrl.fromLocalFile(path))
            snd.setVolume(0.7)
            return snd
        return None

    def play_ok(self) -> None:
        if self.sound_ok:
            self.sound_ok.play()

    def play_fail(self) -> None:
        if self.sound_fail:
            self.sound_fail.play()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._center_once and not self.isMaximized():
            self._center_once = False
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)

    def build_image_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        self.bg = QLabel(root)
        self.bg.setScaledContents(True)
        self.bg.setPixmap(QPixmap(self.main_image))
        self.bg.lower()
        self.output = QTextEdit(root)
        self.output.setObjectName('floatingOutput')
        self.output.setReadOnly(True)
        self.output.hide()
        specs = [
            ('Device Check', (0.250, 0.835, 0.180, 0.105), self.show_device_check),
            ('Install APK', (0.435, 0.835, 0.180, 0.105), self.show_install_apk),
            ('Login & Get Token', (0.620, 0.835, 0.200, 0.105), self.show_login_token),
            ('Phone Guide', (0.825, 0.835, 0.155, 0.105), self.show_phone_guide),
        ]
        for name, rect, handler in specs:
            button = ImageButton(name, root)
            button.clicked.connect(handler)
            self.buttons[name] = button
            self.hotspots.append((button, rect))
        self.status = QLabel('Device: Waiting    ADB: Not authorized    APK: Not installed    Token: Not imported', root)
        self.status.setObjectName('floatingStatus')
        self.time_label = QLabel('-', root)
        self.time_label.setObjectName('floatingTime')

    def build_fallback_ui(self) -> None:
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar())
        layout.addWidget(self.main_panel(), 1)
        self.setCentralWidget(root)

    def sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName('side')
        side.setMinimumWidth(230)
        side.setMaximumWidth(290)
        v = QVBoxLayout(side)
        v.setContentsMargins(20, 20, 20, 16)
        v.setSpacing(14)
        logo = QLabel("<div align='center'><span style='font-size:40px;color:#ff7a2b;'>MI</span><span style='font-size:40px;color:#55a8ff;'>BU</span><br><span style='color:#d58a34;'>by THETECHGUY TOOL</span></div>")
        logo.setObjectName('heroBrand')
        logo.setMinimumHeight(160)
        logo.setAlignment(Qt.AlignCenter)
        v.addWidget(logo)
        self.progress = QLabel('Setup Progress\n1 Device Check\n2 Install APK\n3 Login & Get Token\n4 Phone Guide')
        self.progress.setObjectName('card')
        self.progress.setMinimumHeight(140)
        v.addWidget(self.progress)
        help_box = QLabel('Need Help?\nRestore resources/expected ui/pc for exact image UI. Functional fallback remains available.')
        help_box.setObjectName('card')
        help_box.setWordWrap(True)
        v.addWidget(help_box)
        self.dep_status = QLabel('Dependencies\nChecking...')
        self.dep_status.setObjectName('card')
        v.addWidget(self.dep_status)
        v.addStretch(1)
        version = QLabel('THETECHGUY TOOL • v1.0')
        version.setObjectName('brandSub')
        v.addWidget(version)
        return side

    def main_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName('main')
        v = QVBoxLayout(panel)
        v.setContentsMargins(24, 20, 24, 18)
        v.setSpacing(14)
        title = QLabel('Welcome to MIBU PC Helper')
        title.setObjectName('title')
        sub = QLabel('Fallback view. Put your rendered UI images in resources/expected ui/pc to restore the exact look.')
        sub.setObjectName('small')
        v.addWidget(title)
        v.addWidget(sub)
        grid = QGridLayout()
        actions = [
            ('Device Check', 'Check ADB, USB debugging and RSA authorization.', self.show_device_check),
            ('Install APK', 'Install bundled MIBU.apk and open the app.', self.show_install_apk),
            ('Login & Get Token', 'Open browser, then paste/push token to phone.', self.show_login_token),
            ('Phone Guide', 'Open phone app and start waiting bridge.', self.show_phone_guide),
        ]
        for idx, (name, desc, handler) in enumerate(actions):
            grid.addWidget(self.action_card(idx + 1, name, desc), idx // 2, idx % 2)
        v.addLayout(grid)
        self.status = QLabel('Device: Waiting    ADB: Not authorized    APK: Not installed    Token: Not imported')
        self.status.setObjectName('statusBar')
        v.addWidget(self.status)
        self.time_label = QLabel('-')
        self.time_label.setObjectName('time')
        v.addWidget(self.time_label)
        self.output = QTextEdit()
        self.output.setObjectName('output')
        self.output.setReadOnly(True)
        v.addWidget(self.output, 1)
        row = QHBoxLayout()
        for name, _desc, handler in actions:
            b = QPushButton(name)
            b.setObjectName('button')
            b.clicked.connect(handler)
            self.buttons[name] = b
            row.addWidget(b)
        v.addLayout(row)
        footer = QLabel('By the THETECHGUY TOOL team')
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName('brandSub')
        v.addWidget(footer)
        return panel

    def action_card(self, n: int, title: str, desc: str) -> QLabel:
        lab = QLabel(f'<b>{n}. {title}</b><br><span style="color:#94a4c2;">{desc}</span>')
        lab.setObjectName('dialogCard')
        lab.setWordWrap(True)
        lab.setMinimumHeight(82)
        return lab

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, 'bg'):
            root = self.centralWidget()
            self.bg.setGeometry(0, 0, root.width(), root.height())
            for button, rect in self.hotspots:
                x, y, w, h = rect
                button.setGeometry(int(root.width() * x), int(root.height() * y), int(root.width() * w), int(root.height() * h))
            self.output.setGeometry(int(root.width() * 0.255), int(root.height() * 0.690), int(root.width() * 0.500), int(root.height() * 0.115))
            self.status.setGeometry(int(root.width() * 0.250), int(root.height() * 0.600), int(root.width() * 0.520), int(root.height() * 0.045))
            self.time_label.setGeometry(int(root.width() * 0.555), int(root.height() * 0.645), int(root.width() * 0.395), int(root.height() * 0.050))

    def set_active(self, name: str) -> None:
        for key, btn in self.buttons.items():
            btn.setObjectName('hotspotActive' if self.main_image and key == name else ('activeButton' if key == name else 'button'))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def log(self, text: str) -> None:
        self.output.show()
        self.output.append(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def run_dependency_check(self, show_log: bool = True) -> None:
        checks = run_all_checks()
        text = format_checks(checks)
        all_ok = all(item.ok for item in checks)
        if hasattr(self, 'dep_status'):
            self.dep_status.setText('Dependencies\n' + ('All ready' if all_ok else 'Needs attention'))
        if show_log:
            self.log(text)

    def refresh_time(self, show_log: bool = True) -> None:
        bj, loc = target_times()
        self.time_label.setText(f'Beijing: {bj}     Local: {loc}')
        if show_log:
            self.log('Beijing: ' + bj)
            self.log('Local: ' + loc)

    def update_status(self) -> None:
        self.status.setText(
            f'Device: {"Online" if self.state.device_ok else "Waiting"}    '
            f'ADB: {"Authorized" if self.state.device_ok else "Not authorized"}    '
            f'APK: {"Installed" if self.state.apk_ok else "Not installed"}    '
            f'Token: {"Imported" if self.state.token_ok else "Not imported"}'
        )

    def image_dialog(self, title: str, images: tuple[str, ...]) -> ImageDialog | None:
        if find_asset(*images):
            return ImageDialog(self, title, images)
        return None

    def show_device_check(self) -> None:
        self.set_active('Device Check')
        dlg = self.image_dialog('Device Check Guide', ('02_popup_device_check_guide.png', 'mibu_pc_helper_device_check_guide.png'))
        if dlg:
            status = {'label': 'waiting'}
            def recheck() -> None:
                result = check_device_ready()
                self.log(result.message)
                dlg.log(result.message)
                self.state.device_ok = result.ok
                self.update_status()
                self.play_ok() if result.ok else self.play_fail()
            dlg.add_hotspot('Open ADB Help', (0.420, 0.835, 0.210, 0.075), lambda: webbrowser.open('https://developer.android.com/tools/adb'))
            dlg.add_hotspot('Recheck Device', (0.650, 0.835, 0.250, 0.075), recheck, True)
            dlg.exec()
            return
        fallback = TextFallbackDialog(self, 'Device Check Guide', 'Get ADB online before continuing.')
        for step in [
            '1. Connect phone by USB. Use a good USB cable.',
            '2. Enable USB debugging in Developer Options.',
            '3. Accept the USB debugging warning and tap OK.',
            '4. Accept the RSA prompt, tick “Always allow”, and tap OK.',
        ]:
            fallback.v.addWidget(fallback.card(step))
        def recheck_fb() -> None:
            result = check_device_ready()
            self.log(result.message)
            self.state.device_ok = result.ok
            self.update_status()
            self.play_ok() if result.ok else self.play_fail()
        fallback.add_buttons([('Open ADB Help', lambda: webbrowser.open('https://developer.android.com/tools/adb'), False), ('Recheck Device', recheck_fb, True)])
        fallback.exec()

    def show_install_apk(self) -> None:
        self.set_active('Install APK')
        dlg = self.image_dialog('Install MIBU.apk', ('03_popup_install_apk.png', 'neon_themed_mibu_install_interface.png'))
        current_path = {'path': bundled_apk_path()}
        def browse() -> None:
            path, _ = QFileDialog.getOpenFileName(self, 'Select MIBU APK', '', 'Android APK (*.apk)')
            if path:
                current_path['path'] = path
                self.log('Selected APK: ' + path)
                if dlg:
                    dlg.log('Selected APK: ' + path)
        def install() -> None:
            path = current_path['path']
            msg = 'APK path: ' + (path or 'not found')
            self.log(msg)
            if dlg:
                dlg.log(msg)
            if not path:
                self.play_fail()
                return
            result = install_package(path)
            self.log(result.message or 'No output')
            if dlg:
                dlg.log(result.message or 'No output')
            self.state.apk_ok = result.ok
            if result.ok:
                launch = launch_phone_app()
                self.log('Open app: ' + launch.message)
                if dlg:
                    dlg.log('Open app: ' + launch.message)
                self.play_ok()
            else:
                self.play_fail()
            self.update_status()
        if dlg:
            dlg.add_hotspot('Browse APK', (0.430, 0.795, 0.210, 0.075), browse)
            dlg.add_hotspot('Install APK', (0.660, 0.795, 0.230, 0.075), install, True)
            dlg.exec()
            return
        fallback = TextFallbackDialog(self, 'Install MIBU.apk', 'Push the bundled Android app to the connected phone.')
        fallback.v.addWidget(fallback.card('Device must be online. APK is searched from bundled dist/MIBU.apk first.'))
        fallback.add_buttons([('Browse APK', browse, False), ('Install APK', install, True)])
        fallback.exec()

    def show_login_token(self) -> None:
        self.set_active('Login & Get Token')
        dlg = self.image_dialog('Login & Get Token', ('04_popup_login_get_token.png', 'mibu_pc_helper_login_setup.png'))
        def open_browser() -> None:
            ok = webbrowser.open(LOGIN_URL)
            self.log('Browser open result: ' + str(ok))
            self.log('Login URL: ' + LOGIN_URL)
            if dlg:
                dlg.log('Browser opened. User logs in themselves.')
        def paste_push() -> None:
            token, ok = QInputDialog.getText(self, 'Manual Token / Session Import', 'Paste approved token/session:', QLineEdit.Password)
            if not ok:
                return
            result = push_session_to_phone(token)
            self.log(result.message)
            if dlg:
                dlg.log(result.message)
            self.state.token_ok = result.ok
            self.update_status()
            self.play_ok() if result.ok else self.play_fail()
        if dlg:
            dlg.add_hotspot('Open Chrome / Browser', (0.180, 0.770, 0.200, 0.080), open_browser)
            dlg.add_hotspot('Open Brave / Browser', (0.405, 0.770, 0.190, 0.080), open_browser)
            dlg.add_hotspot('Paste / Push Token', (0.620, 0.770, 0.300, 0.080), paste_push, True)
            dlg.exec()
            return
        fallback = TextFallbackDialog(self, 'Login & Get Token', 'External browser login. MIBU never asks for the password.')
        fallback.v.addWidget(fallback.card('1. Open browser\n2. User logs into Xiaomi\n3. Copy/approve token/session\n4. Paste/push token to phone'))
        fallback.add_buttons([('Open Browser', open_browser, False), ('Paste / Push Token', paste_push, True)])
        fallback.exec()

    def show_phone_guide(self) -> None:
        self.set_active('Phone Guide')
        dlg = self.image_dialog('Continue on Phone', ('05_popup_phone_guide.png', 'mibu_pc_helper_interface_concept.png'))
        def open_app() -> None:
            result = launch_phone_app()
            self.log(result.message)
            if dlg:
                dlg.log(result.message)
            self.play_ok() if result.ok else self.play_fail()
        def start_wait() -> None:
            result = start_phone_waiting()
            self.log(result.message)
            if dlg:
                dlg.log(result.message)
            self.play_ok() if result.ok else self.play_fail()
        if dlg:
            dlg.add_hotspot('Open MIBU', (0.130, 0.800, 0.240, 0.080), open_app)
            dlg.add_hotspot('Start Phone Waiting', (0.390, 0.800, 0.280, 0.080), start_wait, True)
            dlg.add_hotspot('Done', (0.700, 0.800, 0.200, 0.080), dlg.accept)
            dlg.exec()
            return
        fallback = TextFallbackDialog(self, 'Continue on Phone', 'After login and token handoff, finish from the Android app.')
        fallback.v.addWidget(fallback.card('1. Open MIBU on phone\n2. Confirm session imported\n3. Check status\n4. Keep mobile data on\n5. Tap Start Waiting'))
        fallback.add_buttons([('Open MIBU', open_app, False), ('Start Phone Waiting', start_wait, True), ('Done', fallback.accept, False)])
        fallback.exec()

    def theme(self) -> None:
        self.setStyleSheet('''
        QWidget { background:#050913; color:#f4f6fa; font-family: Segoe UI, Arial; }
        #side { background:#090f1d; border-right:1px solid #162038; }
        #main { background:#070b15; }
        #title { font-size:30px; font-weight:800; }
        #small { color:#b7c2d6; font-size:13px; }
        #brandSub { color:#d58a34; font-size:11px; letter-spacing:1px; }
        #heroBrand { background:#0b1120; border:1px solid #293657; border-radius:18px; }
        #card, #dialogCard, #statusBar { background:#0d1423; border:1px solid #1c2841; border-radius:14px; padding:12px; }
        #dialogTitle { font-size:24px; font-weight:800; }
        #time { color:#55a8ff; font-weight:700; font-size:12px; }
        #button { background:#0e1728; border:1px solid #28426a; border-radius:12px; padding:11px 12px; font-size:13px; }
        #button:hover { border:1px solid #55a8ff; }
        #activeButton { background:#101629; border:2px solid #ff7a2b; border-radius:12px; padding:11px 12px; font-size:13px; color:#ffffff; }
        #hotspot { background:rgba(0,0,0,0); border:0px; color:rgba(255,255,255,0); }
        #hotspot:hover { background:rgba(85,168,255,30); border:1px solid #55a8ff; border-radius:14px; color:rgba(255,255,255,0); }
        #hotspotActive { background:rgba(255,122,43,25); border:2px solid #ff7a2b; border-radius:14px; color:rgba(255,255,255,0); }
        #floatingOutput, #output { background:rgba(6,10,18,205); color:#dbe7ff; border:1px solid #1c2841; border-radius:10px; font-family: Consolas, monospace; font-size:11px; }
        #floatingStatus, #floatingTime { background:rgba(6,10,18,180); color:#dbe7ff; border:1px solid #1c2841; border-radius:8px; padding:6px; font-size:11px; }
        #dialogFallback { background:#07101d; }
        ''')


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('MIBU PC Helper')
    app.setFont(QFont('Segoe UI', 9))
    window = Window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
