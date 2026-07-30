from __future__ import annotations

import json
from pathlib import Path

from mibu_actions import Result
from mibu_english_conversion import (
    CHINESE_KEYBOARD_PACKAGES,
    GOOGLE_CORE_PACKAGES,
    MIBU_KEYBOARD_COMPONENT,
    MIBU_KEYBOARD_PACKAGE,
    OPTIONAL_CHINA_PACKAGES,
    apply_english_conversion,
    audit_english_conversion,
    rollback_english_conversion,
)


class FakeAdb:
    def __init__(
        self,
        *,
        include_google: bool = True,
        include_mibu_app: bool = True,
        include_mibu_keyboard: bool = True,
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
        if include_mibu_app:
            self.enabled.add(MIBU_KEYBOARD_PACKAGE)
        if include_mibu_app and include_mibu_keyboard:
            self.imes.append(MIBU_KEYBOARD_COMPONENT)
        self.disabled = {"com.miui.hybrid"}
        self.commands: list[list[str]] = []
        self.system_settings = {
            "system_locales": self.locale,
            "key_home_screen_search_bar": "1",
            "com.android.browser.enable_app_chooser_recommend": "1",
        }
        self.properties = {
            "ro.product.manufacturer": "Xiaomi",
            "ro.product.model": "Test Xiaomi",
            "ro.product.device": "test-device",
            "ro.mi.os.version.incremental": "OS2.0.TEST.CNXM",
            "ro.build.version.incremental": "fallback",
            "ro.product.mod_device": "test_cn",
            "ro.boot.verifiedbootstate": "green",
            "ro.boot.flash.locked": "1",
            "persist.sys.locale": self.locale,
        }

    def __call__(self, parts: list[str], timeout: int = 20) -> Result:
        del timeout
        self.commands.append(parts.copy())
        if parts[:3] == ["shell", "getprop", parts[2]]:
            return Result(True, self.properties.get(parts[2], ""))
        if parts[:4] == ["shell", "settings", "get", "system"]:
            return Result(True, self.system_settings.get(parts[4], "null"))
        if parts[:4] == ["shell", "settings", "put", "system"]:
            self.system_settings[parts[4]] = parts[5]
            if parts[4] == "system_locales":
                self.locale = parts[5]
            return Result(True, "")
        if parts[:4] == ["shell", "settings", "delete", "system"]:
            self.system_settings.pop(parts[4], None)
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
        return Result(False, "Unexpected command: " + " ".join(parts))


class ProtectedPackageFakeAdb(FakeAdb):
    protected_package = "com.xiaomi.market"

    def __init__(self) -> None:
        super().__init__()
        self.removed_for_user: set[str] = set()

    def __call__(self, parts: list[str], timeout: int = 20) -> Result:
        if parts[:3] == ["shell", "pm", "disable-user"] and parts[-1] == self.protected_package:
            self.commands.append(parts.copy())
            return Result(False, "SecurityException: Cannot disable system packages.")
        if parts[:3] == ["shell", "pm", "uninstall"]:
            self.commands.append(parts.copy())
            package = parts[-1]
            self.enabled.discard(package)
            self.disabled.discard(package)
            self.removed_for_user.add(package)
            return Result(True, "Success")
        if parts[:4] == ["shell", "cmd", "package", "install-existing"]:
            self.commands.append(parts.copy())
            package = parts[-1]
            self.removed_for_user.discard(package)
            self.enabled.add(package)
            return Result(True, f"Package {package} installed for user: 0")
        return super().__call__(parts, timeout)


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
    assert audit.preferred_ime == MIBU_KEYBOARD_COMPONENT
    assert audit.bootloader_state == "locked"


def test_apply_is_verified_reversible_and_never_uses_partition_commands(tmp_path: Path) -> None:
    adb = FakeAdb()
    snapshot = tmp_path / "conversion.json"
    result = apply_english_conversion(snapshot_path=snapshot, runner=adb, ready_check=ready)
    assert result.ok
    assert adb.locale == "en-US"
    assert adb.default_ime == MIBU_KEYBOARD_COMPONENT
    assert adb.system_settings["key_home_screen_search_bar"] == "0"
    assert adb.system_settings["com.android.browser.enable_app_chooser_recommend"] == "0"
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


def test_mibu_keyboard_is_verified_then_selected_before_china_keyboards_are_disabled(
    tmp_path: Path,
) -> None:
    adb = FakeAdb(include_google=False)
    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        runner=adb,
        ready_check=ready,
    )

    assert result.ok
    assert adb.default_ime == MIBU_KEYBOARD_COMPONENT
    assert MIBU_KEYBOARD_PACKAGE in adb.enabled
    assert "com.sohu.inputmethod.sogou.xiaomi" in adb.disabled
    assert not any(parts[:2] == ["install", "-r"] for parts in adb.commands)
    select_index = next(
        index
        for index, parts in enumerate(adb.commands)
        if parts[:3] == ["shell", "ime", "set"]
        and parts[3] == MIBU_KEYBOARD_COMPONENT
    )
    disable_index = next(
        index
        for index, parts in enumerate(adb.commands)
        if parts[:3] == ["shell", "pm", "disable-user"]
        and parts[-1] == "com.sohu.inputmethod.sogou.xiaomi"
    )
    assert select_index < disable_index


