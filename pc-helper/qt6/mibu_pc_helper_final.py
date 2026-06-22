#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import traceback
import webbrowser
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont
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
    list_devices,
    package_exists,
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


def find_asset(*names: str) -> str:
    base = app_base_dir()
    candidates: list[Path] = []
    for name in names:
        candidates.extend([
            base / name,
            base / 'dist' / name,
            base / '_internal' / name,
            base / '_internal' / 'dist' / name,
            Path.cwd() / name,
            Path.cwd() / 'dist' / name,
            Path.cwd() / 'resources' / 'expected ui' / name,
            Path.cwd() / 'resources' / 'expected ui' / 'android' / name,
        ])
    for path in candidates:
        if path.exists():
            return str(path)
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


class NeonDialog(QDialog):
    def __init__(self, parent: 'Window', title: str, subtitle: str, active: str) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(620)
        self.setObjectName('dialog')
        self.active = active
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(24, 22, 24, 18)
        self.v.setSpacing(14)
        header = QHBoxLayout()
        h = QLabel(title)
        h.setObjectName('dialogTitle')
        s = QLabel(subtitle)
        s.setObjectName('small')
        col = QVBoxLayout()
        col.addWidget(h)
        col.addWidget(s)
        header.addLayout(col, 1)
        close = QPushButton('×')
        close.setObjectName('xButton')
        close.setFixedSize(42, 36)
        close.clicked.connect(self.reject)
        header.addWidget(close)
        self.v.addLayout(header)

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
        self.setMinimumSize(920, 620)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._center_once = True
        self.state = AppState()
        self.buttons: dict[str, QPushButton] = {}
        self.sound_ok = self._sound('TTG_v4_clean_connected_success.wav')
        self.sound_fail = self._sound('TTG_v4_clean_speaker_turn_on.wav')
        self.build_ui()
        self.theme()
        self.refresh_time(show_log=False)
        self.run_dependency_check(show_log=False)
        self.log('Ready. Use the four workflow buttons. Every popup now has real clickable controls.')

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

    def build_ui(self) -> None:
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
        self.progress = QLabel('Setup Progress\n1 Prepare Device\n2 Install & Connect\n3 Login & Get Token\n4 Hand Off to Phone')
        self.progress.setObjectName('card')
        self.progress.setMinimumHeight(140)
        v.addWidget(self.progress)
        help_box = QLabel('Need Help?\nUse Device Check first. If the phone asks for USB/RSA permission, accept it on the phone and recheck.')
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
        sub = QLabel('This tool prepares your device, installs MIBU, guides login, then hands off to your phone so the app can take over.')
        sub.setObjectName('small')
        v.addWidget(title)
        v.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(12)
        actions = [
            ('Device Check', 'Check ADB, guide USB debugging, and confirm RSA authorization.', self.show_device_check),
            ('Install APK', 'Use the bundled installer flow to push MIBU.apk to the phone.', self.show_install_apk),
            ('Login & Get Token', 'Open browser login, wait for token, then push it to MIBU.', self.show_login_token),
            ('Phone Guide', 'Show phone-side steps and continue waiting from the phone.', self.show_phone_guide),
        ]
        for idx, (name, desc, handler) in enumerate(actions):
            card = self.action_card(idx + 1, name, desc)
            grid.addWidget(card, idx // 2, idx % 2)
        v.addLayout(grid)

        self.status = QLabel('Device: No device / Waiting    ADB: Not authorized    APK: Not installed    Token: Not imported')
        self.status.setObjectName('statusBar')
        v.addWidget(self.status)
        self.time_label = QLabel('-')
        self.time_label.setObjectName('time')
        v.addWidget(self.time_label)
        self.output = QTextEdit()
        self.output.setObjectName('output')
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(100)
        v.addWidget(self.output, 1)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        for name, _desc, handler in actions:
            b = QPushButton(name)
            b.setObjectName('button')
            b.clicked.connect(handler)
            self.buttons[name] = b
            btns.addWidget(b)
        v.addLayout(btns)
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

    def set_active(self, name: str) -> None:
        for key, btn in self.buttons.items():
            btn.setObjectName('activeButton' if key == name else 'button')
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def log(self, text: str) -> None:
        self.output.append(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def safe_call(self, name: str, func) -> None:
        try:
            self.log(f'\n> {name}')
            func()
        except Exception:
            self.play_fail()
            self.log('ERROR:\n' + traceback.format_exc())

    def run_dependency_check(self, show_log: bool = True) -> None:
        checks = run_all_checks()
        text = format_checks(checks)
        all_ok = all(item.ok for item in checks)
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
            f'Device: {"Online" if self.state.device_ok else "No device / Waiting"}    '
            f'ADB: {"Authorized" if self.state.device_ok else "Not authorized"}    '
            f'APK: {"Installed" if self.state.apk_ok else "Not installed"}    '
            f'Token: {"Imported" if self.state.token_ok else "Not imported"}'
        )

    def show_device_check(self) -> None:
        self.set_active('Device Check')
        dlg = NeonDialog(self, 'Device Check Guide', 'Get ADB online before continuing.', 'Device Check')
        steps = [
            '1. Connect phone by USB\nUse a good USB cable and connect your phone to this computer.',
            '2. Enable USB debugging in Developer Options\nSettings > About phone > tap Build number 7 times > Developer Options > USB debugging.',
            '3. Accept the warning and tap OK\nThe phone may show a Danger / USB debugging warning. Read it and tap OK.',
            '4. Accept the RSA prompt\nTick “Always allow from this computer” and tap OK.',
        ]
        for step in steps:
            dlg.v.addWidget(dlg.card(step))
        status = QLabel('Current status: Waiting for device or authorization')
        status.setObjectName('statusBar')
        dlg.v.addWidget(status)

        def recheck() -> None:
            result = check_device_ready()
            self.log(result.message)
            status.setText('Current status: Device online' if result.ok else 'Current status: ' + result.message.split('\n')[0])
            self.state.device_ok = result.ok
            self.update_status()
            self.play_ok() if result.ok else self.play_fail()

        dlg.add_buttons([
            ('Open ADB Help', lambda: webbrowser.open('https://developer.android.com/tools/adb'), False),
            ('Recheck Device', recheck, True),
        ])
        dlg.exec()

    def show_install_apk(self) -> None:
        self.set_active('Install APK')
        dlg = NeonDialog(self, 'Install MIBU.apk', 'Push the bundled Android app to the connected phone.', 'Install APK')
        info = QLabel('ADB found: checking\nDevice connected: checking\nDevice authorized: checking\nBundled MIBU.apk: checking\nReady to install: waiting')
        info.setObjectName('dialogCard')
        dlg.v.addWidget(info)
        log_box = QTextEdit()
        log_box.setObjectName('output')
        log_box.setReadOnly(True)
        log_box.setMinimumHeight(110)
        dlg.v.addWidget(log_box)
        current_path = {'path': bundled_apk_path()}

        def browse() -> None:
            path, _ = QFileDialog.getOpenFileName(self, 'Select MIBU APK', '', 'Android APK (*.apk)')
            if path:
                current_path['path'] = path
                info.setText(info.text() + f'\nSelected APK: {path}')

        def install() -> None:
            path = current_path['path']
            log_box.append('APK path: ' + (path or 'not found'))
            if not path:
                self.play_fail()
                log_box.append('No APK found. Browse to MIBU.apk or rebuild the bundle.')
                return
            result = install_package(path)
            log_box.append(result.message or 'No output')
            self.log(result.message or 'No install output')
            self.state.apk_ok = result.ok
            if result.ok:
                launch = launch_phone_app()
                log_box.append('\nOpen app:\n' + launch.message)
                self.play_ok()
            else:
                self.play_fail()
            self.update_status()

        dlg.add_buttons([('Browse APK', browse, False), ('Install APK', install, True)])
        dlg.exec()

    def show_login_token(self) -> None:
        self.set_active('Login & Get Token')
        dlg = NeonDialog(self, 'Login & Get Token', 'Use external browser login, then push/import the approved token to the phone.', 'Login & Get Token')
        dlg.v.addWidget(dlg.card('1. Open Chrome or Brave\n2. User logs into Xiaomi account\n3. MIBU waits for the approved token/session\n4. Token is sent to MIBU on the phone'))
        dlg.v.addWidget(dlg.card('External browser recommended. The user signs in themselves. MIBU does not ask for the password.'))
        state = QLabel('Current state: Waiting to open browser')
        state.setObjectName('statusBar')
        dlg.v.addWidget(state)

        def open_default() -> None:
            ok = webbrowser.open(LOGIN_URL)
            state.setText('Current state: Browser opened' if ok else 'Current state: Browser open failed')
            self.log('Login URL: ' + LOGIN_URL)

        def paste_push() -> None:
            token, ok = QInputDialog.getText(self, 'Manual Token / Session Import', 'Paste approved token/session:', QLineEdit.Password)
            if not ok:
                return
            result = push_session_to_phone(token)
            self.log(result.message)
            self.state.token_ok = result.ok
            self.update_status()
            state.setText('Current state: Token pushed to phone' if result.ok else 'Current state: Token push failed')
            self.play_ok() if result.ok else self.play_fail()

        dlg.add_buttons([
            ('Open Browser', open_default, False),
            ('Paste / Push Token', paste_push, True),
        ])
        dlg.exec()

    def show_phone_guide(self) -> None:
        self.set_active('Phone Guide')
        dlg = NeonDialog(self, 'Continue on Phone', 'After login and token handoff, finish from the Android app.', 'Phone Guide')
        dlg.v.addWidget(dlg.card('1. Open MIBU on the phone\n2. Confirm session imported\n3. Check account status\n4. Review Beijing and local target time\n5. Keep mobile data on and tap Start Waiting'))
        dlg.v.addWidget(dlg.card('The waiting stage now continues on the phone. Do not close MIBU or turn off mobile data.'))

        def open_app() -> None:
            result = launch_phone_app()
            self.log(result.message)
            self.play_ok() if result.ok else self.play_fail()

        def start_wait() -> None:
            result = start_phone_waiting()
            self.log(result.message)
            self.play_ok() if result.ok else self.play_fail()

        dlg.add_buttons([('Open MIBU', open_app, False), ('Start Phone Waiting', start_wait, True), ('Done', dlg.accept, False)])
        dlg.exec()

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
        #dialog { background:#07101d; border:1px solid #28426a; border-radius:18px; }
        #dialogTitle { font-size:24px; font-weight:800; }
        #time { color:#55a8ff; font-weight:700; font-size:12px; }
        #button { background:#0e1728; border:1px solid #28426a; border-radius:12px; padding:11px 12px; font-size:13px; }
        #button:hover { border:1px solid #55a8ff; }
        #activeButton { background:#101629; border:2px solid #ff7a2b; border-radius:12px; padding:11px 12px; font-size:13px; color:#ffffff; }
        #xButton { background:#101629; border:1px solid #344b77; border-radius:10px; font-size:20px; }
        #output { background:#060a12; color:#dbe7ff; border:1px solid #1c2841; border-radius:10px; font-family: Consolas, monospace; font-size:11px; }
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
