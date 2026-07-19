#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QObject, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
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
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import mibu_pc_helper_v2 as base_ui
from mibu_actions import (
    Result,
    check_device_ready,
    check_fastboot_ready,
    fastboot_oem_info,
    install_package,
    launch_phone_app,
    launch_token_import,
    push_session_to_phone,
    push_two_tokens_to_phone,
    run_adb_user_command,
    reboot_to_fastboot,
    start_phone_waiting,
)
from mibu_pc_helper_v2 import Window as V2Window
from mibu_pc_helper_v2 import find_asset
from mibu_pc_helper_v2 import WorkflowDialog as V2WorkflowDialog
from mibu_pc_helper_v2 import LOGIN_URL
from mibu_pc_helper_v2 import open_or_install_browser
from mibu_pc_helper_v2 import required_asset
from mibu_status import query_phone_status
from ui_geometry import POPUP_CLOSE_RECT, SCREENS


class AssistantWorker(QObject):
    step = Signal(str)
    finished = Signal(Result)

    def __init__(self, apk_path: str) -> None:
        super().__init__()
        self.apk_path = apk_path

    def run(self) -> None:
        try:
            result = self._run_flow()
        except Exception as exc:  # pragma: no cover - final safety for GUI worker
            result = Result(False, f"Assistant failed unexpectedly: {exc}")
        self.finished.emit(result)

    def _run_flow(self) -> Result:
        self.step.emit("Checking the phone over ADB...")
        device = check_device_ready()
        if not device.ok:
            return Result(False, "Assistant needs you: connect the phone, enable USB debugging, accept the RSA prompt, then run One Click Assist again.\n\n" + device.message)

        self.step.emit("Installing and verifying the bundled MIBU APK...")
        if not self.apk_path or not Path(self.apk_path).is_file():
            return Result(False, "Bundled MIBU.apk was not found. Rebuild the release or browse/install manually.")
        installed = install_package(self.apk_path)
        if not installed.ok:
            return Result(False, "Assistant needs you: Android blocked silent install. Approve the phone installer/security prompt, then run One Click Assist again.\n\n" + installed.message)

        self.step.emit("Opening MIBU on the phone...")
        opened = launch_phone_app()
        if not opened.ok:
            return opened

        self.step.emit("Reading phone proof state...")
        status_result, status = query_phone_status()
        if not status_result.ok or status is None:
            return Result(False, "MIBU opened, but the PC could not read the phone proof state yet.\n\n" + status_result.message)

        if status.timing_complete:
            return Result(True, "The phone says the timing stage is already complete. Continue with PC verification / official Mi Unlock handoff.\n\n" + status.raw)
        if status.authoritative_result:
            return Result(True, f"The phone already has an official result recorded as {status.verification}. No new waiting cycle was started.\n\n{status.raw}")
        if not status.captures_ready:
            token_screen = launch_token_import()
            opened = "Phone token-import screen opened." if token_screen.ok else "Could not open the phone token-import screen: " + token_screen.message
            self.step.emit("Opening browser login and waiting for explicit token import...")
            webbrowser.open(LOGIN_URL)
            deadline = time.monotonic() + 300
            latest_raw = status.raw
            while time.monotonic() < deadline:
                poll_result, poll_status = query_phone_status()
                if poll_result.ok and poll_status is not None:
                    latest_raw = poll_status.raw
                    if poll_status.captures_ready:
                        status = poll_status
                        break
                time.sleep(2)
            if not status.captures_ready:
                return Result(False, "Assistant needs you: import fresh Firefox service + Chrome pop token captures. I opened the phone import step and Xiaomi login. Run One Click Assist again after the import if the five-minute wait expires.\n\n" + opened + "\n\n" + latest_raw)

        self.step.emit("Starting the phone waiting service...")
        waiting = start_phone_waiting()
        if not waiting.ok:
            return waiting

        self.step.emit("Verifying the waiting proof...")
        proof_result, proof = query_phone_status()
        if not proof_result.ok or proof is None:
            return Result(False, "Waiting command was sent, but proof could not be read.\n\n" + proof_result.message)
        if proof.timing_complete:
            return Result(True, "Timing completed while the assistant was starting the service. Continue with verification.\n\n" + proof.raw)
        if proof.verification == "WAITING_ARMED":
            return Result(True, "MIBU is armed. Keep the phone powered, online, and do not close the phone app. Wait for the timing window.\n\n" + proof.raw)
        return Result(False, "The service start returned, but the phone did not remain in WAITING_ARMED state.\n\n" + proof.raw)


