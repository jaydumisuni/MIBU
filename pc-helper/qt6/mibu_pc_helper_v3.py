#!/usr/bin/env python3
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QFileInfo, QObject, QPoint, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizeGrip,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtMultimedia import QSoundEffect
except Exception:  # pragma: no cover - optional runtime multimedia support
    QSoundEffect = None  # type: ignore[assignment]

from dependency_check import format_checks, run_all_checks
from mibu_actions import (
    Result,
    check_binding_recovery_compatibility,
    check_device_ready,
    install_package,
    installed_package_version,
    launch_phone_app,
    launch_mi_unlock_status,
    launch_token_import,
    launch_unlock_methods,
    push_two_tokens_to_phone,
    run_adb_user_command,
    start_phone_waiting,
)
from mibu_runtime import (
    AppState,
    BEIJING_ZONE,
    LOGIN_URL,
    find_asset,
    next_target,
    browser_path,
    open_or_install_browser,
)
from mibu_status import PhoneStatus, query_phone_status


WINDOW_SIZE = QSize(760, 560)
MINIMUM_SIZE = QSize(720, 520)


def live_asset(name: str) -> str:
    path = find_asset(name, f"live_ui/{name}")
    if not path:
        raise FileNotFoundError(f"Required live MIBU asset missing: {name}")
    return path


class FunctionWorker(QObject):
    finished = Signal(object)

    def __init__(self, function: Callable[[], object]) -> None:
        super().__init__()
        self.function = function

    def run(self) -> None:
        try:
            value = self.function()
        except Exception as exc:  # pragma: no cover - GUI safety boundary
            value = Result(False, f"Action failed unexpectedly: {exc}")
        self.finished.emit(value)


class AssistantWorker(QObject):
    step = Signal(str, str)
    finished = Signal(object)

    def __init__(self, apk_path: str) -> None:
        super().__init__()
        self.apk_path = apk_path

    def run(self) -> None:
        try:
            result = self._run_flow()
        except Exception as exc:  # pragma: no cover - GUI safety boundary
            result = Result(False, f"One Click Assist failed unexpectedly: {exc}")
        self.finished.emit(result)

    def _run_flow(self) -> Result:
        self.step.emit("Device Check", "Checking USB debugging and ADB authorization...")
        device = check_device_ready()
        if not device.ok:
            return Result(False, "Connect the phone, enable USB debugging, accept the RSA prompt, then press Continue One Click.\n\n" + device.message)

        self.step.emit("Install APK", "Installing and verifying the bundled MIBU APK...")
        if not self.apk_path or not Path(self.apk_path).is_file():
            return Result(False, "The bundled MIBU.apk is missing from this release.")
        installed = install_package(self.apk_path)
        if not installed.ok:
            return Result(False, "Android needs your approval on the phone installer screen. Approve it, then press Continue One Click.\n\n" + installed.message)

        self.step.emit("Install APK", "Opening the verified MIBU app on the phone...")
        opened = launch_phone_app()
        if not opened.ok:
            return opened

        self.step.emit("Login & Get Token", "Checking the phone session state...")
        status_result, status = query_phone_status()
        if not status_result.ok or status is None:
            return Result(False, "MIBU opened, but its live status could not be confirmed.\n\n" + status_result.message)
        if status.timing_complete:
            return Result(True, "The phone confirms the timing stage is complete. Continue with official verification.")
        if status.verification in {"WAIT_TIME_SHOWN", "ACCOUNT_DEVICE_NOT_ADDED", "COMMUNITY_AUTH_REQUIRED", "UNLOCKED"}:
            return Result(True, f"The phone already records the official result: {status.verification}.")

        if not status.captures_ready:
            launch_token_import()
            self.step.emit("Login & Get Token", "Opening your installed browsers for the user-approved login handoff...")
            chrome = open_or_install_browser("chrome")
            firefox = open_or_install_browser("firefox")
            return Result(
                False,
                "PC preparation is complete. The phone import screen and your browsers are open. Import the two approved captures, then press Continue One Click.\n\n"
                + chrome + "\n" + firefox,
            )

        self.step.emit("Phone Guide", "Starting the phone waiting service and checking proof...")
        waiting = start_phone_waiting()
        if not waiting.ok:
            return waiting
        proof_result, proof = query_phone_status()
        if not proof_result.ok or proof is None:
            return Result(False, "The waiting command ran, but the phone proof could not be read.\n\n" + proof_result.message)
        if proof.verification == "WAITING_ARMED":
            return Result(True, "MIBU is armed and the countdown continues on the phone. The PC helper is no longer required.")
        if proof.timing_complete:
            return Result(True, "The timing window was reached while One Click Assist was running.")
        return Result(False, f"The phone did not remain armed. Current state: {proof.verification}.")


