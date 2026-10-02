from __future__ import annotations

import unittest
from pathlib import Path


class PublicReleaseBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[2]
        cls.workflow = (cls.root / ".github/workflows/build.yml").read_text()
        cls.installer = (cls.root / "installer/MIBU-PC-Helper.iss").read_text()
        cls.builder = (cls.root / "installer/build_installer.ps1").read_text()
        cls.helper = (cls.root / "pc-helper/qt6/mibu_pc_helper_v3.py").read_text()
        cls.actions = (cls.root / "pc-helper/qt6/mibu_actions.py").read_text()

    def test_setup_contains_complete_release_bundle(self) -> None:
        self.assertIn(
            r'Source: "..\pc-helper\release\MIBU-PC-Helper\*";',
            self.installer,
        )
        self.assertIn("recursesubdirs", self.installer)

    def test_public_ci_artifact_is_setup_only(self) -> None:
        self.assertIn("name: MIBU-Windows-Release", self.workflow)
        self.assertIn(
            "path: installer/output/MIBU-PC-Helper-Setup-*.exe",
            self.workflow,
        )
        publish = self.workflow.split("  publish-release:", 1)[1]
        self.assertNotIn("MIBU-debug-apk", publish)
        self.assertNotIn("Portable", publish)
        self.assertNotIn("SHA256SUMS", publish)
        self.assertIn("Expected exactly one public MIBU setup package", self.workflow)
        self.assertIn("GH_REPO: ${{ github.repository }}", publish)

    def test_release_contains_remote_adb_single_instance_and_hotplug_contracts(self) -> None:
        self.assertIn("MIBU_ADB_SERVER", self.actions)
        self.assertIn("SingleInstanceGate", self.helper)
        self.assertIn("device_hotplug_timer.start(1500)", self.helper)
        self.assertIn(
            "Qt.ConnectionType.QueuedConnection",
            self.helper,
        )

    def test_tag_version_drives_installer_filename(self) -> None:
        self.assertIn('/DMyAppVersion=$Version', self.builder)
        self.assertIn('MIBU-PC-Helper-Setup-$Version.exe', self.builder)
        self.assertIn("GITHUB_REF_TYPE", self.workflow)


if __name__ == "__main__":
    unittest.main()
