from __future__ import annotations

import base64
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import mibu_actions
import mibu_pc_helper_v2
import mibu_status
from ui_geometry import POPUP_CLOSE_ART_BOUNDS, POPUP_CLOSE_RECT, SCREENS


def rect_contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return ox <= ix and oy <= iy and ox + ow >= ix + iw and oy + oh >= iy + ih


class DeviceParsingTests(unittest.TestCase):
    def test_parse_online_device(self) -> None:
        serial, state = mibu_actions.parse_device_state("List of devices attached\nABC123\tdevice\n")
        self.assertEqual(("ABC123", "device"), (serial, state))

    def test_parse_unauthorized_device(self) -> None:
        serial, state = mibu_actions.parse_device_state("List of devices attached\nABC123\tunauthorized\n")
        self.assertEqual(("ABC123", "unauthorized"), (serial, state))

    def test_parse_empty_device_list(self) -> None:
        self.assertEqual(("", "none"), mibu_actions.parse_device_state("List of devices attached\n\n"))

    def test_parse_multiple_devices_without_daemon_noise(self) -> None:
        output = "* daemon started successfully *\nList of devices attached\nABC123\tdevice\nXYZ999\toffline\n"
        self.assertEqual([("ABC123", "device"), ("XYZ999", "offline")], mibu_actions.parse_devices(output))

    def test_token_encoding_is_url_safe_and_reversible(self) -> None:
        original = "abc+/= token value\nwith symbols"
        encoded = mibu_actions._encode_token(original)
        self.assertNotIn("\n", encoded)
        decoded = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
        self.assertEqual(original, decoded)


class PhoneStatusTests(unittest.TestCase):
    def test_status_parser_accepts_proof_line(self) -> None:
        line = "I/MIBU_STATUS: STATUS captures=READY verification=WAITING_ARMED community=COMMUNITY_ROUTE_UNKNOWN lanes=1:ARMED,2:ARMED,3:ARMED,4:ARMED"
        status = mibu_status._parse_status(line)
        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.captures_ready)
        self.assertFalse(status.timing_complete)
        self.assertEqual("WAITING_ARMED", status.verification)

    def test_timing_complete_only_accepts_completion_states(self) -> None:
        line = "STATUS captures=READY verification=TIMING_WINDOW_REACHED community=COMMUNITY_DEVICE_CONFIRMED lanes=1:WINDOW_REACHED,2:WINDOW_REACHED,3:WINDOW_REACHED,4:WINDOW_REACHED"
        status = mibu_status._parse_status(line)
        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.timing_complete)

    def test_status_parser_rejects_unrelated_log(self) -> None:
        self.assertIsNone(mibu_status._parse_status("I/Other: hello"))


class TimingTests(unittest.TestCase):
    def test_same_day_target_when_window_is_ahead(self) -> None:
        zone = ZoneInfo("Asia/Shanghai")
        now = datetime(2026, 7, 12, 23, 59, 57, tzinfo=zone)
        target = mibu_pc_helper_v2.next_target(now)
        self.assertEqual((12, 23, 59, 58, 600000), (target.day, target.hour, target.minute, target.second, target.microsecond))

    def test_next_day_target_after_window(self) -> None:
        zone = ZoneInfo("Asia/Shanghai")
        now = datetime(2026, 7, 12, 23, 59, 59, tzinfo=zone)
        target = mibu_pc_helper_v2.next_target(now)
        self.assertEqual((13, 23, 59, 58, 600000), (target.day, target.hour, target.minute, target.second, target.microsecond))


class GeometryTests(unittest.TestCase):
    def test_exact_screen_and_button_contract(self) -> None:
        self.assertEqual(5, len(SCREENS))
        self.assertEqual(
            {"Device Check", "Install APK", "Login & Get Token", "Phone Guide"},
            set(SCREENS["main"].hotspots),
        )

    def test_normalized_rectangles_remain_inside_canvas(self) -> None:
        for screen in SCREENS.values():
            for label in screen.hotspots:
                x, y, width, height = screen.normalized(label)
                self.assertGreaterEqual(x, 0.0)
                self.assertGreaterEqual(y, 0.0)
                self.assertGreater(width, 0.0)
                self.assertGreater(height, 0.0)
                self.assertLessEqual(x + width, 1.0)
                self.assertLessEqual(y + height, 1.0)

    def test_close_hotspot_fully_contains_visible_close_art(self) -> None:
        self.assertTrue(rect_contains(POPUP_CLOSE_RECT, POPUP_CLOSE_ART_BOUNDS))
        for screen_name, screen in SCREENS.items():
            if screen_name == "main":
                continue
            x, y, width, height = screen.normalized_rect(POPUP_CLOSE_RECT)
            self.assertGreaterEqual(x, 0.0)
            self.assertGreaterEqual(y, 0.0)
            self.assertLessEqual(x + width, 1.0)
            self.assertLessEqual(y + height, 1.0)

    def test_windows_icon_uses_android_icon_geometry(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        android_icon = (repo_root / "android/app/src/main/res/drawable/ic_mibu.xml").read_text(encoding="utf-8")
        pc_icon = (repo_root / "resources/expected ui/pc/mibu_app_icon.svg").read_text(encoding="utf-8")
        for path_fragment in (
            "M54,8 C28,8 8,28 8,54",
            "M31,43 C37,26 58,20 70,35",
            "M36,49 L50,49 L50,56 L36,56",
            "M20,76 L38,76 L38,92 L20,92",
            "M48,77 L62,77 L62,91 L48,91",
        ):
            self.assertIn(path_fragment, android_icon)
            self.assertIn(path_fragment, pc_icon)


if __name__ == "__main__":
    unittest.main()
