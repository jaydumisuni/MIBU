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
        row.setContentsMargins(10, 7, 10, 7)
        row.setSpacing(10)
        badge = QLabel(str(n))
        badge.setObjectName('badge')
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(26, 26)
        row.addWidget(badge)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        name = QLabel(title)
        name.setObjectName('stepTitle')
        small = QLabel(desc)
        small.setObjectName('small')
        small.setWordWrap(False)
        col.addWidget(name)
        col.addWidget(small)
        row.addLayout(col, 1)
        self.status = QLabel('Pending')
        self.status.setObjectName('pill')
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setFixedWidth(70)
        row.addWidget(self.status)

    def set_status(self, text: str) -> None:
        self.status.setText(text)


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('MIBU PC Helper - THETECHGUY TOOL')
        self.resize(760, 520)
        self.setMinimumSize(720, 500)
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
        side.setFixedWidth(178)
        v = QVBoxLayout(side)
        v.setContentsMargins(16, 16, 16, 14)
        v.setSpacing(10)
        logo = QLabel("<span style='color:#ff7a2b;'>MI</span><span style='color:#ffffff;'>BU</span>")
        logo.setObjectName('brand')
        v.addWidget(logo)
        fam = QLabel('THETECHGUY TOOL')
        fam.setObjectName('brandSub')
        v.addWidget(fam)
        hero = QLabel("<div align='center'><span style='color:#ff7a2b;'>MI</span><br><span style='color:#ffffff;font-size:30px;'>◉</span><br><span style='color:#55a8ff;'>BU</span><br><span style='color:#bd4dff;font-size:18px;'>UNLOCK</span></div>")
        hero.setObjectName('heroBrand')
        hero.setAlignment(Qt.AlignCenter)
        hero.setFixedHeight(122)
        v.addWidget(hero)
        self.progress = QLabel('Progress\n0%')
        self.progress.setObjectName('card')
        self.progress.setFixedHeight(58)
        v.addWidget(self.progress)
        self.dep_status = QLabel('Dependencies\nChecking...')
        self.dep_status.setObjectName('card')
        self.dep_status.setWordWrap(True)
        self.dep_status.setFixedHeight(82)
        v.addWidget(self.dep_status)
        help_box = QLabel('Need help?\nLogin in browser, then install and open MIBU.')
        help_box.setObjectName('card')
        help_box.setWordWrap(True)
        help_box.setFixedHeight(82)
        v.addWidget(help_box)
        v.addStretch(1)
        version = QLabel('THETECHGUY TOOL • v1.0')
        version.setObjectName('brandSub')
        v.addWidget(version)
        return side

    def main_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName('main')
        v = QVBoxLayout(panel)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(10)
        crumb = QLabel('THETECHGUY TOOL  >  MIBU HELPER')
        crumb.setObjectName('crumb')
        v.addWidget(crumb)
        title = QLabel("<span style='color:#ff7a2b;'>MI</span><span style='color:#55a8ff;'>BU</span> <span style='color:#ffffff;'>PC Helper</span>")
        title.setObjectName('title')
        v.addWidget(title)
        sub = QLabel('Small guided setup. User logs in themselves; MIBU only imports the explicit token/session.')
        sub.setObjectName('small')
        v.addWidget(sub)
        steps = [
            (1, 'Browser login', 'Open normal login page.'),
            (2, 'Connection check', 'Confirm ADB sees the phone.'),
            (3, 'Install MIBU.apk', 'Install phone-side app.'),
            (4, 'Open on phone', 'Launch MIBU on device.'),
            (5, 'Timing guide', 'Beijing and local target time.'),
        ]
        for item in steps:
            row = Step(*item)
            self.rows.append(row)
            v.addWidget(row)
        times = QFrame()
        times.setObjectName('cardFrame')
        tv = QVBoxLayout(times)
        tv.setContentsMargins(12, 9, 12, 9)
        tv.setSpacing(3)
        ref = QLabel('Time reference')
        ref.setObjectName('cardTitle')
        tv.addWidget(ref)
        self.bj = QLabel('-')
        self.loc = QLabel('-')
        self.bj.setObjectName('time')
        self.loc.setObjectName('time')
        tv.addWidget(self.bj)
        tv.addWidget(self.loc)
        v.addWidget(times)
        buttons = QHBoxLayout()
        buttons.setSpacing(7)
        for text, handler in [
            ('Deps', self.run_dependency_check),
            ('Login', self.open_login),
            ('Device', self.check_device),
            ('Install', self.install_apk),
            ('Open', self.open_app),
            ('Time', self.refresh_time),
        ]:
            b = QPushButton(text)
            b.setObjectName('button')
            b.clicked.connect(handler)
            buttons.addWidget(b)
        v.addLayout(buttons)
        footer = QLabel('By the THETECHGUY TOOL team')
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName('brandSub')
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
        self.bj.setText('Beijing: ' + bj)
        self.loc.setText('Local: ' + loc)
        self.rows[4].set_status('Ready')
        self.progress_update()

    def theme(self) -> None:
        self.setStyleSheet('''
        QWidget { background:#050913; color:#f4f6fa; font-family: Segoe UI, Arial; }
        #side { background:#090f1d; border-right:1px solid #162038; }
        #main { background:#070b15; }
        #brand { font-size:28px; font-weight:900; letter-spacing:1px; }
        #brandSub { color:#d58a34; font-size:10px; letter-spacing:1px; }
        #muted, #small { color:#94a4c2; font-size:11px; }
        #heroBrand { background:#0b1120; border:1px solid #293657; border-radius:15px; font-size:21px; font-weight:800; }
        #card, #cardFrame { background:#0d1423; border:1px solid #1c2841; border-radius:13px; padding:9px; }
        #cardTitle { color:#f4f6fa; font-size:11px; }
        #crumb { color:#d58a34; font-size:10px; letter-spacing:1px; }
        #title { font-size:28px; font-weight:800; }
        #step { background:#0c1321; border:1px solid #1a2740; border-radius:13px; }
        #badge { background:#0f1930; border:1px solid #334a78; border-radius:13px; color:#6bc1ff; font-size:13px; font-weight:800; }
        #stepTitle { font-size:16px; font-weight:700; }
        #pill { background:#172131; border:1px solid #283a56; border-radius:11px; padding:4px; color:#c9d5ea; font-size:11px; }
        #time { color:#55a8ff; font-weight:700; font-size:11px; }
        #button { background:#0e1728; border:1px solid #28426a; border-radius:10px; padding:8px 10px; font-size:11px; }
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