class TitleBar(QFrame):
    def __init__(self, window: "Window") -> None:
        super().__init__(window)
        self.window = window
        self.drag_position: QPoint | None = None
        self.setObjectName("titleBar")
        self.setFixedHeight(34)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 6, 0)
        row.setSpacing(7)

        icon = QLabel()
        icon.setFixedSize(20, 20)
        icon.setPixmap(QPixmap(live_asset("mibu_logo.png")).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(icon)
        title = QLabel("MIBU PC Helper")
        title.setObjectName("windowTitle")
        row.addWidget(title)
        team = QLabel("THETECHGUY TOOL")
        team.setObjectName("windowTeam")
        row.addWidget(team)
        row.addStretch(1)

        self.minimize = self._control("\u2212", "Minimize", window.showMinimized)
        self.maximize = self._control("\u25a1", "Maximize", self.toggle_maximize)
        self.close = self._control("\u00d7", "Close", window.close, close=True)
        row.addWidget(self.minimize)
        row.addWidget(self.maximize)
        row.addWidget(self.close)

    def _control(self, symbol: str, tooltip: str, callback, close: bool = False) -> QPushButton:
        button = QPushButton(symbol)
        button.setObjectName("titleClose" if close else "titleControl")
        button.setToolTip(tooltip)
        button.setFixedSize(32, 28)
        button.clicked.connect(callback)
        return button

    def toggle_maximize(self) -> None:
        if self.window.isMaximized():
            self.window.showNormal()
            self.maximize.setText("\u25a1")
            self.maximize.setToolTip("Maximize")
        else:
            self.window.showMaximized()
            self.maximize.setText("\u2750")
            self.maximize.setToolTip("Restore")

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton and not self.window.isMaximized():
            self.drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self.drag_position is not None and event.buttons() & Qt.LeftButton and not self.window.isMaximized():
            self.window.move(event.globalPosition().toPoint() - self.drag_position)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        self.drag_position = None


class LiveDialog(QDialog):
    def __init__(self, parent: "Window", title: str, subtitle: str, icon_name: str) -> None:
        super().__init__(parent)
        self.owner = parent
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(490, 430)
        self.setMinimumSize(450, 360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        shell = QFrame()
        shell.setObjectName("dialogShell")
        outer.addWidget(shell)
        root = QVBoxLayout(shell)
        root.setContentsMargins(20, 16, 20, 18)
        root.setSpacing(10)

        title_row = QHBoxLayout()
        icon = QLabel()
        icon.setFixedSize(48, 48)
        icon.setPixmap(QPixmap(live_asset(icon_name)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_row.addWidget(icon)
        copy = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        description = QLabel(subtitle)
        description.setObjectName("muted")
        description.setWordWrap(True)
        description.setMinimumWidth(0)
        copy.addWidget(heading)
        copy.addWidget(description)
        title_row.addLayout(copy, 1)
        close = QPushButton("\u00d7")
        close.setObjectName("dialogClose")
        close.setToolTip("Close")
        close.setFixedSize(30, 30)
        close.clicked.connect(self.reject)
        title_row.addWidget(close, 0, Qt.AlignTop)
        root.addLayout(title_row)

        self.steps = QVBoxLayout()
        self.steps.setSpacing(5)
        root.addLayout(self.steps)
        self.status = QLabel("Ready")
        self.status.setObjectName("dialogStatus")
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(48)
        root.addWidget(self.status)
        self.body = QVBoxLayout()
        self.body.setSpacing(7)
        root.addLayout(self.body)
        root.addStretch(1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        root.addLayout(self.actions)

    def add_step(self, number: int, text: str) -> None:
        row = QLabel(f"{number}    {text}")
        row.setObjectName("dialogStep")
        row.setFixedHeight(31)
        self.steps.addWidget(row)

    def add_action(self, label: str, callback, primary: bool = False) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("primaryButton" if primary else "secondaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedHeight(36)
        button.clicked.connect(callback)
        self.actions.addWidget(button)
        return button

    def set_status(self, message: str, ok: bool | None = None) -> None:
        self.status.setProperty("state", "ok" if ok else "error" if ok is False else "working")
        self.status.setText(message.strip() or "Done")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def run_action(self, button: QPushButton, message: str, function: Callable[[], object], completion) -> None:
        button.setEnabled(False)
        self.set_status(message)

        def done(value: object) -> None:
            button.setEnabled(True)
            completion(value)

        self.owner.run_background(function, done)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        parent = self.parentWidget()
        if parent:
            point = parent.frameGeometry().center() - self.rect().center()
            self.move(point)


class AssistantOverlay(QFrame):
    """Floating, model-free guide and command surface for the live workflow."""

    def __init__(self, owner: "Window") -> None:
        super().__init__(owner.shell)
        self.owner = owner
        self.expanded = False
        self.chat_open = False
        self.setObjectName("assistantOverlay")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.compact = QFrame()
        self.compact.setObjectName("assistantCompact")
        compact_layout = QHBoxLayout(self.compact)
        compact_layout.setContentsMargins(0, 0, 0, 0)
        compact_layout.setSpacing(5)
        self.help_hint = QPushButton("Need help?")
        self.help_hint.setObjectName("assistantHint")
        self.help_hint.setToolTip("Open MIBU Assistant")
        self.help_hint.setFixedSize(83, 34)
        self.help_hint.clicked.connect(self.expand)
        compact_layout.addWidget(self.help_hint)
        self.avatar = QPushButton()
        self.avatar.setObjectName("assistantAvatar")
        self.avatar.setToolTip("Open MIBU Assistant")
        self.avatar.setCursor(Qt.PointingHandCursor)
        self.avatar.setIcon(QIcon(live_asset("mibu_hood.png")))
        self.avatar.setIconSize(QSize(54, 54))
        self.avatar.clicked.connect(self.expand)
        compact_layout.addWidget(self.avatar)
        outer.addWidget(self.compact)

        self.panel = QFrame()
        self.panel.setObjectName("assistantExpanded")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(12, 9, 12, 11)
        panel_layout.setSpacing(6)

        heading = QHBoxLayout()
        title = QLabel("MIBU Assistant")
        title.setObjectName("assistantTitle")
        heading.addWidget(title)
        heading.addStretch(1)
        self.collapse_button = QPushButton("\u00d7")
        self.collapse_button.setObjectName("assistantClose")
        self.collapse_button.setToolTip("Close assistant")
        self.collapse_button.setFixedSize(25, 25)
        self.collapse_button.clicked.connect(self.collapse)
        heading.addWidget(self.collapse_button)
        panel_layout.addLayout(heading)

        stage = QWidget()
        stage.setFixedHeight(138)
        self.art = QLabel(stage)
        self.art.setGeometry(45, 0, 165, 134)
        self.art.setAlignment(Qt.AlignCenter)
        self.art.setPixmap(QPixmap(live_asset("mibu_hood.png")).scaled(165, 134, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.start_button = QPushButton("START")
        self.start_button.setObjectName("assistantChestButton")
        self.start_button.setToolTip("Start One-Click Assist")
        self.start_button.setGeometry(80, 94, 96, 30)
        self.start_button.clicked.connect(owner.run_one_click_assist)
        self.start_button.setParent(stage)
        self.start_button.raise_()
        chest_glow = QGraphicsDropShadowEffect(self.start_button)
        chest_glow.setBlurRadius(22)
        chest_glow.setOffset(0, 0)
        chest_glow.setColor(QColor(188, 65, 255, 210))
        self.start_button.setGraphicsEffect(chest_glow)
        panel_layout.addWidget(stage)

        self.bubble = QLabel("Connect the phone, then press START. I will stop only for approvals you must make.")
        self.bubble.setObjectName("assistantBubble")
        self.bubble.setWordWrap(True)
        self.bubble.setMinimumHeight(42)
        panel_layout.addWidget(self.bubble)

        self.progress = QProgressBar()
        self.progress.setObjectName("assistantProgress")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(7)
        panel_layout.addWidget(self.progress)

        commands = QHBoxLayout()
        self.chat_button = QPushButton("Chat")
        self.chat_button.setObjectName("assistantMiniButton")
        self.chat_button.setToolTip("Ask or tell the assistant what to do")
        self.chat_button.clicked.connect(self.toggle_chat)
        commands.addWidget(self.chat_button)
        self.guide_button = QPushButton("Manual")
        self.guide_button.setObjectName("assistantMiniButton")
        self.guide_button.setToolTip("Open the offline MIBU guide")
        self.guide_button.clicked.connect(owner.open_local_guide)
        commands.addWidget(self.guide_button)
        panel_layout.addLayout(commands)

        self.chat_panel = QFrame()
        self.chat_panel.setObjectName("assistantChat")
        chat_layout = QVBoxLayout(self.chat_panel)
        chat_layout.setContentsMargins(6, 6, 6, 6)
        chat_layout.setSpacing(5)
        self.chat_history = QPlainTextEdit()
        self.chat_history.setObjectName("assistantHistory")
        self.chat_history.setReadOnly(True)
        self.chat_history.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.chat_history.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_history.setPlainText("MIBU: Ask about ADB, install, login, tokens, waiting, status, or the manual.")
        chat_layout.addWidget(self.chat_history, 1)
        chat_entry = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("assistantInput")
        self.chat_input.setPlaceholderText("Ask MIBU or type an action...")
        self.chat_input.returnPressed.connect(self.send_message)
        chat_entry.addWidget(self.chat_input, 1)
        send = QPushButton("\u2192")
        send.setObjectName("assistantSend")
        send.setToolTip("Send")
        send.setFixedWidth(34)
        send.clicked.connect(self.send_message)
        chat_entry.addWidget(send)
        chat_layout.addLayout(chat_entry)
        panel_layout.addWidget(self.chat_panel, 1)

        outer.addWidget(self.panel)
        self.panel.hide()
        self.chat_panel.hide()
        self.setFixedSize(146, 58)
        self.raise_()

    def expand(self) -> None:
        self.expanded = True
        self.compact.hide()
        self.panel.show()
        self._resize_panel()

    def collapse(self) -> None:
        self.expanded = False
        self.chat_open = False
        self.chat_panel.hide()
        self.panel.hide()
        self.compact.show()
        self.setFixedSize(146, 58)
        self.owner.position_assistant()

    def toggle_chat(self) -> None:
        self.chat_open = not self.chat_open
        self.chat_panel.setVisible(self.chat_open)
        self.chat_button.setText("Hide Chat" if self.chat_open else "Chat")
        self._resize_panel()
        if self.chat_open:
            self.chat_input.setFocus()

    def _resize_panel(self) -> None:
        self.setFixedSize(280, 470 if self.chat_open else 326)
        self.owner.position_assistant()
        self.raise_()

    def send_message(self) -> None:
        message = self.chat_input.text().strip()
        if not message:
            return
        self.chat_input.clear()
        self.chat_history.appendPlainText(f"\nYou: {message}")
        response = self.owner.handle_assistant_message(message)
        self.chat_history.appendPlainText(f"MIBU: {response}")
        bar = self.chat_history.verticalScrollBar()
        bar.setValue(bar.maximum())

    def set_step(self, step: str, message: str) -> None:
        self.expand()
        self.bubble.setText(message)
        self.progress.setValue({"Device Check": 18, "Install APK": 45, "Login & Get Token": 70, "Phone Guide": 90}.get(step, 8))

    def finish_run(self, result: Result) -> None:
        self.expand()
        self.bubble.setText(result.message.splitlines()[0][:150])
        self.progress.setValue(100 if result.ok else max(8, self.progress.value()))
        self.start_button.setText("DONE" if result.ok else "CONTINUE")
        self.start_button.setEnabled(False)

    def unlock_start(self) -> None:
        self.start_button.setEnabled(True)

    def pulse(self, enabled: bool) -> None:
        self.setProperty("pulse", enabled)
        self.style().unpolish(self)
        self.style().polish(self)


class Window(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MIBU PC Helper - THETECHGUY TOOL")
        self.setWindowIcon(QIcon(live_asset("mibu_logo.png")))
        self._sounds: dict[bool, object] = {}
        self._init_sounds()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(WINDOW_SIZE)
        self.setMinimumSize(MINIMUM_SIZE)
        self.state = AppState()
        self.buttons: dict[str, QPushButton] = {}
        self.cards: dict[str, QPushButton] = {}
        self._threads: set[QThread] = set()
        self._workers: dict[QThread, FunctionWorker] = {}
        self._assistant_thread: QThread | None = None
        self._assistant_worker: AssistantWorker | None = None
        self._assistant_phase = 0
        self._build_ui()
        self._theme()
        self._update_time()
        self._update_status()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self.assistant_timer = QTimer(self)
        self.assistant_timer.timeout.connect(self._animate_assistant)
        self.assistant_timer.start(900)
        QTimer.singleShot(250, self._center)
        QTimer.singleShot(450, self.refresh_live_state)
        QTimer.singleShot(700, self._dependency_review)

    def _build_ui(self) -> None:
        transparent = QWidget()
        self.setCentralWidget(transparent)
        outer = QVBoxLayout(transparent)
        outer.setContentsMargins(7, 7, 7, 7)
        outer.setSpacing(0)
        self.shell = QFrame()
        self.shell.setObjectName("appShell")
        outer.addWidget(self.shell)
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.title_bar = TitleBar(self)
        shell_layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        shell_layout.addWidget(content, 1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(164)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 12, 12, 12)
        side.setSpacing(7)
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(114)
        logo.setPixmap(QPixmap(live_asset("mibu_logo.png")).scaled(112, 112, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        side.addWidget(logo)
        brand = QLabel("MIBU")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignCenter)
        side.addWidget(brand)
        byline = QLabel("BY THETECHGUY TOOL")
        byline.setObjectName("byline")
        byline.setAlignment(Qt.AlignCenter)
        side.addWidget(byline)
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        side.addWidget(divider)
        section = QLabel("SETUP PROGRESS")
        section.setObjectName("sectionTitle")
        side.addWidget(section)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("progressList")
        self.progress_label.setWordWrap(True)
        side.addWidget(self.progress_label)

        side.addStretch(1)
        self.system_label = QLabel("Checking systems...")
        self.system_label.setObjectName("systemState")
        self.system_label.setFixedHeight(28)
        side.addWidget(self.system_label)
        content_layout.addWidget(sidebar)

        main = QFrame()
        main.setObjectName("mainPanel")
        body = QVBoxLayout(main)
        body.setContentsMargins(12, 8, 12, 8)
        body.setSpacing(3)
        header = QHBoxLayout()
        copy = QVBoxLayout()
        copy.setSpacing(2)
        kicker = QLabel("PC HELPER SETUP WIZARD")
        kicker.setObjectName("kicker")
        kicker.setMinimumWidth(0)
        title = QLabel("Welcome to MIBU PC Helper")
        title.setObjectName("heroTitle")
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        description = QLabel("Prepare the phone, install MIBU, import the approved session, then hand off to Android.")
        description.setObjectName("muted")
        description.setWordWrap(True)
        copy.addWidget(kicker)
        copy.addWidget(title)
        copy.addWidget(description)
        header.addLayout(copy, 1)
        hero = QLabel()
        hero.setFixedSize(100, 58)
        hero.setAlignment(Qt.AlignCenter)
        hero.setPixmap(QPixmap(live_asset("mibu_hood.png")).scaled(100, 66, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(hero)
        body.addLayout(header)

        steps = (
            ("Device Check", "icon_device.png", "Check ADB, USB debugging and RSA"),
            ("Install APK", "icon_install.png", "Install, verify and open MIBU"),
            ("Login & Get Token", "icon_account.png", "Open browsers and push approved captures"),
            ("Phone Guide", "icon_guide.png", "Continue waiting from the phone"),
        )
        handlers = {
            "Device Check": self.show_device_check,
            "Install APK": self.show_install_apk,
            "Login & Get Token": self.show_login_token,
            "Phone Guide": self.show_phone_guide,
        }
        for index, (name, icon_name, subtitle) in enumerate(steps, start=1):
            card = QPushButton(f"{index}.  {name}\n{subtitle}")
            card.setObjectName("stepCard")
            card.setProperty("active", False)
            card.setIcon(QIcon(live_asset(icon_name)))
            card.setIconSize(QSize(36, 36))
            card.setCursor(Qt.PointingHandCursor)
            card.setFixedHeight(44)
            card.setMinimumWidth(0)
            card.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            card.clicked.connect(handlers[name])
            self.cards[name] = card
            body.addWidget(card)

        self.status = QLabel()
        self.status.setObjectName("statusStrip")
        self.status.setFixedHeight(32)
        self.status.setMinimumWidth(0)
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        body.addWidget(self.status)
        self.time_label = QLabel()
        self.time_label.setObjectName("timeStrip")
        self.time_label.setFixedHeight(22)
        self.time_label.setMinimumWidth(0)
        self.time_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        body.addWidget(self.time_label)

        command = QHBoxLayout()
        command.setSpacing(5)
        self.command_input = QLineEdit()
        self.command_input.setObjectName("commandInput")
        self.command_input.setPlaceholderText("ADB command, e.g. shell getprop ro.product.model")
        self.command_input.setFixedHeight(26)
        self.command_input.setMinimumWidth(0)
        self.command_input.returnPressed.connect(self.run_custom_adb_command)
        command.addWidget(self.command_input, 1)
        self.command_button = QPushButton("Run")
        self.command_button.setObjectName("secondaryButton")
        self.command_button.setFixedSize(54, 26)
        self.command_button.clicked.connect(self.run_custom_adb_command)
        command.addWidget(self.command_button)
        body.addLayout(command)
        self.output = QPlainTextEdit()
        self.output.setObjectName("floatingOutput")
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(250)
        self.output.setFixedHeight(42)
        self.output.setMinimumWidth(0)
        body.addWidget(self.output)

        actions = QGridLayout()
        actions.setHorizontalSpacing(5)
        actions.setContentsMargins(0, 0, 0, 0)
        for column, (name, icon_name, _) in enumerate(steps):
            button = QPushButton(name.replace(" & ", "\n& "))
            button.setObjectName("flowButton")
            button.setProperty("active", False)
            button.setIcon(QIcon(live_asset(icon_name)))
            button.setIconSize(QSize(22, 22))
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(40)
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            button.clicked.connect(handlers[name])
            self.buttons[name] = button
            actions.addWidget(button, 0, column)
        body.addLayout(actions)
        content_layout.addWidget(main, 1)
        self.size_grip = QSizeGrip(self.shell)
        self.size_grip.setFixedSize(14, 14)
        self.assistant = AssistantOverlay(self)
        self.assistant_bubble = self.assistant.bubble
        self.assistant_button = self.assistant.start_button
        self.position_assistant()

    def _theme(self) -> None:
        self.setStyleSheet("""
        QWidget { color:#f5f7fb; font-family:'Segoe UI',Arial; font-size:10px; }
        QFrame#appShell { background:#040711; border:1px solid #6b2f86; border-radius:12px; }
        QFrame#titleBar { background:#070912; border:0; border-bottom:1px solid #171c2c; border-top-left-radius:11px; border-top-right-radius:11px; }
        QLabel#windowTitle { color:#ffffff; font-size:11px; font-weight:650; }
        QLabel#windowTeam { color:#7c8ba8; font-size:9px; }
        QPushButton#titleControl, QPushButton#titleClose, QPushButton#dialogClose { background:transparent; border:0; color:#c7d0e4; font-size:15px; }
        QPushButton#titleControl:hover { background:#1a2233; }
        QPushButton#titleClose:hover, QPushButton#dialogClose:hover { background:#c42b3a; color:#ffffff; }
        QFrame#sidebar, QFrame#mainPanel { background:#070b16; border:1px solid #233653; border-radius:9px; }
        QLabel#brand { color:#ffffff; font-size:25px; font-weight:300; }
        QLabel#byline { color:#aab5cc; font-size:8px; letter-spacing:0px; }
        QFrame#divider { background:#1c273b; border:0; }
        QLabel#sectionTitle { color:#edf3ff; font-size:9px; font-weight:800; }
        QLabel#progressList { color:#9aa8c4; font-size:9px; line-height:1.3; }
        QFrame#assistantOverlay { background:transparent; border:0; }
        QFrame#assistantOverlay[pulse="true"] QPushButton#assistantAvatar { border:2px solid #248fff; }
        QPushButton#assistantAvatar { background:#050914; border:1px solid #8543bb; border-radius:28px; padding:1px; }
        QPushButton#assistantAvatar:hover { border:2px solid #ff7929; background:#090f20; }
        QPushButton#assistantHint { background:#0a1020; border:1px solid #9c49d5; border-radius:12px; color:#f4e9ff; font-size:8px; font-weight:800; padding:4px 7px; }
        QPushButton#assistantHint:hover { border:1px solid #ff7929; background:#15102a; }
        QFrame#assistantExpanded { background:#070c18; border:1px solid #4f70a7; border-radius:10px; }
        QLabel#assistantTitle { color:#be65ff; font-size:10px; font-weight:750; }
        QLabel#assistantBubble { color:#d3ddf1; font-size:8px; background:#090f1e; border:1px solid #263c60; border-radius:6px; padding:6px; }
        QPushButton#assistantClose { background:transparent; border:0; color:#c7d0e4; font-size:15px; }
        QPushButton#assistantClose:hover { background:#c42b3a; color:#fff; border-radius:5px; }
        QPushButton#assistantChestButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff7223, stop:.5 #be45ff, stop:1 #258fff); border:1px solid #fff; border-radius:8px; color:#fff; font-size:8px; font-weight:900; }
        QPushButton#assistantMiniButton, QPushButton#assistantSend { background:#0d1628; border:1px solid #48628c; border-radius:6px; color:#fff; font-size:8px; padding:4px; }
        QFrame#assistantChat { background:#060a14; border:1px solid #223859; border-radius:7px; }
        QPlainTextEdit#assistantHistory { background:#060a14; border:0; color:#cbd7ec; font-size:8px; padding:2px; }
        QLineEdit#assistantInput { background:#0a1120; border:1px solid #314d79; border-radius:6px; color:#fff; font-size:8px; padding:4px; }
        QProgressBar#assistantProgress { background:#11182a; border:0; border-radius:3px; }
        QProgressBar#assistantProgress::chunk { border-radius:3px; background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff7223, stop:.5 #c246ff, stop:1 #258fff); }
        QLabel#systemState { background:#081321; border:1px solid #213956; border-radius:7px; color:#42f792; padding:5px 8px; font-size:8px; }
        QLabel#kicker { color:#ff8a24; font-size:9px; font-weight:800; }
        QLabel#heroTitle { color:#ffffff; font-size:21px; font-weight:800; }
        QLabel#muted { color:#9eabc3; font-size:9px; }
        QPushButton#stepCard { text-align:left; background:#0a0f20; border:1px solid #2f4162; border-radius:8px; color:#f6f8ff; padding:3px 10px; font-size:10px; font-weight:650; }
        QPushButton#stepCard:hover { border:1px solid #258cff; background:#0d1528; }
        QPushButton#stepCard[active="true"] { border:2px solid #ff7a2b; background:#15102c; }
        QLabel#statusStrip, QLabel#timeStrip { background:#080e1b; border:1px solid #263957; border-radius:7px; color:#dce7ff; padding:4px 8px; font-size:8px; }
        QLabel#timeStrip { color:#b85dff; }
        QLineEdit#commandInput, QPlainTextEdit#floatingOutput { background:#060b15; border:1px solid #263957; border-radius:7px; color:#dce7ff; padding:4px 7px; }
        QLineEdit#commandInput { font-size:9px; }
        QPlainTextEdit#floatingOutput { font-family:Consolas; font-size:8px; }
        QPushButton#flowButton { background:#090f1d; border:1px solid #344a70; border-radius:7px; color:#edf3ff; font-size:8px; font-weight:700; padding:3px; }
        QPushButton#flowButton:hover { border:1px solid #258cff; }
        QPushButton#flowButton[active="true"] { border:2px solid #ff7a2b; background:#17102f; }
        QPushButton#primaryButton, QPushButton#secondaryButton, QPushButton#assistantButton { border-radius:7px; color:white; padding:5px 10px; font-size:9px; font-weight:750; }
        QPushButton#primaryButton, QPushButton#assistantButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff7a2b, stop:.48 #c546ff, stop:1 #218bff); border:1px solid #f1f5ff; }
        QPushButton#secondaryButton { background:#0d1628; border:1px solid #48628c; }
        QPushButton:disabled { background:#1a2130; border-color:#313d51; color:#7f8da7; }
        QFrame#dialogShell { background:#070b16; border:1px solid #4c7ed1; border-radius:11px; }
        QLabel#dialogTitle { color:#ffffff; font-size:19px; font-weight:800; }
        QLabel#dialogStep { color:#dce7ff; font-size:10px; padding:4px 8px; background:#080e1c; border:1px solid #243653; border-radius:7px; }
        QLabel#dialogStatus { background:#080e1b; border:1px solid #334a75; border-radius:8px; color:#ffb75f; padding:7px; font-size:9px; }
        QLabel#dialogStatus[state="ok"] { border-color:#2dcc79; color:#49f29a; }
        QLabel#dialogStatus[state="error"] { border-color:#e15b66; color:#ff8f98; }
        """)

    def _center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen and not self.isMaximized():
            area = screen.availableGeometry()
            self.move(area.center() - self.rect().center())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.size_grip.move(self.shell.width() - 15, self.shell.height() - 15)
        self.position_assistant()

    def position_assistant(self) -> None:
        if not hasattr(self, "assistant"):
            return
        if self.assistant.expanded:
            self.assistant.move(20, 43)
        else:
            self.assistant.move(17, max(290, self.shell.height() - 160))
        self.assistant.raise_()

    def run_background(self, function: Callable[[], object], completion: Callable[[object], None]) -> None:
        thread = QThread(self)
        worker = FunctionWorker(function)
        worker.moveToThread(thread)
        self._threads.add(thread)
        self._workers[thread] = worker

        def done(value: object) -> None:
            completion(value)
            thread.quit()

        worker.finished.connect(done)
        thread.started.connect(worker.run)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._background_done(thread))
        thread.start()

    def _background_done(self, thread: QThread) -> None:
        self._threads.discard(thread)
        self._workers.pop(thread, None)

    def _log(self, message: str) -> None:
        self.output.appendPlainText(message.strip())
        bar = self.output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _play(self, ok: bool) -> None:
        sound = self._sounds.get(ok)
        if sound is not None:
            sound.play()
        elif not ok:
            QApplication.beep()

    def _init_sounds(self) -> None:
        if QSoundEffect is None:
            return
        names = {
            True: "TTG_v4_clean_connected_success.wav",
            False: "TTG_v4_clean_speaker_turn_on.wav",
        }
        for ok, name in names.items():
            path = find_asset(name, f"dist/{name}", f"expected ui/{name}")
            if not path:
                continue
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
            effect.setVolume(0.8)
            self._sounds[ok] = effect

    def _dependency_review(self) -> None:
        def done(value: object) -> None:
            checks = value if isinstance(value, list) else []
            if checks:
                self._log(format_checks(checks))
                self.system_label.setText("Systems ready" if all(item.ok for item in checks) else "Dependency attention needed")

        self.run_background(run_all_checks, done)

    def _update_time(self) -> None:
        from datetime import datetime
        target = next_target()
        local = target.astimezone()
        remaining = max(0, int((target - datetime.now(BEIJING_ZONE)).total_seconds()))
        hours, rem = divmod(remaining, 3600)
        minutes, seconds = divmod(rem, 60)
        self.time_label.setText(f"BJ {target:%H:%M:%S}  |  LOCAL {local:%H:%M:%S}  |  {hours:02d}:{minutes:02d}:{seconds:02d} LEFT")

    def _update_status(self) -> None:
        self.status.setText(
            f"PHONE {'ONLINE' if self.state.device_ok else 'WAIT'}  |  "
            f"ADB {'READY' if self.state.device_ok else 'WAIT'}  |  "
            f"APK {'READY' if self.state.apk_ok else 'WAIT'}  |  "
            f"SESSION {'READY' if self.state.tokens_ok else 'WAIT'}"
        )
        lines = []
        values = (self.state.device_ok, self.state.apk_ok, self.state.tokens_ok, self.state.tokens_ok)
        for index, (name, ready) in enumerate(zip(self.buttons, values), start=1):
            marker = "\u2713" if ready else "\u25cb"
            lines.append(f"{marker}  {index}  {name}")
        self.progress_label.setText("\n".join(lines))

    def _set_active(self, name: str) -> None:
        for mapping in (self.buttons, self.cards):
            for key, button in mapping.items():
                active = key == name
                button.setProperty("active", active)
                button.style().unpolish(button)
                button.style().polish(button)
                button.setGraphicsEffect(None)
                if active:
                    glow = QGraphicsDropShadowEffect(button)
                    glow.setBlurRadius(20)
                    glow.setOffset(0, 0)
                    glow.setColor(QColor(255, 86, 54, 190))
                    button.setGraphicsEffect(glow)

    def _report(self, dialog: LiveDialog, value: object) -> None:
        result = value if isinstance(value, Result) else Result(False, str(value))
        self._log(result.message)
        dialog.set_status(result.message, result.ok)
        self._play(result.ok)

    def refresh_live_state(self) -> None:
        if any(thread.isRunning() for thread in self._threads):
            return

        def probe() -> tuple[Result, Result, Result, PhoneStatus | None]:
            device = check_device_ready()
            version = installed_package_version() if device.ok else Result(False, "Device not ready")
            status_result, status = query_phone_status() if version.ok else (Result(False, "MIBU not ready"), None)
            return device, version, status_result, status

        def done(value: object) -> None:
            if not isinstance(value, tuple):
                return
            device, version, status_result, phone = value
            self.state.device_ok = device.ok
            self.state.apk_ok = version.ok
            self.state.tokens_ok = bool(status_result.ok and phone and phone.captures_ready)
            self._update_status()
            if device.ok:
                self.system_label.setText("Phone connected")
            self._log(device.message)

        self.run_background(probe, done)

    def _assistant_apk_path(self) -> str:
        return find_asset("MIBU.apk", "app-debug.apk")

    def open_local_guide(self) -> None:
        path = find_asset("guide/index.html")
        if not path:
            self._log("The offline MIBU manual is missing from this build.")
            self.assistant_bubble.setText("The offline manual is missing. Rebuild the release.")
            return
        webbrowser.open(Path(path).resolve().as_uri())
        self._log("Opened the branded offline MIBU workflow guide.")

    def handle_assistant_message(self, message: str) -> str:
        clean = " ".join(message.lower().split())
        if clean.startswith("adb "):
            command = message.strip()[4:].strip()
            if not command:
                return "Add a command after adb, for example: adb shell getprop ro.product.model"
            self.command_input.setText(command)
            QTimer.singleShot(0, self.run_custom_adb_command)
            return "Running that ADB command in the app output area. No terminal window will open."
        if "status" in clean or "what is happening" in clean:
            return self.status.text().replace("    ", "; ")
        if "four token" in clean or "4 token" in clean or "lane" in clean:
            return "Two distinct captures feed four lanes: Firefox is reused for lanes 1 and 3; Chrome is reused for lanes 2 and 4."
        if "manual" in clean or "guide" in clean or clean == "help":
            QTimer.singleShot(0, self.open_local_guide)
            return "Opening the offline illustrated MIBU manual."
        if "start waiting" in clean or "phone guide" in clean or "timer" in clean:
            QTimer.singleShot(0, self.show_phone_guide)
            return "Opening the phone handoff. I will verify the service after Start Waiting."
        if "couldn't add" in clean or "couldnt add" in clean or "unlock status" in clean or "bind" in clean:
            self.run_background(launch_unlock_methods, lambda value: self._log(value.message if isinstance(value, Result) else str(value)))
            return "Opening Mi Unlock & Binding on the phone. Use Xiaomi's exact result to choose official or recovery steps."
        if "compatibility" in clean or "hypersploit" in clean or "hyperos build" in clean:
            self.run_background(check_binding_recovery_compatibility, lambda value: self._log(value.message if isinstance(value, Result) else str(value)))
            return "Checking the phone's model, HyperOS build, security patch and Settings version without changing the phone."
        if "token" in clean or "login" in clean or "browser" in clean or "session" in clean:
            QTimer.singleShot(0, self.show_login_token)
            return "Opening the explicit browser-session handoff. Firefox feeds lanes 1/3 and Chrome feeds lanes 2/4."
        if "install" in clean or "apk" in clean:
            QTimer.singleShot(0, self.show_install_apk)
            return "Opening the live APK installer and verifier."
        if "device" in clean or "adb" in clean or "connect" in clean or "usb" in clean:
            QTimer.singleShot(0, self.show_device_check)
            return "Opening Device Check to verify the cable, ADB state, and RSA authorization."
        if "one click" in clean or "automatic" in clean or clean in {"start", "go", "run"}:
            QTimer.singleShot(0, self.run_one_click_assist)
            return "Starting One-Click Assist. I will pause only for phone or browser approval you must provide."
        return "I can check the device, install MIBU, open the session handoff, start the phone guide, report status, open the manual, or run an explicit adb command."

    def run_one_click_assist(self) -> None:
        if self._assistant_thread is not None:
            self._log("One Click Assist is already running.")
            return
        self._set_active("Device Check")
        self.assistant.expand()
        self.assistant.start_button.setText("WORKING")
        self.assistant.start_button.setEnabled(False)
        self.assistant.bubble.setText("Starting device check...")
        self.assistant.progress.setValue(5)
        self._log("One Click Assist started.")
        thread = QThread(self)
        worker = AssistantWorker(self._assistant_apk_path())
        worker.moveToThread(thread)
        worker.step.connect(self._assistant_step)
        worker.finished.connect(self._assistant_finished)
        worker.finished.connect(thread.quit)
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._assistant_thread_done)
        self._assistant_thread = thread
        self._assistant_worker = worker
        thread.start()

    def _assistant_step(self, step: str, message: str) -> None:
        self._set_active(step)
        self.assistant.set_step(step, message)
        self._log(f"Assistant: {message}")

    def _assistant_finished(self, value: object) -> None:
        result = value if isinstance(value, Result) else Result(False, str(value))
        self._log(result.message)
        self.assistant.finish_run(result)
        self._play(result.ok)
        self.refresh_live_state()

    def _assistant_thread_done(self) -> None:
        self._assistant_thread = None
        self._assistant_worker = None
        self.assistant.unlock_start()

    def _animate_assistant(self) -> None:
        self._assistant_phase += 1
        self.assistant.pulse(self._assistant_phase % 2 == 1)

    def run_custom_adb_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            self._log("Type an ADB command first.")
            return
        self.command_button.setEnabled(False)
        self._log(f"$ adb {command}")

        def done(value: object) -> None:
            self.command_button.setEnabled(True)
            result = value if isinstance(value, Result) else Result(False, str(value))
            self._log(result.message)
            self._play(result.ok)

        self.run_background(lambda: run_adb_user_command(command), done)

    def show_device_check(self) -> None:
        self._set_active("Device Check")
        dialog = LiveDialog(self, "Device Check Guide", "Get the Xiaomi phone online over ADB.", "icon_device.png")
        for number, text in (
            (1, "Connect the phone by USB"),
            (2, "Enable USB debugging"),
            (3, "Accept the Android security warning"),
            (4, "Accept RSA and choose Always allow"),
        ):
            dialog.add_step(number, text)

        def complete(value: object) -> None:
            result = value if isinstance(value, Result) else Result(False, str(value))
            self.state.device_ok = result.ok
            self._update_status()
            self._report(dialog, result)

        help_button = dialog.add_action("ADB Help", lambda: webbrowser.open("https://developer.android.com/tools/adb"))
        recheck = dialog.add_action("Recheck Device", lambda: None, True)
        recheck.clicked.disconnect()
        recheck.clicked.connect(lambda: dialog.run_action(recheck, "Checking the connected phone...", check_device_ready, complete))
        dialog.run_action(recheck, "Checking the connected phone...", check_device_ready, complete)
        dialog.exec()

    def show_install_apk(self) -> None:
        self._set_active("Install APK")
        dialog = LiveDialog(self, "Install MIBU.apk", "Install, verify, and open the bundled Android app.", "icon_install.png")
        for number, text in ((1, "Confirm ADB online"), (2, "Locate bundled MIBU.apk"), (3, "Install or update the APK"), (4, "Verify version and open MIBU")):
            dialog.add_step(number, text)
        selected = {"path": self._assistant_apk_path()}

        def browse() -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Select MIBU APK", "", "Android APK (*.apk)")
            if path:
                selected["path"] = path
                dialog.set_status(f"Selected: {path}")

        def perform() -> Result:
            path = selected["path"]
            if not path:
                return Result(False, "No APK was found. Rebuild the release or browse to MIBU.apk.")
            installed = install_package(path)
            if not installed.ok:
                return installed
            opened = launch_phone_app()
            return Result(opened.ok, installed.message + "\n" + opened.message)

        def complete(value: object) -> None:
            result = value if isinstance(value, Result) else Result(False, str(value))
            self.state.apk_ok = result.ok
            self._update_status()
            self._report(dialog, result)

        dialog.add_action("Browse APK", browse)
        install = dialog.add_action("Install APK", lambda: None, True)
        install.clicked.disconnect()
        install.clicked.connect(lambda: dialog.run_action(install, "Installing and verifying MIBU...", perform, complete))
        dialog.exec()

    def show_login_token(self) -> None:
        self._set_active("Login & Get Token")
        dialog = LiveDialog(self, "Login & Get Token", "Two approved captures are reused across the four timing lanes.", "icon_account.png")
        for number, text in ((1, "Open Firefox and Chrome"), (2, "Complete Xiaomi login yourself"), (3, "Firefox feeds lanes 1 and 3"), (4, "Chrome feeds lanes 2 and 4")):
            dialog.add_step(number, text)
        service = QLineEdit()
        service.setPlaceholderText("Firefox new_bbs_serviceToken (lanes 1 + 3)")
        service.setEchoMode(QLineEdit.Password)
        pop = QLineEdit()
        pop.setPlaceholderText("Chrome popRunToken (lanes 2 + 4)")
        pop.setEchoMode(QLineEdit.Password)
        dialog.body.addWidget(service)
        dialog.body.addWidget(pop)

        def open_browser(key: str) -> None:
            message = open_or_install_browser(key, LOGIN_URL)
            dialog.set_status(message)
            self._log(message)

        def push() -> Result:
            return push_two_tokens_to_phone(service.text(), pop.text())

        def complete(value: object) -> None:
            result = value if isinstance(value, Result) else Result(False, str(value))
            self.state.tokens_ok = result.ok
            self._update_status()
            self._report(dialog, result)
            if result.ok:
                service.clear()
                pop.clear()

        icon_provider = QFileIconProvider()
        for key, label in (("firefox", "Open Firefox"), ("chrome", "Open Chrome")):
            button = dialog.add_action(label, lambda checked=False, selected=key: open_browser(selected))
            path = browser_path(key)
            if path:
                button.setIcon(icon_provider.icon(QFileInfo(path)))
                button.setIconSize(QSize(20, 20))
        push_button = dialog.add_action("Push Captures", lambda: None, True)
        push_button.clicked.disconnect()
        push_button.clicked.connect(lambda: dialog.run_action(push_button, "Pushing approved captures to the phone...", push, complete))
        dialog.exec()

    def show_phone_guide(self) -> None:
        self._set_active("Phone Guide")
        dialog = LiveDialog(self, "Continue on Phone", "The Android app owns the countdown after handoff.", "icon_guide.png")
        for number, text in ((1, "Open MIBU on the phone"), (2, "Confirm the session is ready"), (3, "Keep mobile data available"), (4, "Start waiting, then verify binding")):
            dialog.add_step(number, text)

        def action(button: QPushButton, message: str, function: Callable[[], object]) -> None:
            dialog.run_action(button, message, function, lambda value: self._report(dialog, value))

        open_button = dialog.add_action("Open MIBU", lambda: None)
        open_button.clicked.disconnect()
        open_button.clicked.connect(lambda: action(open_button, "Opening MIBU on the phone...", launch_phone_app))
        wait_button = dialog.add_action("Start Waiting", lambda: None, True)
        wait_button.clicked.disconnect()
        wait_button.clicked.connect(lambda: action(wait_button, "Starting and proving the phone service...", start_phone_waiting))
        bind_button = dialog.add_action("Mi Unlock Status", lambda: None)
        bind_button.clicked.disconnect()
        bind_button.clicked.connect(lambda: action(bind_button, "Opening Xiaomi Mi Unlock Status...", launch_mi_unlock_status))
        build_button = dialog.add_action("Check Build", lambda: None)
        build_button.setToolTip("Read-only binding-recovery compatibility report")
        build_button.clicked.disconnect()
        build_button.clicked.connect(lambda: action(build_button, "Reading the HyperOS and Settings build...", check_binding_recovery_compatibility))
        dialog.exec()


def main() -> int:
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("THETECHGUY.MIBU.PCHelper")
    app = QApplication(sys.argv)
    app.setApplicationName("MIBU PC Helper")
    app.setOrganizationName("THETECHGUY TOOL")
    app.setWindowIcon(QIcon(live_asset("mibu_logo.png")))
    app.setFont(QFont("Segoe UI", 9))
    window = Window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
