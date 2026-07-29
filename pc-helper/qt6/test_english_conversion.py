from __future__ import annotations

import json
from pathlib import Path

from mibu_actions import Result
from mibu_english_conversion import (
    BUNDLED_KEYBOARD_COMPONENT,
    BUNDLED_KEYBOARD_PACKAGE,
    CHINESE_KEYBOARD_PACKAGES,
    GOOGLE_CORE_PACKAGES,
    OPTIONAL_CHINA_PACKAGES,
    apply_english_conversion,
    audit_english_conversion,
    bundled_keyboard_path,
    rollback_english_conversion,
)


class FakeAdb:
    def __init__(
        self,
        *,
        include_google: bool = True,
        include_english_keyboard: bool = True,
        install_success: bool = True,
    ) -> None:
        self.locale = "zh-CN"
        self.default_ime = "com.sohu.inputmethod.sogou.xiaomi/.SogouIME"
        self.imes = [self.default_ime]
        self.enabled = {
            "com.xiaomi.market",
            "com.miui.video",
            "com.sohu.inputmethod.sogou.xiaomi",
        }
        if include_google:
            self.enabled.update(GOOGLE_CORE_PACKAGES)
        if include_english_keyboard:
            self.enabled.add("com.google.android.inputmethod.latin")
            self.imes.append(
                "com.google.android.inputmethod.latin/"
                "com.android.inputmethod.latin.LatinIME"
            )
        self.disabled = {"com.miui.hybrid"}
        self.commands: list[list[str]] = []
        self.install_success = install_success
        self.properties = {
            "ro.product.manufacturer": "Xiaomi",
            "ro.product.model": "Test Xiaomi",
            "ro.product.device": "test-device",
            "ro.mi.os.version.incremental": "OS2.0.TEST.CNXM",
            "ro.build.version.incremental": "fallback",
            "ro.product.mod_device": "test_cn",
            "persist.sys.locale": self.locale,
        }

    def __call__(self, parts: list[str], timeout: int = 20) -> Result:
        del timeout
        self.commands.append(parts.copy())
        if parts[:3] == ["shell", "getprop", parts[2]]:
            return Result(True, self.properties.get(parts[2], ""))
        if parts[:5] == ["shell", "settings", "get", "system", "system_locales"]:
            return Result(True, self.locale)
        if parts[:5] == ["shell", "settings", "put", "system", "system_locales"]:
            self.locale = parts[5]
            return Result(True, "")
        if parts[:5] == ["shell", "settings", "get", "secure", "default_input_method"]:
            return Result(True, self.default_ime)
        if parts[:4] == ["shell", "ime", "list", "-s"]:
            return Result(True, "\n".join(self.imes))
        if parts[:3] == ["shell", "ime", "enable"]:
            return Result(True, f"Input method {parts[3]} now enabled")
        if parts[:3] == ["shell", "ime", "set"]:
            self.default_ime = parts[3]
            return Result(True, f"Input method {parts[3]} selected")
        if parts[:5] == ["shell", "pm", "list", "packages", "-e"]:
            packages = sorted(self.enabled)
            if len(parts) > 5:
                packages = [package for package in packages if parts[5] in package]
            return Result(True, "\n".join(f"package:{package}" for package in packages))
        if parts[:5] == ["shell", "pm", "list", "packages", "-d"]:
            return Result(True, "\n".join(f"package:{package}" for package in sorted(self.disabled)))
        if parts[:3] == ["shell", "pm", "enable"]:
            package = parts[-1]
            self.disabled.discard(package)
            self.enabled.add(package)
            return Result(True, f"Package {package} new state: enabled")
        if parts[:3] == ["shell", "pm", "disable-user"]:
            package = parts[-1]
            self.enabled.discard(package)
            self.disabled.add(package)
            return Result(True, f"Package {package} new state: disabled-user")
        if parts[:3] == ["shell", "pm", "path"]:
            package = parts[3]
            if package in self.enabled or package in self.disabled:
                return Result(True, f"package:/data/app/{package}/base.apk")
            return Result(False, "")
        if parts[:2] == ["install", "-r"]:
            if not self.install_success:
                return Result(
                    False,
                    "Failure [INSTALL_FAILED_USER_RESTRICTED: Install canceled by user]",
                )
            self.enabled.add(BUNDLED_KEYBOARD_PACKAGE)
            if BUNDLED_KEYBOARD_COMPONENT not in self.imes:
                self.imes.append(BUNDLED_KEYBOARD_COMPONENT)
            return Result(True, "Success")
        if parts and parts[0] == "push":
            return Result(True, "1 file pushed")
        if parts[:4] == ["shell", "am", "start", "-W"]:
            return Result(True, "Status: ok")
        return Result(False, "Unexpected command: " + " ".join(parts))


