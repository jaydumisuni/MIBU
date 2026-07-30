from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from mibu_actions import Result, check_device_ready, parse_installed_packages, run_tool

AdbRunner = Callable[[list[str], int], Result]
ReadyCheck = Callable[[], Result]

GOOGLE_CORE_PACKAGES = (
    "com.google.android.gms",
    "com.google.android.gsf",
    "com.android.vending",
)

GOOGLE_OPTIONAL_PACKAGES = (
    "com.google.android.gsf.login",
    "com.google.android.syncadapters.contacts",
    "com.google.android.syncadapters.calendar",
)

# These are optional content/store packages. System UI, Settings, Security,
# provisioning, telephony and package installers are intentionally excluded.
OPTIONAL_CHINA_PACKAGES = (
    "com.android.browser",
    "com.xiaomi.market",
    "com.xiaomi.gamecenter",
    "com.xiaomi.youpin",
    "com.xiaomi.shop",
    "com.xiaomi.vipaccount",
    "com.miui.video",
    "com.miui.player",
    "com.miui.themestore",
    "com.miui.personalassistant",
    "com.miui.contentextension",
    "com.miui.hybrid",
    "com.miui.hybrid.accessory",
    "com.miui.newhome",
    "com.miui.fm",
    "com.eg.android.AlipayGphone",
    "com.smile.gifmaker",
    "com.baidu.searchbox",
    "com.baidu.BaiduMap",
    "com.xunmeng.pinduoduo",
    "com.phoenix.read",
    "com.ss.android.article.news",
    "com.ss.android.ugc.aweme",
    "com.mfashiongallery.emag",
    "com.sina.weibo",
    "com.duokan.reader",
    "com.mipay.wallet",
    "tv.danmaku.bili",
    "com.tencent.qqlive",
    "com.dragon.read",
)

CHINESE_KEYBOARD_PACKAGES = (
    "com.sohu.inputmethod.sogou.xiaomi",
    "com.iflytek.inputmethod.miui",
    "com.baidu.input_mi",
)

MIBU_KEYBOARD_PACKAGE = "com.thetechguy.mibu"
MIBU_KEYBOARD_COMPONENT = "com.thetechguy.mibu/.MibuEnglishImeService"

KEYBOARD_PACKAGE_PRIORITY = (
    MIBU_KEYBOARD_PACKAGE,
    "com.google.android.inputmethod.latin",
    "com.android.inputmethod.latin",
)

LAUNCHER_ENGLISH_SETTINGS = {
    "key_home_screen_search_bar": "0",
    "com.android.browser.enable_app_chooser_recommend": "0",
}

SNAPSHOT_SCHEMA = 4


@dataclass(frozen=True)
class EnglishConversionAudit:
    manufacturer: str
    model: str
    device: str
    rom_build: str
    mod_device: str
    verified_boot_state: str
    flash_locked: str
    locale: str
    launcher_search_bar: str
    browser_app_recommendations: str
    default_ime: str
    available_imes: tuple[str, ...]
    enabled_packages: frozenset[str]
    disabled_packages: frozenset[str]

    @property
    def is_xiaomi(self) -> bool:
        identity = f"{self.manufacturer} {self.model} {self.device}".lower()
        return any(marker in identity for marker in ("xiaomi", "redmi", "poco"))

    @property
    def is_china_rom(self) -> bool:
        build = f"{self.rom_build} {self.mod_device}".lower()
        return "cnxm" in build or self.mod_device.lower().endswith("_cn")

    @property
    def installed_packages(self) -> frozenset[str]:
        return self.enabled_packages | self.disabled_packages

    @property
    def google_core_ready(self) -> bool:
        return all(package in self.enabled_packages for package in GOOGLE_CORE_PACKAGES)

    @property
    def bootloader_state(self) -> str:
        if self.flash_locked == "1":
            return "locked"
        if self.flash_locked == "0":
            return "unlocked"
        if self.verified_boot_state.lower() == "orange":
            return "unlocked"
        return "unknown"

    @property
    def preferred_ime(self) -> str:
        for package in KEYBOARD_PACKAGE_PRIORITY:
            for component in self.available_imes:
                if component.startswith(package + "/"):
                    return component
        return ""


