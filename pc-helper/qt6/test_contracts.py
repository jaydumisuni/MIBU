from __future__ import annotations

import base64
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import mibu_actions
import mibu_runtime
import mibu_status


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

    def test_adb_parser_ignores_unrecognised_noise(self) -> None:
        output = "List of devices attached\nerror: protocol fault\nABC123\tdevice product:x\n"
        self.assertEqual([("ABC123", "device")], mibu_actions.parse_devices(output))

    def test_fastboot_parser_requires_real_device_rows(self) -> None:
        output = "< waiting for any device >\nABC123\tfastboot\nFinished. Total time: 0.001s\n"
        self.assertEqual([("ABC123", "fastboot")], mibu_actions.parse_fastboot_devices(output))

    def test_token_encoding_is_url_safe_and_reversible(self) -> None:
        original = "abc+/=tokenvaluewithsymbols"
        encoded = mibu_actions._encode_token(original)
        self.assertNotIn("\n", encoded)
        decoded = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
        self.assertEqual(original, decoded)

    def test_token_encoding_compacts_wrapped_copies(self) -> None:
        encoded = mibu_actions._encode_token("abc12345\nxyz67890")
        decoded = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
        self.assertEqual("abc12345xyz67890", decoded)

    def test_token_validation_bounds_and_control_characters(self) -> None:
        self.assertTrue(mibu_actions._valid_token("abcdefgh"))
        self.assertTrue(mibu_actions._valid_token("abcd\nefgh"))
        self.assertFalse(mibu_actions._valid_token("short"))
        self.assertFalse(mibu_actions._valid_token("x" * (mibu_actions.MAX_TOKEN_LENGTH + 1)))


class ServiceProofTests(unittest.TestCase):
    def test_service_armed_marker_is_success_for_matching_nonce(self) -> None:
        with patch.object(
            mibu_actions,
            "run_tool",
            return_value=mibu_actions.Result(True, "I/MIBU_SERVICE: WAITING_SERVICE_ARMED targetMidnight=123 nonce=abc12345"),
        ):
            result = mibu_actions._wait_for_log_outcome(
                "MIBU_SERVICE",
                "WAITING_SERVICE_ARMED",
                failure_markers=("WAITING_SERVICE_FAILED",),
                wait_seconds=1,
                nonce="abc12345",
            )
        self.assertTrue(result.ok)
        self.assertIn("WAITING_SERVICE_ARMED", result.message)

    def test_completed_race_marker_is_accepted_from_success_tuple(self) -> None:
        with patch.object(
            mibu_actions,
            "run_tool",
            return_value=mibu_actions.Result(True, "I/MIBU_SERVICE: WAITING_SERVICE_RECOVERED_COMPLETE nonce=abc12345"),
        ):
            result = mibu_actions._wait_for_log_outcome(
                "MIBU_SERVICE",
                ("WAITING_SERVICE_ARMED", "WAITING_SERVICE_RECOVERED_COMPLETE"),
                wait_seconds=1,
                nonce="abc12345",
            )
        self.assertTrue(result.ok)
        self.assertIn("WAITING_SERVICE_RECOVERED_COMPLETE", result.message)

    def test_stale_success_marker_with_wrong_nonce_is_rejected(self) -> None:
        with patch.object(
            mibu_actions,
            "run_tool",
            return_value=mibu_actions.Result(True, "I/MIBU_SERVICE: WAITING_SERVICE_ARMED nonce=oldnonce"),
        ), patch.object(mibu_actions.time, "sleep", return_value=None), patch.object(
            mibu_actions.time,
            "monotonic",
            side_effect=[0.0, 0.0, 2.0],
        ):
            result = mibu_actions._wait_for_log_outcome(
                "MIBU_SERVICE",
                "WAITING_SERVICE_ARMED",
                wait_seconds=1,
                nonce="newnonce",
            )
        self.assertFalse(result.ok)

    def test_service_failure_marker_rejects_immediately(self) -> None:
        with patch.object(
            mibu_actions,
            "run_tool",
            return_value=mibu_actions.Result(True, "E/MIBU_SERVICE: WAITING_SERVICE_FAILED nonce=abc12345"),
        ):
            result = mibu_actions._wait_for_log_outcome(
                "MIBU_SERVICE",
                "WAITING_SERVICE_ARMED",
                failure_markers=("WAITING_SERVICE_FAILED",),
                wait_seconds=1,
                nonce="abc12345",
            )
        self.assertFalse(result.ok)
        self.assertIn("WAITING_SERVICE_FAILED", result.message)

    def test_activity_started_marker_is_not_service_proof(self) -> None:
        with patch.object(
            mibu_actions,
            "run_tool",
            return_value=mibu_actions.Result(True, "I/MIBU_WAIT: WAITING_ACTIVITY_STARTED nonce=abc12345"),
        ), patch.object(mibu_actions.time, "sleep", return_value=None), patch.object(
            mibu_actions.time,
            "monotonic",
            side_effect=[0.0, 0.0, 2.0],
        ):
            result = mibu_actions._wait_for_log_outcome(
                "MIBU_SERVICE",
                "WAITING_SERVICE_ARMED",
                wait_seconds=1,
                nonce="abc12345",
            )
        self.assertFalse(result.ok)


