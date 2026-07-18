#!/usr/bin/env python3
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

import mibu_pc_helper_v2 as base_ui
from mibu_actions import (
    Result,
    check_device_ready,
    check_fastboot_ready,
    fastboot_oem_info,
    install_package,
    launch_phone_app,
    reboot_to_fastboot,
    start_phone_waiting,
)
from mibu_pc_helper_v2 import Window as V2Window
from mibu_pc_helper_v2 import find_asset
from mibu_pc_helper_v2 import WorkflowDialog as V2WorkflowDialog
from mibu_pc_helper_v2 import LOGIN_URL
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
            return Result(False, "Assistant needs you: log in in the browser and import fresh Firefox service + Chrome pop token captures. I opened MIBU; use Login & Get Token, then run One Click Assist again.\n\n" + status.raw)

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


class Window(V2Window):
    def __init__(self) -> None:
        # Inherited Device/Install/Login methods resolve WorkflowDialog from the
        # base module, so replace that one class with the reviewed v3 geometry.
        base_ui.WorkflowDialog = WorkflowDialog
        super().__init__()
        self.setWindowIcon(QIcon(find_asset("logo 1_transparent.png") or required_asset("mibu_app_icon.png")))
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
        self._theme()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._position_assistant()

    def _position_assistant(self) -> None:
        root = self.centralWidget()
        if not root or not hasattr(self, "assistant_art"):
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
        super()._theme()
        self.setStyleSheet(self.styleSheet() + """
        #assistantBubble { background:rgba(6,11,21,225); border:1px solid #53a8ff; border-radius:12px; color:#d9e6fb; padding:8px; font-size:11px; }
        #assistantButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #ff7a2b, stop:.48 #c546ff, stop:1 #218bff); border:1px solid #ffffff; border-radius:13px; color:white; font-weight:700; padding:8px 12px; }
        #assistantButton:disabled { background:#1b2437; border:1px solid #33425c; color:#8fa3c4; }
        """)

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

    def show_phone_guide(self) -> None:
        self._set_active("Phone Guide")
        dialog = WorkflowDialog(self, "Continue on Phone", SCREENS["phone"])
        dialog.setWindowIcon(self.windowIcon())

        def report(result: Result) -> None:
            self._log(result.message)
            dialog.set_status(result.message)
            self._play(result.ok)

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

        dialog.add_hotspot("Open MIBU", open_app)
        dialog.add_hotspot("Start Waiting", start_wait)
        dialog.add_hotspot("Verify Fastboot", verify_fastboot)
        dialog.add_hotspot("Done", dialog.accept)
        dialog.exec()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MIBU PC Helper")
    app.setWindowIcon(QIcon(find_asset("logo 1_transparent.png") or required_asset("mibu_app_icon.png")))
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