@dataclass(frozen=True)
class EnglishConversionSnapshot:
    schema: int
    created_utc: str
    device: str
    rom_build: str
    locale: str
    default_ime: str
    package_enabled: dict[str, bool]
    system_settings: dict[str, str | None]


def default_snapshot_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".thetechguy"
    return base / "THETECHGUY" / "MIBU" / "english-conversion-snapshot.json"


def _run(runner: AdbRunner, parts: list[str], timeout: int = 20) -> Result:
    return runner(parts, timeout)


def _read_value(runner: AdbRunner, parts: list[str], timeout: int = 20) -> str:
    result = _run(runner, parts, timeout)
    if not result.ok:
        return ""
    value = result.message.strip()
    return "" if value.lower() in {"null", "none"} else value


def _read_package_sets(runner: AdbRunner) -> tuple[Result, frozenset[str], frozenset[str]]:
    enabled = _run(runner, ["shell", "pm", "list", "packages", "-e"], 45)
    disabled = _run(runner, ["shell", "pm", "list", "packages", "-d"], 45)
    if not enabled.ok:
        return Result(False, "Android would not return enabled packages: " + enabled.message), frozenset(), frozenset()
    if not disabled.ok:
        return Result(False, "Android would not return disabled packages: " + disabled.message), frozenset(), frozenset()
    return (
        Result(True, "Package state read."),
        frozenset(parse_installed_packages(enabled.message)),
        frozenset(parse_installed_packages(disabled.message)),
    )


def audit_english_conversion(
    runner: AdbRunner = run_tool,
    ready_check: ReadyCheck = check_device_ready,
) -> tuple[Result, EnglishConversionAudit | None]:
    ready = ready_check()
    if not ready.ok:
        return ready, None

    package_result, enabled, disabled = _read_package_sets(runner)
    if not package_result.ok:
        return package_result, None

    locale = _read_value(runner, ["shell", "settings", "get", "system", "system_locales"])
    if not locale:
        locale = _read_value(runner, ["shell", "getprop", "persist.sys.locale"]) or "unknown"

    ime_output = _read_value(runner, ["shell", "ime", "list", "-s"])
    audit = EnglishConversionAudit(
        manufacturer=_read_value(runner, ["shell", "getprop", "ro.product.manufacturer"]) or "unknown",
        model=_read_value(runner, ["shell", "getprop", "ro.product.model"]) or "unknown",
        device=_read_value(runner, ["shell", "getprop", "ro.product.device"]) or "unknown",
        rom_build=(
            _read_value(runner, ["shell", "getprop", "ro.mi.os.version.incremental"])
            or _read_value(runner, ["shell", "getprop", "ro.build.version.incremental"])
            or "unknown"
        ),
        mod_device=_read_value(runner, ["shell", "getprop", "ro.product.mod_device"]) or "unknown",
        verified_boot_state=(
            _read_value(runner, ["shell", "getprop", "ro.boot.verifiedbootstate"])
            or "unknown"
        ),
        flash_locked=(
            _read_value(runner, ["shell", "getprop", "ro.boot.flash.locked"])
            or "unknown"
        ),
        locale=locale,
        launcher_search_bar=(
            _read_value(
                runner,
                ["shell", "settings", "get", "system", "key_home_screen_search_bar"],
            )
        ),
        browser_app_recommendations=(
            _read_value(
                runner,
                [
                    "shell",
                    "settings",
                    "get",
                    "system",
                    "com.android.browser.enable_app_chooser_recommend",
                ],
            )
        ),
        default_ime=_read_value(runner, ["shell", "settings", "get", "secure", "default_input_method"]),
        available_imes=tuple(line.strip() for line in ime_output.splitlines() if "/" in line),
        enabled_packages=enabled,
        disabled_packages=disabled,
    )

    google_state = ", ".join(
        f"{package.rsplit('.', 1)[-1]}="
        + ("enabled" if package in enabled else "disabled" if package in disabled else "missing")
        for package in GOOGLE_CORE_PACKAGES
    )
    optional_count = sum(package in audit.installed_packages for package in OPTIONAL_CHINA_PACKAGES)
    keyboard = audit.preferred_ime or "no English keyboard detected"
    summary = (
        f"Device: {audit.manufacturer} {audit.model}\n"
        f"ROM: {audit.rom_build} ({'China' if audit.is_china_rom else 'not identified as China'})\n"
        f"Bootloader: {audit.bootloader_state}; verified boot: {audit.verified_boot_state}\n"
        f"Locale: {audit.locale}\n"
        f"Launcher search content: {'visible' if audit.launcher_search_bar != '0' else 'hidden'}\n"
        f"Keyboard: {keyboard}\n"
        f"Google core: {google_state}\n"
        f"Optional China packages found: {optional_count}"
    )
    if not audit.is_xiaomi:
        return Result(False, "English Conversion is restricted to Xiaomi, Redmi and POCO devices.\n" + summary), audit
    return Result(True, summary), audit