class WorkflowDialog(V2WorkflowDialog):
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        x, y, width, height = self.screen.normalized_rect(POPUP_CLOSE_RECT)
        self.close_button.setGeometry(
            int(self.width() * x),
            int(self.height() * y),
            int(self.width() * width),
            int(self.height() * height),
        )


class LiveDialog(QDialog):
    def __init__(self, parent: "Window", title: str, subtitle: str, icon_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(parent.windowIcon())
        self.setModal(True)
        self.resize(520, 500)
        self.setMinimumSize(460, 360)
        self.status = QLabel("Status appears here while this step runs.")
        self.status.setObjectName("dialogStatusBox")
        self.status.setWordWrap(True)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 20)
        root.setSpacing(14)

        title_row = QHBoxLayout()
        mark = QLabel(icon_text)
        mark.setObjectName("dialogMark")
        mark.setAlignment(Qt.AlignCenter)
        mark.setFixedSize(62, 62)
        title_box = QVBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        sub = QLabel(subtitle)
        sub.setObjectName("muted")
        sub.setWordWrap(True)
        title_box.addWidget(heading)
        title_box.addWidget(sub)
        close = QPushButton("x")
        close.setObjectName("closeButton")
        close.setFixedSize(32, 32)
        close.clicked.connect(self.reject)
        title_row.addWidget(mark)
        title_row.addLayout(title_box, 1)
        title_row.addWidget(close)
        root.addLayout(title_row)

        self.steps = QVBoxLayout()
        self.steps.setSpacing(8)
        root.addLayout(self.steps)
        root.addWidget(self.status)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        root.addLayout(self.body)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(12)
        root.addLayout(self.actions)

    def add_step(self, number: int, text: str) -> None:
        row = QLabel(f"{number}.  {text}")
        row.setObjectName("dialogStep")
        self.steps.addWidget(row)

    def add_action(self, label: str, callback, primary: bool = False) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("primaryButton" if primary else "secondaryButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        self.actions.addWidget(button)
        return button

    def set_status(self, message: str) -> None:
        self.status.setText(message.strip() or "Done")


class Window(V2Window):
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(14, 14, 14, 14)
        shell.setSpacing(14)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(248)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 18, 18, 18)
        side.setSpacing(14)
        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(210, 210)
        logo.setPixmap(QPixmap(required_asset("logo 1_transparent.png")).scaled(208, 208, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        side.addWidget(logo)
        brand = QLabel("MIBU")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignCenter)
        side.addWidget(brand)
        byline = QLabel("by THETECHGUY TOOL")
        byline.setObjectName("muted")
        byline.setAlignment(Qt.AlignCenter)
        side.addWidget(byline)
        progress_title = QLabel("Setup Progress")
        progress_title.setObjectName("sectionTitle")
        side.addWidget(progress_title)
        self.progress_label = QLabel("1  Device Check\n2  Install APK\n3  Login & Get Token\n4  Phone Guide")
        self.progress_label.setObjectName("progressList")
        side.addWidget(self.progress_label)
        help_card = QLabel("Need Help?\nUse Device Check for USB/RSA prompts, then Install APK, Login & Get Token, and Phone Guide.")
        help_card.setObjectName("helpCard")
        help_card.setWordWrap(True)
        side.addWidget(help_card, 1)
        self.system_label = QLabel("All systems checking...")
        self.system_label.setObjectName("systemOk")
        side.addWidget(self.system_label)
        shell.addWidget(sidebar)

        main = QFrame()
        main.setObjectName("mainPanel")
        body = QVBoxLayout(main)
        body.setContentsMargins(22, 22, 22, 22)
        body.setSpacing(14)
        top = QHBoxLayout()
        copy = QVBoxLayout()
        kicker = QLabel("PC HELPER SETUP WIZARD")
        kicker.setObjectName("kicker")
        title = QLabel("Welcome to MIBU PC Helper")
        title.setObjectName("heroTitle")
        desc = QLabel("This tool prepares your device, installs MIBU, guides login, and hands off to your phone so the app can take over.")
        desc.setObjectName("muted")
        desc.setWordWrap(True)
        copy.addWidget(kicker)
        copy.addWidget(title)
        copy.addWidget(desc)
        top.addLayout(copy, 2)
        hero = QLabel()
        hero.setObjectName("heroArt")
        hero.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        hero_path = find_asset("mibu_pc_hood_hero.png", "mibu_hood_hero.png", "assint.png")
        if hero_path:
            hero.setPixmap(QPixmap(hero_path).scaled(360, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        top.addWidget(hero, 1)
        body.addLayout(top)

        self.step_cards: dict[str, QLabel] = {}
        for name, icon, text in (
            ("Device Check", "[1]", "Check ADB, guide USB debugging, and confirm RSA authorization."),
            ("Install APK", "[2]", "Push the bundled MIBU.apk to the phone and open it."),
            ("Login & Get Token", "[3]", "Open browser login, then explicitly paste/push approved captures."),
            ("Phone Guide", "[4]", "Continue the waiting stage inside the Android app."),
        ):
            card = QPushButton(f"{icon}  {name}\n{text}")
            card.setObjectName("stepButton")
            card.setCursor(Qt.PointingHandCursor)
            card.clicked.connect({
                "Device Check": self.show_device_check,
                "Install APK": self.show_install_apk,
                "Login & Get Token": self.show_login_token,
                "Phone Guide": self.show_phone_guide,
            }[name])
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card.setMinimumHeight(74)
            self.buttons[name] = card
            body.addWidget(card)

        self.status = QLabel()
        self.status.setObjectName("statusStrip")
        self.status.setWordWrap(True)
        body.addWidget(self.status)
        self.time_label = QLabel()
        self.time_label.setObjectName("statusStrip")
        body.addWidget(self.time_label)
        command_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setObjectName("commandInput")
        self.command_input.setPlaceholderText("ADB command, e.g. shell getprop ro.product.model")
        self.command_input.returnPressed.connect(self.run_custom_adb_command)
        self.command_button = QPushButton("Run")
        self.command_button.setObjectName("secondaryButton")
        self.command_button.clicked.connect(self.run_custom_adb_command)
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.command_button)
        body.addLayout(command_row)
        self.output = QPlainTextEdit()
        self.output.setObjectName("floatingOutput")
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(300)
        self.output.setMinimumHeight(94)
        body.addWidget(self.output)
        shell.addWidget(main, 1)

    def __init__(self) -> None:
        # Inherited Device/Install/Login methods resolve WorkflowDialog from the
        # base module, so replace that one class with the reviewed v3 geometry.
        base_ui.WorkflowDialog = WorkflowDialog
        super().__init__()
        self.setWindowTitle("MIBU PC Helper - THETECHGUY TOOL")
        self.resize(1120, 720)
        self.setMinimumSize(920, 620)
        self.setWindowIcon(QIcon(required_asset("logo 1_transparent.png")))
        self._assistant_phase = 0
        self._assistant_thread: QThread | None = None
        self._assistant_worker: AssistantWorker | None = None
        self._build_assistant_overlay()
        self.assistant_timer = QTimer(self)
        self.assistant_timer.timeout.connect(self._animate_assistant)
        self.assistant_timer.start(1200)

    def _build_assistant_overlay(self) -> None:
        root = self.centralWidget()
        self.assistant_art = QLabel(root)
        self.assistant_art.setScaledContents(True)
        art = find_asset("assint.png")
        if art:
            self.assistant_art.setPixmap(QPixmap(art))
        self.assistant_art.setToolTip("MIBU Assistant")

        self.assistant_bubble = QLabel(
            "MIBU Assistant\nOne click handles what the PC can do. I will ask only for phone security prompts, USB debugging, or token import.",
            root,
        )
        self.assistant_bubble.setObjectName("assistantBubble")
        self.assistant_bubble.setWordWrap(True)

        self.assistant_button = QPushButton("One Click Assist", root)
        self.assistant_button.setObjectName("assistantButton")
        self.assistant_button.clicked.connect(self.run_one_click_assist)
        self.assistant_art.show()
        self.assistant_bubble.show()
        self.assistant_button.show()
        self._theme()
        self._position_assistant()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._position_assistant()

    def _position_assistant(self) -> None:
        root = self.centralWidget()
        if not root or not hasattr(self, "assistant_art"):
            return
        if not self.assistant_button.isVisible():
            return
        width = root.width()
        height = root.height()
        art_size = max(96, min(150, int(width * 0.12)))
        bob = (self._assistant_phase % 3) * 5
        x = max(10, int(width * 0.80))
        y = max(10, int(height * 0.08) + bob)
        self.assistant_art.setGeometry(x, y, art_size, art_size)
        self.assistant_bubble.setGeometry(max(10, x - int(width * 0.31)), y + 6, int(width * 0.30), max(82, int(height * 0.12)))
        self.assistant_button.setGeometry(x - int(width * 0.18), y + art_size + 8, int(width * 0.29), 42)
        self.assistant_art.raise_()
        self.assistant_bubble.raise_()
        self.assistant_button.raise_()

    def _animate_assistant(self) -> None:
        self._assistant_phase += 1
        self._position_assistant()

    def _theme(self) -> None:
        self.setStyleSheet("""
        QWidget { background:#040711; color:#f5f7fb; font-family:'Segoe UI',Arial; }
        QFrame#sidebar, QFrame#mainPanel { background:rgba(7,12,26,245); border:1px solid #233653; border-radius:18px; }
        QLabel#brand { color:#ffffff; font-size:38px; font-weight:300; letter-spacing:0; }
        QLabel#kicker { color:#ff8a24; font-size:13px; font-weight:800; }
        QLabel#heroTitle { color:#ffffff; font-size:30px; font-weight:800; }
        QLabel#muted { color:#b7c0d6; font-size:13px; }
        QLabel#sectionTitle { color:#eef4ff; font-size:12px; font-weight:800; text-transform:uppercase; }
        QLabel#progressList, QLabel#helpCard, QLabel#systemOk, QLabel#statusStrip, QLabel#dialogStatusBox, QPlainTextEdit#floatingOutput, QLineEdit#commandInput {
            background:rgba(9,16,32,235); border:1px solid #263957; border-radius:12px; color:#dce7ff; padding:10px;
        }
        QLabel#systemOk { color:#39ff87; }
        QPushButton#stepButton {
            text-align:left; background:rgba(10,15,32,235); border:1px solid #2f4162; border-radius:14px;
            color:#f6f8ff; padding:12px 18px; font-size:15px; font-weight:650;
        }
        QPushButton#stepButton:hover, QPushButton#stepButtonActive {
            border:2px solid #ff7a2b; background:rgba(22,18,48,245);
        }
        QPlainTextEdit#floatingOutput { font-family:Consolas; font-size:11px; }
        QLineEdit#commandInput { font-size:12px; }
        QPushButton#primaryButton, QPushButton#secondaryButton, QPushButton#assistantButton {
            border-radius:13px; color:white; padding:10px 16px; min-height:36px; font-weight:750;
        }
        QPushButton#primaryButton, QPushButton#assistantButton {
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff7a2b, stop:.48 #c546ff, stop:1 #218bff);
            border:1px solid #ffffff;
        }
        QPushButton#secondaryButton { background:rgba(13,22,40,245); border:1px solid #48628c; }
        QPushButton#closeButton { background:transparent; border:0; color:#dce7ff; font-size:18px; }
        QLabel#dialogTitle { color:#ffffff; font-size:24px; font-weight:800; }
        QLabel#dialogMark { border:2px solid #218bff; border-radius:31px; color:#53a8ff; font-size:24px; font-weight:800; background:rgba(8,18,38,235); }
        QLabel#dialogStep { color:#dce7ff; font-size:14px; padding:7px 10px; background:rgba(8,14,28,190); border:1px solid #243653; border-radius:10px; }
        QDialog { background:#070b16; }
        #assistantBubble { background:rgba(6,11,21,225); border:1px solid #53a8ff; border-radius:12px; color:#d9e6fb; padding:8px; font-size:11px; }
        #assistantButton:disabled { background:#1b2437; border:1px solid #33425c; color:#8fa3c4; }
        """)

    def _set_active(self, name: str) -> None:
        for key, button in self.buttons.items():
            button.setObjectName("stepButtonActive" if key == name else "stepButton")
            button.style().unpolish(button)
            button.style().polish(button)

    def _assistant_apk_path(self) -> str:
        return find_asset("MIBU.apk", "app-debug.apk")

    def run_one_click_assist(self) -> None:
        if self._assistant_thread is not None:
            self._log("Assistant is already running.")
            return
        self._set_active("Device Check")
        self.assistant_button.setEnabled(False)
        self.assistant_bubble.setText("MIBU Assistant\nStarting one-click setup...")
        self._log("MIBU Assistant: one-click setup started.")

        thread = QThread(self)
        worker = AssistantWorker(self._assistant_apk_path())
        worker.moveToThread(thread)
        worker.step.connect(self._assistant_step)
        worker.finished.connect(self._assistant_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._assistant_thread_done)
        thread.started.connect(worker.run)
        self._assistant_thread = thread
        self._assistant_worker = worker
        thread.start()

    def _assistant_step(self, message: str) -> None:
        self.assistant_bubble.setText("MIBU Assistant\n" + message)
        self._log("Assistant: " + message)

    def _assistant_finished(self, result: Result) -> None:
        self._log(result.message)
        self.assistant_bubble.setText(("MIBU Assistant\n" + result.message).splitlines()[0][:180])
        self._play(result.ok)
        if result.ok:
            if "installed" in result.message.lower() or "armed" in result.message.lower():
                self.state.apk_ok = True
                self.state.tokens_ok = "armed" in result.message.lower() or "timing" in result.message.lower()
                self._update_status()
            return
        if "token" in result.message.lower() or "capture" in result.message.lower():
            webbrowser.open(LOGIN_URL)

    def _assistant_thread_done(self) -> None:
        self._assistant_thread = None
        self._assistant_worker = None
        self.assistant_button.setEnabled(True)

    def _report_dialog(self, dialog: LiveDialog, result: Result) -> None:
        self._log(result.message)
        dialog.set_status(result.message)
        self._play(result.ok)

    def show_device_check(self) -> None:
        self._set_active("Device Check")
        dialog = LiveDialog(self, "Device Check Guide", "Get ADB online before continuing.", "1")
        for number, text in (
            (1, "Connect phone by USB"),
            (2, "Enable USB debugging"),
            (3, "Accept Danger warning and tap OK"),
            (4, "Accept RSA prompt and Always allow"),
        ):
            dialog.add_step(number, text)

        def recheck() -> None:
            result = check_device_ready()
            self.state.device_ok = result.ok
            self._update_status()
            self._report_dialog(dialog, result)

        dialog.add_action("Open ADB Help", lambda: webbrowser.open("https://developer.android.com/tools/adb"))
        dialog.add_action("Recheck Device", recheck, True)
        recheck()
        dialog.exec()

    def show_install_apk(self) -> None:
        self._set_active("Install APK")
        dialog = LiveDialog(self, "Install MIBU.apk", "Push the bundled Android app to the connected phone.", "2")
        for number, text in (
            (1, "ADB found and device online"),
            (2, "Bundled APK located"),
            (3, "Installing with adb install -r"),
            (4, "Opening MIBU on phone"),
        ):
            dialog.add_step(number, text)
        selected = {"path": find_asset("MIBU.apk", "app-debug.apk")}

        def browse() -> None:
            path, _ = QFileDialog.getOpenFileName(self, "Select MIBU APK", "", "Android APK (*.apk)")
            if path:
                selected["path"] = path
                dialog.set_status(f"Selected APK:\n{path}")

        def install() -> None:
            path = selected["path"]
            if not path:
                self._report_dialog(dialog, Result(False, "No APK found. Build Android or browse to the APK."))
                return
            result = install_package(path)
            self.state.apk_ok = result.ok
            self._update_status()
            self._report_dialog(dialog, result)
            if result.ok:
                opened = launch_phone_app()
                self._log("Open MIBU:\n" + opened.message)
                dialog.set_status(result.message + "\n\nOpen MIBU:\n" + opened.message)

        dialog.add_action("Browse APK", browse)
        dialog.add_action("Install APK", install, True)
        dialog.exec()

    def show_login_token(self) -> None:
        self._set_active("Login & Get Token")
        dialog = LiveDialog(self, "Login & Get Token", "Use your normal browser, then paste/import the token explicitly.", "3")
        for number, text in (
            (1, "Open Chrome, Firefox, or Brave"),
            (2, "Log into Xiaomi yourself"),
            (3, "Paste token/session manually"),
            (4, "Push token to MIBU on phone"),
        ):
            dialog.add_step(number, text)

        def open_browser() -> None:
            chrome = open_or_install_browser("chrome")
            firefox = open_or_install_browser("firefox")
            brave = open_or_install_browser("brave")
            dialog.set_status(f"{chrome}\n{firefox}\n{brave}\n\nMIBU does not ask for your password.")
            self._log(dialog.status.text())

        def paste_one() -> None:
            token, accepted = QInputDialog.getText(self, "Token Import", "Paste token/session:", QLineEdit.Password)
            if not accepted:
                return
            result = push_session_to_phone(token)
            self.state.tokens_ok = result.ok
            self._update_status()
            self._report_dialog(dialog, result)

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
            self._report_dialog(dialog, result)

        dialog.add_action("Open Browser", open_browser)
        dialog.add_action("Paste One", paste_one)
        dialog.add_action("Paste Two", paste_two, True)
        dialog.exec()

    def show_phone_guide(self) -> None:
        self._set_active("Phone Guide")
        dialog = LiveDialog(self, "Continue on Phone", "After login and token handoff, finish from the Android app.", "4")
        for number, text in (
            (1, "Open MIBU on the phone"),
            (2, "Confirm session imported"),
            (3, "Check account status"),
            (4, "Keep mobile data on and tap Start Waiting"),
        ):
            dialog.add_step(number, text)

        def report(result: Result) -> None:
            self._report_dialog(dialog, result)

        def open_app() -> None:
            report(launch_phone_app())

        def start_wait() -> None:
            status_result, status = query_phone_status()
            if not status_result.ok or status is None:
                report(status_result)
                return
            if status.timing_complete:
                report(Result(True, f"Phone timing stage is already complete. No new waiting cycle was started.\n{status.raw}"))
                return
            if status.authoritative_result:
                report(Result(True, f"An official result is already recorded as {status.verification}. No new waiting cycle was started. Reset the workflow on the phone only when a fresh authorised attempt is genuinely required.\n{status.raw}"))
                return
            if not status.captures_ready:
                report(Result(False, "Phone proof says both fresh captures are not ready. Import Firefox + Chrome tokens first."))
                return

            result = start_phone_waiting()
            report(result)
            if not result.ok:
                return

            proof_result, proof = query_phone_status()
            if not proof_result.ok or proof is None:
                report(proof_result)
                return
            if proof.timing_complete:
                report(Result(True, f"Timing completed while the waiting service was starting.\n{proof.raw}"))
                return
            if proof.authoritative_result:
                report(Result(True, f"An official result became authoritative while waiting was starting: {proof.verification}.\n{proof.raw}"))
                return
            armed = proof.verification == "WAITING_ARMED"
            report(Result(armed, proof.raw if armed else f"Foreground service proof succeeded, but phone state did not remain WAITING_ARMED. {proof.raw}"))

        def verify_fastboot() -> None:
            status_result, status = query_phone_status()
            if not status_result.ok or status is None:
                report(status_result)
                return
            if status.unlocked:
                report(Result(True, f"The phone already records the authoritative result UNLOCKED. No new fastboot handoff is required.\n{status.raw}"))
                return
            if status.authoritative_result:
                report(Result(False, f"Fastboot handoff is blocked because the recorded official result is {status.verification}. Follow that result or reset the workflow only for a legitimate fresh attempt.\n{status.raw}"))
                return
            if not status.timing_complete:
                report(Result(False, f"Phone timing proof is not complete yet. Current state: {status.verification}"))
                return
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
            dialog.set_status("Fastboot detected and phone timing state was proven complete. Continue with the official Mi Unlock Tool.")

        dialog.add_action("Open MIBU", open_app)
        dialog.add_action("Start Waiting", start_wait, True)
        dialog.add_action("Verify Fastboot", verify_fastboot)
        dialog.add_action("Done", dialog.accept)
        dialog.exec()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MIBU PC Helper")
    app.setWindowIcon(QIcon(required_asset("logo 1_transparent.png")))
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
