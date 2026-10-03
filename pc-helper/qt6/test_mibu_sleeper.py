from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mibu_sleeper


class MibuSleeperContractTests(unittest.TestCase):
    def test_consumer_descriptor_is_stable_and_policy_bound(self):
        descriptor = mibu_sleeper.consumer_descriptor()
        self.assertEqual(descriptor["tool_id"], "mibu")
        self.assertEqual(descriptor["name"], "MIBU PC Helper")
        self.assertEqual(descriptor["repository"], "jaydumisuni/MIBU")
        self.assertIn("adb_transport", descriptor["capabilities"])
        self.assertIn("shared_sleeper_query", descriptor["capabilities"])
        self.assertIn("shared_learning_publish", descriptor["capabilities"])
        self.assertIn("smart_play_engine", descriptor["capabilities"])
        self.assertIn("caller_selects_job", descriptor["policy_tags"])
        self.assertIn("partition_backup_before_write", descriptor["policy_tags"])
        self.assertIn("xiaomi_official_result_authoritative", descriptor["policy_tags"])

    def test_public_build_can_remain_standalone_when_private_engine_is_absent(self):
        with patch.dict(os.environ, {"SLEEPER_AGENT_ROOT": ""}, clear=False):
            bridge = mibu_sleeper.MibuSleeperBridge()
        # Public CI may have no private Sleeper package. The bridge must fail closed, not break MIBU.
        if not bridge.available:
            result = bridge.status_result()
            self.assertFalse(result.ok)
            self.assertIn("Sleeper is not attached", result.message)

    def test_smart_play_descriptor_resolves_from_sleeper_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            sleeper_root = Path(td) / "Sleeper-agent"
            descriptor = (
                sleeper_root
                / ".workspace"
                / "smart-play-engine-build"
                / "engine-manifest.json"
            )
            descriptor.parent.mkdir(parents=True)
            descriptor.write_text("{}")
            bridge = object.__new__(mibu_sleeper.MibuSleeperBridge)
            bridge.engine_source = str(sleeper_root / "src")
            with patch.dict(
                os.environ,
                {"TTG_SMART_PLAY_DESCRIPTOR": "", "SLEEPER_AGENT_ROOT": ""},
                clear=False,
            ):
                self.assertEqual(bridge._smart_play_descriptor(), descriptor.resolve())

    def test_smart_play_fails_closed_when_sleeper_is_unavailable(self):
        bridge = object.__new__(mibu_sleeper.MibuSleeperBridge)
        bridge.available = False
        bridge.error = "not attached"
        bridge.engine_source = "missing"
        result = bridge.smart_play_result()
        self.assertFalse(result.ok)
        self.assertIn("Sleeper is not attached", result.message)

    def test_ui_keeps_one_persistent_smart_play_button(self):
        source = (
            Path(__file__).resolve().parent / "mibu_pc_helper_v3.py"
        ).read_text()
        self.assertIn('QPushButton("Smart Play")', source)
        self.assertIn('self.utility_buttons["Smart Play"]', source)
        self.assertIn("self.sleeper.smart_play_result", source)
        self.assertIn("def run_smart_play", source)

    def test_smart_play_release_gate_uses_gmail_only_for_qualification(self):
        source = (
            Path(__file__).resolve().parent / "mibu_sleeper.py"
        ).read_text()
        self.assertIn(
            "descriptor.qualification_build",
            source,
        )
        self.assertIn(
            "proof_package = descriptor.gmail_proof_package",
            source,
        )
        self.assertIn(
            "proof_package = descriptor.qualification_proof_package",
            source,
        )

    def test_smart_play_enables_bounded_same_serial_reconnect(self):
        source = (
            Path(__file__).resolve().parent / "mibu_sleeper.py"
        ).read_text()
        self.assertIn(
            "reconnect_window_seconds=45.0",
            source,
        )

    def test_smart_play_preflight_precedes_service_mode_upgrade(self):
        source = (
            Path(__file__).resolve().parent / "mibu_sleeper.py"
        ).read_text()
        preflight = source.index("preflight = strategy.qualify()")
        upgrade = source.index("sleeper.ensure_service_mode_package(")
        self.assertLess(preflight, upgrade)
        self.assertIn(
            "No package migration or Service Mode broker upgrade ",
            source,
        )
        self.assertIn('"was performed."', source)

    def test_contract_pins_the_proven_consumer_context_revision(self):
        self.assertEqual(
            mibu_sleeper.SLEEPER_CONTRACT_COMMIT,
            "671a2f752a953e4e5c765c9c284d8a449983d4c0",
        )


if __name__ == "__main__":
    unittest.main()