def _snapshot_for(audit: EnglishConversionAudit) -> EnglishConversionSnapshot:
    touched = (
        set(GOOGLE_CORE_PACKAGES)
        | set(GOOGLE_OPTIONAL_PACKAGES)
        | set(OPTIONAL_CHINA_PACKAGES)
        | set(CHINESE_KEYBOARD_PACKAGES)
    )
    package_enabled = {
        package: package in audit.enabled_packages
        for package in sorted(touched)
        if package in audit.installed_packages
    }
    return EnglishConversionSnapshot(
        schema=SNAPSHOT_SCHEMA,
        created_utc=datetime.now(timezone.utc).isoformat(),
        device=audit.device,
        rom_build=audit.rom_build,
        locale=audit.locale,
        default_ime=audit.default_ime,
        package_enabled=package_enabled,
        system_settings={
            "key_home_screen_search_bar": audit.launcher_search_bar or None,
            "com.android.browser.enable_app_chooser_recommend": (
                audit.browser_app_recommendations or None
            ),
        },
    )


def _save_snapshot(snapshot: EnglishConversionSnapshot, destination: Path) -> Result:
    try:
        if destination.is_file():
            existing = json.loads(destination.read_text(encoding="utf-8"))
            if (
                int(existing.get("schema", -1)) == SNAPSHOT_SCHEMA
                and str(existing.get("device", "")) == snapshot.device
                and str(existing.get("rom_build", "")) == snapshot.rom_build
            ):
                return Result(
                    True,
                    f"Existing rollback snapshot preserved: {destination}",
                )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(asdict(snapshot), indent=2) + "\n", encoding="utf-8")
        return Result(True, f"Rollback snapshot saved: {destination}")
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return Result(False, f"Rollback snapshot could not be saved: {exc}")


def _package_enabled(runner: AdbRunner, package: str) -> bool:
    output = _run(runner, ["shell", "pm", "list", "packages", "-e", package], 20)
    return output.ok and package in parse_installed_packages(output.message)


def _hide_package_for_user(runner: AdbRunner, package: str) -> tuple[bool, str]:
    disabled = _run(runner, ["shell", "pm", "disable-user", "--user", "0", package], 25)
    if not _package_enabled(runner, package):
        return True, "disabled"

    removed = _run(runner, ["shell", "pm", "uninstall", "--user", "0", package], 45)
    if removed.ok and not _package_enabled(runner, package):
        return True, "hidden for this user"

    details = "; ".join(
        text for text in (disabled.message.strip(), removed.message.strip()) if text
    )
    return False, details or "Android rejected both reversible package operations"


def _installed_ime_for_package(runner: AdbRunner, package: str) -> str:
    output = _read_value(runner, ["shell", "ime", "list", "-s"])
    return next(
        (
            line.strip()
            for line in output.splitlines()
            if line.strip().startswith(package + "/")
        ),
        "",
    )


def _ensure_english_keyboard(
    audit: EnglishConversionAudit,
    runner: AdbRunner,
) -> tuple[Result, str]:
    if MIBU_KEYBOARD_PACKAGE not in audit.installed_packages:
        return (
            Result(
                False,
                "MIBU is not installed on the phone. Run Install APK first; "
                "the signed MIBU APK contains the verified English keyboard.",
            ),
            "",
        )

    package_path = _run(runner, ["shell", "pm", "path", MIBU_KEYBOARD_PACKAGE], 25)
    if not package_path.ok or "package:" not in package_path.message:
        return (
            Result(
                False,
                "MIBU is listed on the phone, but Android did not return its "
                "installed package path. English conversion stopped safely.",
            ),
            "",
        )

    component = _installed_ime_for_package(runner, MIBU_KEYBOARD_PACKAGE)
    if component != MIBU_KEYBOARD_COMPONENT:
        return (
            Result(
                False,
                "The installed MIBU build does not expose the required English "
                f"keyboard. Expected {MIBU_KEYBOARD_COMPONENT}; got "
                f"{component or 'no service'}. Run Install APK to update MIBU.",
            ),
            "",
        )
    return Result(True, "MIBU English keyboard package and service verified."), component


