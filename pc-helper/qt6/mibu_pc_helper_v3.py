#!/usr/bin/env python3
from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

import mibu_pc_helper_v2 as base_ui
from mibu_actions import (
    Result,
    check_fastboot_ready,
    fastboot_oem_info,
    launch_phone_app,
    reboot_to_fastboot,
    start_phone_waiting,
)
from mibu_pc_helper_v2 import Window as V2Window
from mibu_pc_helper_v2 import WorkflowDialog as V2WorkflowDialog
from mibu_pc_helper_v2 import required_asset
from mibu_status import query_phone_status
from ui_geometry import POPUP_CLOSE_RECT, SCREENS


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
        self.setWindowIcon(QIcon(required_asset("mibu_app_icon.png")))

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
            armed = proof.verification == "WAITING_ARMED"
            report(Result(armed, proof.raw if armed else f"Foreground service proof succeeded, but phone state did not remain WAITING_ARMED. {proof.raw}"))

        def verify_fastboot() -> None:
            status_result, status = query_phone_status()
            if not status_result.ok or status is None:
                report(status_result)
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
    app.setWindowIcon(QIcon(required_asset("mibu_app_icon.png")))
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
