#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

BEIJING_ZONE = ZoneInfo('Asia/Shanghai')
TARGET_TIME = time(23, 59, 58, 600000)


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
        status = QLabel('Pending')
        status.setObjectName('pill')
        status.setAlignment(Qt.AlignCenter)
        status.setFixedWidth(90)
        row.addWidget(status)


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('MIBU PC Helper')
        self.resize(980, 640)
        self._center_once = True
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar())
        layout.addWidget(self.main(), 1)
        self.setCentralWidget(root)
        self.theme()
        self.refresh_time()

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
        progress = QLabel('Progress\n0%')
        progress.setObjectName('card')
        progress.setFixedHeight(90)
        v.addWidget(progress)
        help_box = QLabel('Need help?\nFollow each step carefully. Keep the helper small, centered, and clean.')
        help_box.setObjectName('card')
        help_box.setWordWrap(True)
        help_box.setFixedHeight(130)
        v.addWidget(help_box)
        v.addStretch(1)
        v.addWidget(QLabel('v1.0.0'))
        return side

    def main(self) -> QWidget:
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
        sub = QLabel('Follow the steps below to prepare your Xiaomi device using the approved MIBU flow.')
        sub.setObjectName('small')
        v.addWidget(sub)
        for n, t, d in [
            (1, 'Device checklist', 'Check device, OS version and account requirements.'),
            (2, 'Connection check', 'Connect your phone and confirm the PC can see it.'),
            (3, 'Install MIBU.apk', 'Install the phone-side app from this helper.'),
            (4, 'Import to phone', 'Move the prepared session into the phone app.'),
            (5, 'Timing guide', 'Show Beijing time and matching local time.'),
        ]:
            v.addWidget(Step(n, t, d))
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
        for text in ['Guide', 'Refresh Time', 'Next']:
            b = QPushButton(text)
            b.setObjectName('primary' if text == 'Next' else 'button')
            if text == 'Refresh Time':
                b.clicked.connect(self.refresh_time)
            buttons.addWidget(b)
        v.addLayout(buttons)
        footer = QLabel('By the THETECHGUY TOOL team')
        footer.setAlignment(Qt.AlignCenter)
        footer.setObjectName('muted')
        v.addWidget(footer)
        return panel

    def refresh_time(self) -> None:
        bj, loc = target_times()
        self.bj.setText('Beijing target: ' + bj)
        self.loc.setText('Local target: ' + loc)

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
        #primary { background:#1e58ff; border:1px solid #4b72ff; border-radius:12px; padding:10px 24px; font-weight:800; }
        ''')


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('MIBU PC Helper')
    app.setFont(QFont('Segoe UI', 10))
    w = Window()
    w.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
