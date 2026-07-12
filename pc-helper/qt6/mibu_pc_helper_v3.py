#!/usr/bin/env python3
from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from mibu_actions import (
    check_fastboot_ready,
    fastboot_oem_info,
    launch_phone_app,
    reboot_to_fastboot,
    start_phone_waiting,
)
from mibu_pc_helper_v2 import Window as V2Window
from mibu_pc_helper_v2 import WorkflowDialog, required_asset
from mibu_status import query_phone_status
from ui_geometry import SCREENS


class Window(V2Window):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowIcon(QIcon(required_asset("mibu_app_icon.png")))

    def show_phone_guide(self) -> None:
        self._set_active("Phone Guide")
        dialog = WorkflowDialog(self, "Continue on Phone", SCREENS["phone"])
        dialog.setWindowIcon(self.windowIcon())

        def report(result) -> None:
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
            if not status.captures_ready:
                report(type(status_result)(False, "Phone proof says both fresh captures are not ready. Import Firefox + Chrome tokens first."))
                return
            result = start_phone_waiting()
            report(result)
            if not result.ok:
                return
            proof_result, proof = query_phone_status()
            if not proof_result.ok or proof is None:
                report(proof_result)
                return
            armed = proof.verification == "WAITING_ARMED"
            report(type(proof_result)(armed, proof.raw if armed else f"Waiting did not enter WAITING_ARMED. {proof.raw}"))

        def verify_fastboot() -> None:
            status_result, status = query_phone_status()
            if not status_result.ok or status is None:
                report(status_result)
                return
            if not status.timing_complete:
                report(type(status_result)(False, f"Phone timing proof is not complete yet. Current state: {status.verification}"))
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