def apply_english_conversion(
    *,
    disable_optional_china_apps: bool = True,
    snapshot_path: Path | None = None,
    keyboard_apk_path: Path | None = None,
    runner: AdbRunner = run_tool,
    ready_check: ReadyCheck = check_device_ready,
) -> Result:
    audit_result, audit = audit_english_conversion(runner, ready_check)
    if not audit_result.ok or audit is None:
        return audit_result

    destination = snapshot_path or default_snapshot_path()
    saved = _save_snapshot(_snapshot_for(audit), destination)
    if not saved.ok:
        return saved

    completed: list[str] = []
    warnings: list[str] = []

    # Retained for compatibility with older callers; MIBU now supplies its own
    # signed keyboard and never installs an unrelated keyboard package.
    _ = keyboard_apk_path
    keyboard_result, english_ime = _ensure_english_keyboard(audit, runner)
    if not keyboard_result.ok:
        return Result(
            False,
            "English conversion stopped before disabling the existing keyboard.\n"
            + saved.message
            + "\n"
            + keyboard_result.message,
        )
    completed.append(keyboard_result.message)

    _run(runner, ["shell", "ime", "enable", english_ime], 20)
    selected = _run(runner, ["shell", "ime", "set", english_ime], 20)
    ime_after = _read_value(
        runner,
        ["shell", "settings", "get", "secure", "default_input_method"],
    )
    if not selected.ok or ime_after != english_ime:
        return Result(
            False,
            "English conversion stopped before disabling the existing keyboard.\n"
            + saved.message
            + "\nAndroid did not allow the verified English keyboard to be selected.",
        )
    completed.append("English keyboard selected and verified")

    locale_set = _run(runner, ["shell", "settings", "put", "system", "system_locales", "en-US"], 20)
    locale_after = _read_value(runner, ["shell", "settings", "get", "system", "system_locales"])
    if locale_set.ok and "en-US" in locale_after:
        completed.append("English (United States) locale verified")
    else:
        warnings.append("Android did not grant the shell permission to change the full system locale")

    for key, value in LAUNCHER_ENGLISH_SETTINGS.items():
        changed = _run(
            runner,
            ["shell", "settings", "put", "system", key, value],
            20,
        )
        after = _read_value(
            runner,
            ["shell", "settings", "get", "system", key],
        )
        if changed.ok and after == value:
            completed.append(f"Disabled China launcher content setting {key}")
        else:
            warnings.append(f"Could not change launcher content setting {key}")

    for package in GOOGLE_CORE_PACKAGES + GOOGLE_OPTIONAL_PACKAGES:
        if package in audit.disabled_packages:
            enabled = _run(runner, ["shell", "pm", "enable", "--user", "0", package], 25)
            if enabled.ok and _package_enabled(runner, package):
                completed.append(f"Enabled existing Google component {package}")
            else:
                warnings.append(f"Could not enable existing Google component {package}")

    if disable_optional_china_apps:
        for package in OPTIONAL_CHINA_PACKAGES + CHINESE_KEYBOARD_PACKAGES:
            if package not in audit.enabled_packages:
                continue
            if english_ime.startswith(package + "/"):
                continue
            hidden, operation = _hide_package_for_user(runner, package)
            if hidden:
                completed.append(f"{operation.capitalize()} China package {package}")
            else:
                warnings.append(f"Could not hide China package {package}: {operation}")

    _, verified = audit_english_conversion(runner, ready_check)
    google_ready = bool(verified and verified.google_core_ready)
    if not google_ready:
        warnings.append(
            "This ROM does not contain a complete enabled Google core. MIBU will not sideload mismatched "
            "privileged packages; finish with a verified compatible Global ROM after official unlock."
        )

    if verified and verified.is_china_rom:
        warnings.append(
            "The controllable user layer is English, but this remains a China ROM. "
            "ROM-signed recovery, security and setup screens can still contain "
            "Chinese until an officially unlocked device is flashed with a verified "
            "compatible Global ROM."
        )

    china_apps_disabled = bool(
        verified
        and not any(
            package in verified.enabled_packages
            for package in OPTIONAL_CHINA_PACKAGES + CHINESE_KEYBOARD_PACKAGES
        )
    )
    successful = bool(
        verified
        and "en-US" in verified.locale
        and verified.default_ime == english_ime
        and verified.preferred_ime == english_ime
        and verified.launcher_search_bar == "0"
        and verified.browser_app_recommendations == "0"
        and china_apps_disabled
    )
    heading = (
        "Controllable English conversion verified."
        if successful
        else "English conversion completed with limits."
    )
    details = [heading, saved.message]
    if completed:
        details.append("\nCompleted:\n- " + "\n- ".join(completed))
    if warnings:
        details.append("\nNeeds attention:\n- " + "\n- ".join(dict.fromkeys(warnings)))
    return Result(successful, "\n".join(details))