class PhoneStatusTests(unittest.TestCase):
    def proof_line(
        self,
        *,
        nonce: str = "abc12345",
        protocol: int = mibu_status.EXPECTED_PROOF_PROTOCOL,
        app: str = mibu_actions.EXPECTED_APP_VERSION,
        verification: str = "WAITING_ARMED",
    ) -> str:
        return (
            f"I/MIBU_STATUS: STATUS nonce={nonce} protocol={protocol} app={app} "
            f"captures=READY verification={verification} community=COMMUNITY_ROUTE_UNKNOWN "
            "lanes=1:ARMED,2:ARMED,3:ARMED,4:ARMED"
        )

    def test_status_parser_accepts_matching_current_contract(self) -> None:
        status = mibu_status._parse_status(self.proof_line(), expected_nonce="abc12345")
        self.assertIsNotNone(status)
        assert status is not None
        self.assertEqual("abc12345", status.nonce)
        self.assertEqual(mibu_status.EXPECTED_PROOF_PROTOCOL, status.protocol)
        self.assertEqual(mibu_actions.EXPECTED_APP_VERSION, status.app_version)
        self.assertTrue(status.contract_current)
        self.assertTrue(status.captures_ready)
        self.assertFalse(status.timing_complete)
        self.assertEqual("WAITING_ARMED", status.verification)

    def test_status_parser_rejects_wrong_nonce(self) -> None:
        self.assertIsNone(mibu_status._parse_status(self.proof_line(nonce="stale123"), expected_nonce="fresh123"))

    def test_old_protocol_parses_but_is_not_current(self) -> None:
        status = mibu_status._parse_status(self.proof_line(protocol=1), expected_nonce="abc12345")
        self.assertIsNotNone(status)
        assert status is not None
        self.assertFalse(status.contract_current)

    def test_old_app_version_parses_but_is_not_current(self) -> None:
        status = mibu_status._parse_status(self.proof_line(app="0.1.0-dev"), expected_nonce="abc12345")
        self.assertIsNotNone(status)
        assert status is not None
        self.assertFalse(status.contract_current)

    def test_timing_complete_only_accepts_completion_states(self) -> None:
        status = mibu_status._parse_status(
            self.proof_line(verification="TIMING_WINDOW_REACHED"),
            expected_nonce="abc12345",
        )
        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.timing_complete)

    def test_status_parser_rejects_unrelated_log(self) -> None:
        self.assertIsNone(mibu_status._parse_status("I/Other: hello"))


class TimingTests(unittest.TestCase):
    def test_same_day_target_when_window_is_ahead(self) -> None:
        zone = ZoneInfo("Asia/Shanghai")
        now = datetime(2026, 7, 12, 23, 59, 57, tzinfo=zone)
        target = mibu_runtime.next_target(now)
        self.assertEqual((12, 23, 59, 58, 600000), (target.day, target.hour, target.minute, target.second, target.microsecond))

    def test_next_day_target_after_window(self) -> None:
        zone = ZoneInfo("Asia/Shanghai")
        now = datetime(2026, 7, 12, 23, 59, 59, tzinfo=zone)
        target = mibu_runtime.next_target(now)
        self.assertEqual((13, 23, 59, 58, 600000), (target.day, target.hour, target.minute, target.second, target.microsecond))


if __name__ == "__main__":
    unittest.main()
