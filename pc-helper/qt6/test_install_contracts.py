from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mibu_actions


class PackageVersionTests(unittest.TestCase):
    def test_parse_package_version(self) -> None:
        output = """
        Packages:
          Package [com.thetechguy.mibu]
            versionCode=2 minSdk=26 targetSdk=35
            versionName=0.2.0-dev
        """
        self.assertEqual("0.2.0-dev", mibu_actions.parse_package_version(output))

    def test_missing_version_returns_none(self) -> None:
        self.assertIsNone(mibu_actions.parse_package_version("Package not found"))

    def test_current_version_is_verified_without_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "MIBU.apk"
            apk.write_bytes(b"apk")
            with patch.object(mibu_actions, "check_device_ready", return_value=mibu_actions.Result(True, "ready")), patch.object(
                mibu_actions,
                "installed_package_version",
                return_value=mibu_actions.Result(True, mibu_actions.EXPECTED_APP_VERSION),
            ), patch.object(mibu_actions, "run_tool") as run_tool:
                result = mibu_actions.install_package(str(apk))
            self.assertTrue(result.ok)
            run_tool.assert_not_called()

    def test_old_installed_version_is_updated_and_reverified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "MIBU.apk"
            apk.write_bytes(b"apk")
            with patch.object(mibu_actions, "check_device_ready", return_value=mibu_actions.Result(True, "ready")), patch.object(
                mibu_actions,
                "installed_package_version",
                side_effect=[
                    mibu_actions.Result(True, "0.1.0-dev"),
                    mibu_actions.Result(True, mibu_actions.EXPECTED_APP_VERSION),
                ],
            ), patch.object(
                mibu_actions,
                "run_tool",
                return_value=mibu_actions.Result(True, "Success"),
            ) as run_tool:
                result = mibu_actions.install_package(str(apk))
            self.assertTrue(result.ok)
            run_tool.assert_called_once_with(["install", "-r", str(apk)], timeout=120)

    def test_version_mismatch_after_install_is_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / "MIBU.apk"
            apk.write_bytes(b"apk")
            with patch.object(mibu_actions, "check_device_ready", return_value=mibu_actions.Result(True, "ready")), patch.object(
                mibu_actions,
                "installed_package_version",
                side_effect=[
                    mibu_actions.Result(False, "not installed"),
                    mibu_actions.Result(True, "0.1.0-dev"),
                ],
            ), patch.object(
                mibu_actions,
                "run_tool",
                return_value=mibu_actions.Result(True, "Success"),
            ):
                result = mibu_actions.install_package(str(apk))
            self.assertFalse(result.ok)
            self.assertIn("expected", result.message)


if __name__ == "__main__":
    unittest.main()