def ready() -> Result:
    return Result(True, "Device online")


def test_audit_reports_real_china_rom_state() -> None:
    adb = FakeAdb()
    result, audit = audit_english_conversion(adb, ready)
    assert result.ok
    assert audit is not None
    assert audit.is_xiaomi
    assert audit.is_china_rom
    assert audit.locale == "zh-CN"
    assert audit.google_core_ready
    assert audit.preferred_ime.startswith("com.google.android.inputmethod.latin/")


def test_apply_is_verified_reversible_and_never_uses_partition_commands(tmp_path: Path) -> None:
    adb = FakeAdb()
    snapshot = tmp_path / "conversion.json"
    result = apply_english_conversion(snapshot_path=snapshot, runner=adb, ready_check=ready)
    assert result.ok
    assert adb.locale == "en-US"
    assert adb.default_ime.startswith("com.google.android.inputmethod.latin/")
    assert not (
        set(OPTIONAL_CHINA_PACKAGES + CHINESE_KEYBOARD_PACKAGES) & adb.enabled
    )
    assert snapshot.is_file()

    command_text = "\n".join(" ".join(parts) for parts in adb.commands).lower()
    for forbidden in ("dd ", "/dev/block", "frp", "proinfo", "fastboot", "uninstall"):
        assert forbidden not in command_text

    saved = json.loads(snapshot.read_text(encoding="utf-8"))
    assert saved["locale"] == "zh-CN"
    assert saved["default_ime"].startswith("com.sohu.inputmethod")


def test_missing_google_core_is_reported_instead_of_sideloaded(tmp_path: Path) -> None:
    adb = FakeAdb(include_google=False)
    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        runner=adb,
        ready_check=ready,
    )
    assert result.ok
    assert "does not contain a complete enabled Google core" in result.message
    assert not any(parts[:2] == ["install", "-r"] for parts in adb.commands)


def test_bundled_english_keyboard_is_installed_verified_then_selected(
    tmp_path: Path,
) -> None:
    adb = FakeAdb(include_google=False, include_english_keyboard=False)
    keyboard_apk = bundled_keyboard_path()
    assert keyboard_apk is not None

    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        keyboard_apk_path=keyboard_apk,
        runner=adb,
        ready_check=ready,
    )

    assert result.ok
    assert adb.default_ime == BUNDLED_KEYBOARD_COMPONENT
    assert BUNDLED_KEYBOARD_PACKAGE in adb.enabled
    assert "com.sohu.inputmethod.sogou.xiaomi" in adb.disabled
    install_index = next(
        index
        for index, parts in enumerate(adb.commands)
        if parts[:2] == ["install", "-r"]
    )
    select_index = next(
        index
        for index, parts in enumerate(adb.commands)
        if parts[:3] == ["shell", "ime", "set"]
        and parts[3] == BUNDLED_KEYBOARD_COMPONENT
    )
    disable_index = next(
        index
        for index, parts in enumerate(adb.commands)
        if parts[:3] == ["shell", "pm", "disable-user"]
        and parts[-1] == "com.sohu.inputmethod.sogou.xiaomi"
    )
    assert install_index < select_index < disable_index


def test_tampered_bundled_keyboard_is_rejected(tmp_path: Path) -> None:
    adb = FakeAdb(include_english_keyboard=False)
    keyboard_apk = tmp_path / "HeliBoard.apk"
    keyboard_apk.write_bytes(b"not the verified keyboard")

    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        keyboard_apk_path=keyboard_apk,
        runner=adb,
        ready_check=ready,
    )

    assert not result.ok
    assert "failed SHA-256 verification" in result.message
    assert not any(parts[:2] == ["install", "-r"] for parts in adb.commands)


