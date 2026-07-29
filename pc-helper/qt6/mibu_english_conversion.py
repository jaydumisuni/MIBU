from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from mibu_actions import Result, app_base_dir, check_device_ready, parse_installed_packages, run_tool

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
    "com.xiaomi.market",
    "com.xiaomi.gamecenter",
    "com.miui.video",
    "com.miui.player",
    "com.miui.contentextension",
    "com.miui.hybrid",
    "com.miui.hybrid.accessory",
)

CHINESE_KEYBOARD_PACKAGES = (
    "com.sohu.inputmethod.sogou.xiaomi",
    "com.iflytek.inputmethod.miui",
)

BUNDLED_KEYBOARD_PACKAGE = "helium314.keyboard.debug"
BUNDLED_KEYBOARD_COMPONENT = (
    "helium314.keyboard.debug/helium314.keyboard.latin.LatinIME"
)
BUNDLED_KEYBOARD_FILENAME = "HeliBoard-4.0-arm64-debug.apk"
BUNDLED_KEYBOARD_REMOTE_PATH = (
    "/sdcard/Download/HeliBoard-4.0-arm64-debug.apk"
)
BUNDLED_KEYBOARD_SHA256 = (
    "b36ccd9e2594ed552a736007420cb42b05ffdc92bd49fb59f28c37c9c2cf05b4"
)

KEYBOARD_PACKAGE_PRIORITY = (
    "com.google.android.inputmethod.latin",
    BUNDLED_KEYBOARD_PACKAGE,
    "com.android.inputmethod.latin",
)

SNAPSHOT_SCHEMA = 2


@dataclass(frozen=True)
class EnglishConversionAudit:
    manufacturer: str
    model: str
    device: str
    rom_build: str
    mod_device: str
    locale: str
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


def default_snapshot_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".thetechguy"
    return base / "THETECHGUY" / "MIBU" / "english-conversion-snapshot.json"


def bundled_keyboard_path(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit.resolve() if explicit.is_file() else None
    base = app_base_dir()
    candidates = (
        base / "resources" / "third_party" / BUNDLED_KEYBOARD_FILENAME,
        base / "_internal" / "resources" / "third_party" / BUNDLED_KEYBOARD_FILENAME,
        Path.cwd() / "resources" / "third_party" / BUNDLED_KEYBOARD_FILENAME,
        Path(__file__).resolve().parents[2]
        / "resources"
        / "third_party"
        / BUNDLED_KEYBOARD_FILENAME,
    )
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        locale=locale,
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
        f"Locale: {audit.locale}\n"
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
        | {BUNDLED_KEYBOARD_PACKAGE}
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


def _open_keyboard_installer(runner: AdbRunner, apk: Path) -> Result:
    pushed = _run(
        runner,
        ["push", str(apk), BUNDLED_KEYBOARD_REMOTE_PATH],
        180,
    )
    if not pushed.ok:
        return Result(
            False,
            "MIBU could not copy the verified keyboard to the phone. "
            + pushed.message,
        )
    opened = _run(
        runner,
        [
            "shell",
            "am",
            "start",
            "-W",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            f"file://{BUNDLED_KEYBOARD_REMOTE_PATH}",
            "-t",
            "application/vnd.android.package-archive",
            "--grant-read-uri-permission",
        ],
        60,
    )
    if not opened.ok:
        return Result(
            False,
            "The keyboard was copied to Downloads, but Xiaomi's installer "
            "could not be opened automatically. "
            + opened.message,
        )
    return Result(
        True,
        "Xiaomi's installer is open on the phone. Tap Allow/Install, then "
        "run English Conversion again.",
    )


def _ensure_english_keyboard(
    audit: EnglishConversionAudit,
    runner: AdbRunner,
    keyboard_apk_path: Path | None,
) -> tuple[Result, str]:
    if audit.preferred_ime:
        return Result(True, "Using an installed English keyboard."), audit.preferred_ime

    apk = bundled_keyboard_path(keyboard_apk_path)
    if apk is None:
        return (
            Result(
                False,
                "No English keyboard is installed and the verified bundled "
                f"{BUNDLED_KEYBOARD_FILENAME} is missing.",
            ),
            "",
        )
    try:
        apk_sha256 = _file_sha256(apk)
    except OSError as exc:
        return Result(False, f"Bundled English keyboard could not be read: {exc}"), ""
    if apk_sha256 != BUNDLED_KEYBOARD_SHA256:
        return (
            Result(
                False,
                "Bundled English keyboard failed SHA-256 verification. "
                "MIBU refused to install it.",
            ),
            "",
        )

    if BUNDLED_KEYBOARD_PACKAGE not in audit.installed_packages:
        installed = _run(runner, ["install", "-r", str(apk)], 180)
        if not installed.ok or "success" not in installed.message.lower():
            fallback = _open_keyboard_installer(runner, apk)
            return (
                Result(
                    False,
                    "Android did not install the bundled English keyboard. "
                    f"{fallback.message}\n"
                    f"{installed.message or 'No install output.'}",
                ),
                "",
            )
    else:
        _run(
            runner,
            ["shell", "pm", "enable", "--user", "0", BUNDLED_KEYBOARD_PACKAGE],
            25,
        )

    package_path = _run(
        runner, ["shell", "pm", "path", BUNDLED_KEYBOARD_PACKAGE], 25
    )
    if not package_path.ok or "package:" not in package_path.message:
        return (
            Result(
                False,
                "ADB reported the keyboard install, but package verification failed.",
            ),
            "",
        )

    component = _installed_ime_for_package(runner, BUNDLED_KEYBOARD_PACKAGE)
    if component != BUNDLED_KEYBOARD_COMPONENT:
        return (
            Result(
                False,
                "The installed keyboard did not expose the verified HeliBoard "
                f"input method. Expected {BUNDLED_KEYBOARD_COMPONENT}; got "
                f"{component or 'no service'}.",
            ),
            "",
        )
    return Result(True, "Bundled HeliBoard 4.0 installed and verified."), component


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

    keyboard_result, english_ime = _ensure_english_keyboard(
        audit, runner, keyboard_apk_path
    )
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
            disabled = _run(runner, ["shell", "pm", "disable-user", "--user", "0", package], 25)
            if disabled.ok and not _package_enabled(runner, package):
                completed.append(f"Disabled China package {package}")
            else:
                warnings.append(f"Could not disable China package {package}")

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

    for package, was_enabled in snapshot.package_enabled.items():
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

    if BUNDLED_KEYBOARD_PACKAGE not in snapshot.package_enabled:
        installed = _run(
            runner, ["shell", "pm", "path", BUNDLED_KEYBOARD_PACKAGE], 20
        )
        if installed.ok and "package:" in installed.message:
            deactivated = _run(
                runner,
                [
                    "shell",
                    "pm",
                    "disable-user",
                    "--user",
                    "0",
                    BUNDLED_KEYBOARD_PACKAGE,
                ],
                25,
            )
            (
                restored
                if deactivated.ok
                and not _package_enabled(runner, BUNDLED_KEYBOARD_PACKAGE)
                else failed
            ).append("MIBU-installed keyboard deactivated")

    message = "Rollback complete." if not failed else "Rollback finished with items that Android did not restore."
    message += "\nRestored: " + (", ".join(restored) if restored else "none")
    if failed:
        message += "\nNot restored: " + ", ".join(failed)
    return Result(not failed, message)