def test_old_mibu_without_keyboard_is_rejected_before_disabling_sogou(
    tmp_path: Path,
) -> None:
    adb = FakeAdb(include_mibu_keyboard=False)
    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        runner=adb,
        ready_check=ready,
    )

    assert not result.ok
    assert "does not expose the required English keyboard" in result.message
    assert not any(parts[:2] == ["install", "-r"] for parts in adb.commands)
    assert "com.sohu.inputmethod.sogou.xiaomi" in adb.enabled


def test_missing_mibu_app_requires_install_apk_before_conversion(tmp_path: Path) -> None:
    adb = FakeAdb(include_mibu_app=False, include_mibu_keyboard=False)
    result = apply_english_conversion(
        snapshot_path=tmp_path / "conversion.json",
        runner=adb,
        ready_check=ready,
    )

    assert not result.ok
    assert "Run Install APK first" in result.message
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


def test_protected_system_package_uses_reversible_per_user_hide_and_restores(
    tmp_path: Path,
) -> None:
    adb = ProtectedPackageFakeAdb()
    snapshot = tmp_path / "conversion.json"

    applied = apply_english_conversion(snapshot_path=snapshot, runner=adb, ready_check=ready)

    assert applied.ok
    assert adb.protected_package in adb.removed_for_user
    assert any(
        parts[:3] == ["shell", "pm", "uninstall"]
        and parts[-1] == adb.protected_package
        for parts in adb.commands
    )

    rolled_back = rollback_english_conversion(
        snapshot_path=snapshot,
        runner=adb,
        ready_check=ready,
    )

    assert rolled_back.ok
    assert adb.protected_package in adb.enabled
    assert adb.protected_package not in adb.removed_for_user
    assert "com.miui.video" in adb.enabled
    assert "com.miui.hybrid" in adb.disabled
    assert adb.system_settings["key_home_screen_search_bar"] == "1"
    assert adb.system_settings["com.android.browser.enable_app_chooser_recommend"] == "1"


def test_rollback_restores_previous_keyboard_without_disabling_mibu(tmp_path: Path) -> None:
    adb = FakeAdb()
    snapshot = tmp_path / "conversion.json"

    applied = apply_english_conversion(
        snapshot_path=snapshot,
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
    assert MIBU_KEYBOARD_PACKAGE in adb.enabled
    assert MIBU_KEYBOARD_PACKAGE not in adb.disabled


def test_retry_preserves_original_preinstall_snapshot(tmp_path: Path) -> None:
    adb = FakeAdb()
    snapshot = tmp_path / "conversion.json"

    first = apply_english_conversion(
        snapshot_path=snapshot,
        runner=adb,
        ready_check=ready,
    )
    assert first.ok
    original = json.loads(snapshot.read_text(encoding="utf-8"))
    assert MIBU_KEYBOARD_PACKAGE not in original["package_enabled"]

    second = apply_english_conversion(
        snapshot_path=snapshot,
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
