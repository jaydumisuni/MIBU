from __future__ import annotations

import json
from pathlib import Path

from mibu_actions import Result
from mibu_english_conversion import (
    GOOGLE_CORE_PACKAGES,
    OPTIONAL_CHINA_PACKAGES,
    apply_english_conversion,
    audit_english_conversion,
    rollback_english_conversion,
)


class FakeAdb:
    def __init__(self, *, include_google: bool = True) -> None:
        self.locale = "zh-CN"
        self.default_ime = "com.sohu.inputmethod.sogou.xiaomi/.SogouIME"
        self.imes = [
            self.default_ime,
            "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME",
        ]
        self.enabled = {
            "com.xiaomi.market",
            "com.miui.video",
            "com.sohu.inputmethod.sogou.xiaomi",
        }
        if include_google:
            self.enabled.update(GOOGLE_CORE_PACKAGES)
            self.enabled.add("com.google.android.inputmethod.latin")
        self.disabled = {"com.miui.hybrid"}
        self.commands: list[list[str]] = []
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
    assert not (set(OPTIONAL_CHINA_PACKAGES) & adb.enabled)
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
    assert not result.ok
    assert "does not contain a complete enabled Google core" in result.message
    assert not any(parts[:2] == ["install", "-r"] for parts in adb.commands)


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