def test_restricted_install_opens_xiaomi_installer_without_disabling_sogou(
    tmp_path: Path,
) -> None:
    adb = FakeAdb(include_english_keyboard=False, install_success=False)
    keyboard_apk = bundled_keyboard_path()
    assert keyboard_apk is not None

    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        keyboard_apk_path=keyboard_apk,
        runner=adb,
        ready_check=ready,
    )

    assert not result.ok
    assert "installer is open on the phone" in result.message
    assert any(parts and parts[0] == "push" for parts in adb.commands)
    assert any(parts[:4] == ["shell", "am", "start", "-W"] for parts in adb.commands)
    assert "com.sohu.inputmethod.sogou.xiaomi" in adb.enabled


def test_rollback_restores_locale_keyboard_and_package_state(tmp_path: Path) -> None:
    adb = FakeAdb()
    snapshot = tmp_path / "conversion.json"
    applied = apply_english_conversion(snapshot_path=snapshot, runner=adb, ready_check=ready)
    assert applied.ok

    rolled_back = rollback_english_conversion(snapshot_path=snapshot, runner=adb, ready_check=ready)
    assert rolled_back.ok
    assert adb.locale == "zh-CN"
    assert adb.default_ime.startswith("com.sohu.inputmethod")
    assert "com.xiaomi.market" in adb.enabled
    assert "com.miui.video" in adb.enabled
    assert "com.miui.hybrid" in adb.disabled


def test_rollback_deactivates_keyboard_that_mibu_installed(tmp_path: Path) -> None:
    adb = FakeAdb(include_english_keyboard=False)
    keyboard_apk = bundled_keyboard_path()
    assert keyboard_apk is not None
    snapshot = tmp_path / "conversion.json"

    applied = apply_english_conversion(
        snapshot_path=snapshot,
        keyboard_apk_path=keyboard_apk,
        runner=adb,
        ready_check=ready,
    )
    assert applied.ok

    rolled_back = rollback_english_conversion(
        snapshot_path=snapshot,
        runner=adb,
        ready_check=ready,
    )
    assert rolled_back.ok
    assert adb.default_ime.startswith("com.sohu.inputmethod")
    assert BUNDLED_KEYBOARD_PACKAGE in adb.disabled


def test_retry_preserves_original_preinstall_snapshot(tmp_path: Path) -> None:
    adb = FakeAdb(include_english_keyboard=False)
    keyboard_apk = bundled_keyboard_path()
    assert keyboard_apk is not None
    snapshot = tmp_path / "conversion.json"

    first = apply_english_conversion(
        snapshot_path=snapshot,
        keyboard_apk_path=keyboard_apk,
        runner=adb,
        ready_check=ready,
    )
    assert first.ok
    original = json.loads(snapshot.read_text(encoding="utf-8"))
    assert BUNDLED_KEYBOARD_PACKAGE not in original["package_enabled"]

    second = apply_english_conversion(
        snapshot_path=snapshot,
        keyboard_apk_path=keyboard_apk,
        runner=adb,
        ready_check=ready,
    )
    assert second.ok
    assert "Existing rollback snapshot preserved" in second.message
    assert json.loads(snapshot.read_text(encoding="utf-8")) == original


def test_rollback_refuses_snapshot_from_different_rom(tmp_path: Path) -> None:
    adb = FakeAdb()
    snapshot = tmp_path / "conversion.json"
    applied = apply_english_conversion(
        snapshot_path=snapshot,
        runner=adb,
        ready_check=ready,
    )
    assert applied.ok
    adb.properties["ro.mi.os.version.incremental"] = "OS2.0.OTHER.CNXM"

    rolled_back = rollback_english_conversion(
        snapshot_path=snapshot,
        runner=adb,
        ready_check=ready,
    )

    assert not rolled_back.ok
    assert "different device or ROM build" in rolled_back.message
