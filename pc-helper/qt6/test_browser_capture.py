from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mibu_browser_capture


class FakeChromeDriver:
    def __init__(self, cookies: dict[str, str]) -> None:
        self.cookies = cookies
        self.visited = ""
        self.closed = False
        self.refresh_count = 0

    def get(self, url: str) -> None:
        self.visited = url

    def get_cookie(self, name: str) -> dict[str, str] | None:
        value = self.cookies.get(name)
        return {"name": name, "value": value} if value else None

    def refresh(self) -> None:
        self.refresh_count += 1

    def quit(self) -> None:
        self.closed = True


class ChromeCaptureTests(unittest.TestCase):
    def test_valid_normal_profile_capture_skips_controlled_profile(self) -> None:
        with patch.object(
            mibu_browser_capture,
            "browser_path",
            return_value="C:/Chrome/chrome.exe",
        ), patch.object(
            mibu_browser_capture,
            "_capture_chrome_normal_profile",
            return_value=(mibu_browser_capture.Result(True, "captured; value hidden"), "normal-profile-token"),
        ), patch.object(
            mibu_browser_capture,
            "validate_xiaomi_capture",
            return_value=mibu_browser_capture.Result(True, "validated"),
        ), patch.object(
            mibu_browser_capture.webdriver,
            "Chrome",
        ) as controlled:
            result, token = mibu_browser_capture.capture_chrome_pop_token()

        self.assertTrue(result.ok)
        self.assertEqual("normal-profile-token", token)
        controlled.assert_not_called()

    def test_controlled_chrome_reads_pop_token_and_closes(self) -> None:
        driver = FakeChromeDriver({"popRunToken": "valid-pop-token"})
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            mibu_browser_capture.os.environ,
            {"LOCALAPPDATA": tmp},
        ), patch.object(
            mibu_browser_capture,
            "browser_path",
            return_value="C:/Chrome/chrome.exe",
        ), patch.object(
            mibu_browser_capture.webdriver,
            "Chrome",
            return_value=driver,
        ), patch.object(
            mibu_browser_capture,
            "_capture_chrome_normal_profile",
            return_value=(mibu_browser_capture.Result(False, "not available"), None),
        ), patch.object(
            mibu_browser_capture.time,
            "sleep",
            return_value=None,
        ), patch.object(
            mibu_browser_capture,
            "validate_xiaomi_capture",
            return_value=mibu_browser_capture.Result(True, "valid"),
        ):
            result, token = mibu_browser_capture.capture_chrome_pop_token(timeout_seconds=3)

        self.assertTrue(result.ok)
        self.assertEqual("valid-pop-token", token)
        self.assertEqual(mibu_browser_capture.LOGIN_URL, driver.visited)
        self.assertTrue(driver.closed)
        self.assertNotIn("valid-pop-token", result.message)

    def test_valid_chrome_service_token_is_safe_fallback(self) -> None:
        driver = FakeChromeDriver(
            {
                "popRunToken": "expired-pop-token",
                "new_bbs_serviceToken": "valid-service-token",
            }
        )

        def validate(token: str, _label: str) -> mibu_browser_capture.Result:
            return mibu_browser_capture.Result(token == "valid-service-token", "checked")

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            mibu_browser_capture.os.environ,
            {"LOCALAPPDATA": tmp},
        ), patch.object(
            mibu_browser_capture,
            "browser_path",
            return_value="C:/Chrome/chrome.exe",
        ), patch.object(
            mibu_browser_capture.webdriver,
            "Chrome",
            return_value=driver,
        ), patch.object(
            mibu_browser_capture,
            "_capture_chrome_normal_profile",
            return_value=(mibu_browser_capture.Result(False, "not available"), None),
        ), patch.object(
            mibu_browser_capture,
            "validate_xiaomi_capture",
            side_effect=validate,
        ):
            result, token = mibu_browser_capture.capture_chrome_pop_token(timeout_seconds=3)

        self.assertTrue(result.ok)
        self.assertEqual("valid-service-token", token)
        self.assertIn("service-token fallback", result.message)
        self.assertNotIn("valid-service-token", result.message)

    def test_capture_profile_is_persistent_and_app_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            mibu_browser_capture.os.environ,
            {"LOCALAPPDATA": tmp},
        ):
            profile = mibu_browser_capture.chrome_capture_profile_dir()
        self.assertEqual(Path(tmp) / "THETECHGUY TOOL" / "MIBU" / "ChromeCapture", profile)


if __name__ == "__main__":
    unittest.main()
