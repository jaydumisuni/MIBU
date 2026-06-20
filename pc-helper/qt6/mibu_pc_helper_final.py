#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import webbrowser
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget

from dependency_check import format_checks, run_all_checks
from mibu_actions import install_package, launch_phone_app, list_devices

BEIJING_ZONE = ZoneInfo('Asia/Shanghai')
TARGET_TIME = time(23, 59, 58, 600000)
LOGIN_URL = 'https://account.xiaomi.com/'
DEFAULT_APK = os.path.join(os.getcwd(), 'dist', 'MIBU.apk')


def target_times() -> tuple[str, str]:
    now = datetime.now(BEIJING_ZONE)
    target = datetime.combine(now.date(), TARGET_TIME, tzinfo=BEIJING_ZONE)
    if target <= now:
        target += timedelta(days=1)
    local = target.astimezone()
    return target.strftime('%Y-%m-%d %H:%M:%S.%f %Z'), local.strftime('%Y-%m-%d %H:%M:%S.%f %Z')


class Step(QFrame):
    def __init__(self, n: int, title: str, desc: str) -> None:
        super().__init__()
        self.setObjectName('step')
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        badge = QLabel(str(n))
        badge.setObjectName('badge')
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(34, 34)
        row.addWidget(badge)
        col = QVBoxLayout()
        name = QLabel(title)
        name.setObjectName('stepTitle')
        small = QLabel(desc)
        small.setObjectName('small')
        small.setWordWrap(True)
        col.addWidget(name)
        col.addWidget(small)
        row.addLayout(col, 1)
        self.status = QLabel('Pending')
        self.status.setObjectName('pill')
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setFixedWidth(92)
        row.addWidget(self.status)

    def set_status(self, text: str) -> None:
        self.status.setText(text)


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('MIBU PC Helper')
        self.resize(980, 640)
        self._center_once = True
        self.rows: list[Step] = []
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar())
        layout.addWidget(self.main_panel(), 1)
        self.setCentralWidget(root)
        self.theme()
        self.refresh_time()
        self.run_dependency_check(show_popup=False)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._center_once:
            self._center_once = False
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)

    def sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName('side')
        v = QVBoxLayout(side)
        v.setContentsMargins(24, 24, 24, 24)
        logo = QLabel('MIBU')
        logo.setObjectName('brand')
        v.addWidget(logo)
        fam = QLabel('THETECHGUY TOOL')
        fam.setObjectName('muted')
        v.addWidget(fam)
        ghost = QLabel('mi   BU')
        ghost.setObjectName('ghost')
        ghost.setAlignment(Qt.AlignCenter)
        ghost.setFixedHeight(150)
        v.addWidget(ghost)
        self.progress = QLabel('Progress\n0%')
        self.progress.setObjectName('card')
        self.progress.setFixedHeight(90)
        v.addWidget(self.progress)
        self.dep_status = QLabel('Dependencies\nChecking...')
        self.dep_status.setObjectName('card')
        self.dep_status.setWordWrap(True)
        self.dep_status.setFixedHeight(150)
        v.addWidget(self.dep_status)
        help_box = QLabel('Need help?\nLogin yourself in the browser, then use this helper to install and open MIBU.')
        help_box.setObjectName('card')
        help_box.setWordWrap(True)
        help_box.setFixedHeight(110)
        v.addWidget(help_box)
        v.addStretch(1)
        v.addWidget(QLabel('v1.0.0'))
        return side

    def main_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName('main')
        v = QVBoxLayout(panel)
        v.setContentsMargins(30, 26, 30, 22)
        v.setSpacing(16)
        crumb = QLabel('THETECHGUY TOOLS  >  MIBU PC HELPER  >  SETUP WIZARD')
        crumb.setObjectName('crumb')
        v.addWidget(crumb)
        title = QLabel("Welcome to <span style='color:#ff7a2b;'>M</span><span style='color:#bd4dff;'>I</span><span style='color:#55a8ff;'>BU</span> PC Helper")
        title.setObjectName('title')
        v.addWidget(title)
        sub = QLabel('Follow the steps below. The user logs in themselves; MIBU only handles explicit token/session import and device setup.')
        sub.setObjectName('small')
        v.addWidget(sub)
        steps = [
            (1, 'Browser login', 'Open the normal login page. User logs in themselves.'),
            (2, 'Connection check', 'Connect phone and confirm the PC can see it.'),
            (3, 'Install MIBU.apk', 'Install the phone-side app from this helper.'),
            (4, 'Open on phone', 'Launch MIBU on the connected phone.'),
            (5, 'Timing guide', 'Show Beijing time and matching local time.'),
        ]
        for item in steps:
            row = Step(*item)
            self.rows.append(row)
            v.addWidget(row)
        times = QFrame()
        times.setObjectName('cardFrame')
        tv = QVBoxLayout(times)
        tv.addWidget(QLabel('Time reference'))
        self.bj = QLabel('-')
        self.loc = QLabel('-')
        self.bj.setObjectName('time')
        self.loc.setObjectName('time')
        tv.addWidget(self.bj)
        tv.addWidget(self.loc)
        v.addWidget(times)
        buttons = QHBoxLayout()
        for text, handler in [
            ('Check Deps', self.run_dependency_check),
            ('Open Login', self.open_login),
            ('Check Device', self.check_device),
            ('Install APK', self.install_apk),
            ('Open App', self.open_app),
            ('Refresh Time', self.refresh_time),
        ]:
            b = QPushButton(text)
            b.setObjectName('button')
            b.clicked.connect(handler)
            buttons.addWidget(b)
        v.addLayout(buttons)
        footer = QLabel('By the THETECHGUY TOOL team')
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName('muted')
        v.addWidget(footer)
        return panel

    def progress_update(self) -> None:
        done = sum(1 for row in self.rows if row.status.text() in ('Ready', 'Done'))
        self.progress.setText(f'Progress\n{int(done / len(self.rows) * 100)}%')

    def run_dependency_check(self, show_popup: bool = True) -> None:
        checks = run_all_checks()
        text = format_checks(checks)
        all_ok = all(item.ok for item in checks)
        self.dep_status.setText('Dependencies\n' + ('All ready' if all_ok else 'Needs attention'))
        if show_popup:
            QMessageBox.information(self, 'Dependency check', text)

    def open_login(self) -> None:
        webbrowser.open(LOGIN_URL)
        self.rows[0].set_status('Ready')
        self.progress_update()
        QMessageBox.information(self, 'Login', 'Browser opened. Log in yourself, then continue in MIBU.')

    def check_device(self) -> None:
        result = list_devices()
        ok = result.ok and '\tdevice' in result.message
        self.rows[1].set_status('Ready' if ok else 'Waiting')
        self.progress_update()
        QMessageBox.information(self, 'Device check', result.message or 'No output')

    def install_apk(self) -> None:
        path = DEFAULT_APK if os.path.exists(DEFAULT_APK) else ''
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, 'Select MIBU APK', '', 'Android APK (*.apk)')
        if not path:
            return
        result = install_package(path)
        self.rows[2].set_status('Done' if result.ok else 'Failed')
        self.progress_update()
        QMessageBox.information(self, 'Install APK', result.message or 'No output')

    def open_app(self) -> None:
        result = launch_phone_app()
        self.rows[3].set_status('Done' if result.ok else 'Failed')
        self.progress_update()
        QMessageBox.information(self, 'Open MIBU', result.message or 'No output')

    def refresh_time(self) -> None:
        bj, loc = target_times()
        self.bj.setText('Beijing target: ' + bj)
        self.loc.setText('Local target: ' + loc)
        self.rows[4].set_status('Ready')
        self.progress_update()

    def theme(self) -> None:
        self.setStyleSheet('''
        QWidget { background:#050913; color:#f4f6fa; font-family: Segoe UI, Arial; }
        #side { background:#090f1d; border-right:1px solid #162038; }
        #main { background:#070b15; }
        #brand { font-size:34px; font-weight:800; }
        #muted, #small { color:#94a4c2; font-size:13px; }
        #ghost { background:#0b1120; border:1px solid #293657; border-radius:18px; color:#b17cff; font-size:34px; }
        #card, #cardFrame { background:#0d1423; border:1px solid #1c2841; border-radius:16px; padding:14px; }
        #crumb { color:#d58a34; font-size:12px; }
        #title { font-size:32px; font-weight:800; }
        #step { background:#0c1321; border:1px solid #1a2740; border-radius:16px; }
        #badge { background:#0f1930; border:1px solid #334a78; border-radius:17px; color:#6bc1ff; font-size:16px; font-weight:800; }
        #stepTitle { font-size:20px; font-weight:700; }
        #pill { background:#172131; border:1px solid #283a56; border-radius:14px; padding:6px; color:#c9d5ea; }
        #time { color:#55a8ff; font-weight:700; }
        #button { background:#0e1728; border:1px solid #28426a; border-radius:12px; padding:10px 16px; }
        ''')


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('MIBU PC Helper')
    app.setFont(QFont('Segoe UI', 10))
    window = Window()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