def rollback_english_conversion(
    *,
    snapshot_path: Path | None = None,
    runner: AdbRunner = run_tool,
    ready_check: ReadyCheck = check_device_ready,
) -> Result:
    ready = ready_check()
    if not ready.ok:
        return ready
    source = snapshot_path or default_snapshot_path()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        snapshot = EnglishConversionSnapshot(
            schema=int(data["schema"]),
            created_utc=str(data["created_utc"]),
            device=str(data["device"]),
            rom_build=str(data["rom_build"]),
            locale=str(data["locale"]),
            default_ime=str(data["default_ime"]),
            package_enabled={str(key): bool(value) for key, value in data["package_enabled"].items()},
            system_settings={
                str(key): None if value is None else str(value)
                for key, value in data["system_settings"].items()
            },
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return Result(False, f"No valid English Conversion rollback snapshot is available: {exc}")
    if snapshot.schema != SNAPSHOT_SCHEMA:
        return Result(False, f"Unsupported rollback snapshot schema: {snapshot.schema}")
    audit_result, current = audit_english_conversion(runner, ready_check)
    if not audit_result.ok or current is None:
        return audit_result
    if current.device != snapshot.device or current.rom_build != snapshot.rom_build:
        return Result(
            False,
            "Rollback snapshot belongs to a different device or ROM build. "
            "MIBU refused to apply it.",
        )

    restored: list[str] = []
    failed: list[str] = []
    if snapshot.locale and snapshot.locale != "unknown":
        changed = _run(runner, ["shell", "settings", "put", "system", "system_locales", snapshot.locale], 20)
        locale_after = _read_value(runner, ["shell", "settings", "get", "system", "system_locales"])
        (restored if changed.ok and locale_after == snapshot.locale else failed).append("locale")

    for key, value in snapshot.system_settings.items():
        operation = "delete" if value is None else "put"
        parts = ["shell", "settings", operation, "system", key]
        if value is not None:
            parts.append(value)
        changed = _run(runner, parts, 20)
        after = _read_value(
            runner,
            ["shell", "settings", "get", "system", key],
        )
        expected = "" if value is None else value
        (restored if changed.ok and after == expected else failed).append(key)

    for package, was_enabled in snapshot.package_enabled.items():
        if package not in current.installed_packages:
            installed = _run(
                runner,
                ["shell", "cmd", "package", "install-existing", "--user", "0", package],
                45,
            )
            if not installed.ok:
                failed.append(package)
                continue
        command = "enable" if was_enabled else "disable-user"
        parts = ["shell", "pm", command, "--user", "0", package]
        changed = _run(runner, parts, 25)
        is_enabled = _package_enabled(runner, package)
        (restored if changed.ok and is_enabled == was_enabled else failed).append(package)

    if snapshot.default_ime:
        _run(runner, ["shell", "ime", "enable", snapshot.default_ime], 20)
        selected = _run(runner, ["shell", "ime", "set", snapshot.default_ime], 20)
        ime_after = _read_value(runner, ["shell", "settings", "get", "secure", "default_input_method"])
        (restored if selected.ok and ime_after == snapshot.default_ime else failed).append("keyboard")

    message = "Rollback complete." if not failed else "Rollback finished with items that Android did not restore."
    message += "\nRestored: " + (", ".join(restored) if restored else "none")
    if failed:
        message += "\nNot restored: " + ", ".join(failed)
    return Result(not failed, message)
