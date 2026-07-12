# MIBU Architecture

## Product boundary

MIBU is a two-part **timing, state-proof and official-tool handoff assistant** for a Xiaomi device the user owns or is authorised to service.

It does not claim that reaching a timing window means Xiaomi approved a request. It does not replace the official Mi Unlock Tool, bypass account/device restrictions, or infer success from a toast alone.

## Components

### MIBU Android app

The Android app is installed on the phone and owns the phone-side state.

It:

- accepts two explicit user-provided captures:
  - Firefox `new_bbs_serviceToken`
  - Chrome `popRunToken`
- maps those two captures to the four internal timing lanes:
  - lane 1: Firefox, 1400 ms before Beijing midnight
  - lane 2: Chrome, 900 ms before Beijing midnight
  - lane 3: Firefox, 400 ms before Beijing midnight
  - lane 4: Chrome, 100 ms before Beijing midnight
- stores the two capture timestamps independently;
- expires stale captures after 30 minutes;
- refuses to arm when the captures cannot remain fresh until the selected timing window;
- persists one Beijing-midnight target shared by the dashboard, foreground service, Logs and PC status bridge;
- shows one user-facing countdown while keeping lane details in Logs;
- reconciles lane state from persisted wall-clock targets after process recreation;
- runs a foreground service and partial wake lock only for the remaining bounded waiting interval;
- records Community-check and verification state;
- exposes restricted ADB activities protected by `android.permission.DUMP` for:
  - explicit token import;
  - starting the waiting flow;
  - returning state-only proof without exposing token values.

The Android app does **not** currently submit or replay Xiaomi network requests. Its proven responsibility is local timing, freshness enforcement, state persistence and handoff proof.

### MIBU PC Helper v3

The active PC entrypoint is:

```text
pc-helper/qt6/mibu_pc_helper_v3.py
```

The Windows release is a guided four-button workflow:

1. Device Check
2. Install APK
3. Login & Get Tokens
4. Phone Guide / Fastboot Verification

It:

- uses the Android platform-tools bundled inside the release before unrelated system copies;
- requires exactly one authorised online ADB device;
- distinguishes missing, unauthorised, offline and online states;
- verifies Android reports `adb_enabled=1`;
- installs and verifies the bundled APK;
- falls back to the Android/MIUI system installer when silent ADB installation is blocked;
- transfers only the explicit token values entered by the user;
- verifies token import through Android proof markers;
- starts the phone flow, then waits for `WAITING_SERVICE_ARMED` from the foreground service;
- does not treat `WAITING_ACTIVITY_STARTED` as proof that waiting actually armed;
- queries the state-only Android proof bridge before and after waiting;
- refuses fastboot handoff until Android reports the timing stage complete;
- reboots to bootloader, requires exactly one fastboot device and reads available device/unlocked information;
- hands the user to the official Mi Unlock Tool for the authoritative external result.

## State authority

The following state types are intentionally separate:

- **Capture state** — whether both explicit captures are present and fresh.
- **Lane state** — `PENDING`, `ARMED`, `WINDOW_REACHED`, and diagnostic outcomes.
- **Timing verification state** — not started, armed, timing reached, or ready for official verification.
- **Community state** — confirmed, not found, not required, or unknown.
- **Authoritative external result state** — wait time shown, account/device not added, Community authorisation required, or unlocked.

Timing reconciliation must never overwrite an authoritative external result. Starting or restarting the foreground service must also preserve completed and authoritative states.

## Time model

The reference zone is always:

```text
Asia/Shanghai
```

The canonical first visible target is:

```text
23:59:58.600 Beijing time
```

The app persists the target Beijing midnight as an instant. All four lane targets are derived from that same persisted midnight. The UI may display Beijing and device-local forms, but scheduling never relies on manually entered local offsets.

## Visual architecture

### PC UI

The PC helper uses source-controlled SVG artwork rendered deterministically to PNG. Button hitboxes and artwork rectangles share `ui_geometry.py` as their source of truth. Popup close artwork must be fully contained by the shared close hotspot.

### Android UI baseline

The approved Android reference is restored at:

```text
resources/expected ui/android/approved_android_ui_baseline_sheet.svg
```

Its provenance manifest records the exact recovered uploads and SHA-256 values. Both the dedicated baseline workflow and the main build validate this baseline. Complete Windows releases bundle it as review evidence.

## Release composition

A complete Windows release contains:

```text
MIBU-PC-Helper.exe
MIBU.apk
platform-tools/adb.exe
platform-tools/fastboot.exe
platform-tools/AdbWinApi.dll
platform-tools/AdbWinUsbApi.dll
resources/expected ui/pc/*
resources/expected ui/android/approved_android_ui_baseline_sheet.svg
resources/expected ui/android/README.md
```

The build fails rather than producing an incomplete release when required executable, APK, platform-tool, icon, PC hotspot artwork or Android baseline evidence is absent.

## Proof boundary

Static review and CI prove:

- source contracts;
- compilation;
- Android timing calculations;
- token-freshness rules;
- state reconciliation contracts;
- PC parsing and proof-marker handling;
- UI geometry and deterministic rendering;
- release contents.

A physical-device run remains necessary to prove external facts:

- USB authorisation and local driver behaviour;
- MIUI package-installer behaviour;
- foreground-service behaviour on the target phone;
- fastboot detection on the servicing PC;
- the official Mi Unlock Tool result.

Tests confirm the reviewed implementation. They are not a substitute for understanding the architecture first.
