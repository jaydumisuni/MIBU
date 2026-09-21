from __future__ import annotations

import os
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

    def test_contract_pins_the_proven_consumer_context_revision(self):
        self.assertEqual(
            mibu_sleeper.SLEEPER_CONTRACT_COMMIT,
            "d8966052c752399aea5de01e6b842d3296a7043b",
        )


if __name__ == "__main__":
    unittest.main()
