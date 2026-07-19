# MIBU Architecture

## Product boundary

MIBU is a two-part **timing, state-proof and official-tool handoff assistant** for a Xiaomi device the user owns or is authorised to service.

It does not claim that reaching a timing window means Xiaomi approved a request. It does not replace the official Mi Unlock Tool, bypass account/device restrictions, infer success from a toast, or currently submit/replay Xiaomi network requests.

## Android component

The Android app owns phone-side workflow state.

It accepts two explicit captures:

- Firefox `new_bbs_serviceToken` → lanes 1 and 3;
- Chrome `popRunToken` → lanes 2 and 4.

The four local timing targets are:

| Lane | Source | Offset from Beijing midnight |
|---|---|---:|
| 1 | Firefox | 1400 ms before |
| 2 | Chrome | 900 ms before |
| 3 | Firefox | 400 ms before |
| 4 | Chrome | 100 ms before |

The app:

- validates capture shape and bounds each value to 8192 characters;
- stores capture timestamps independently;
- expires captures after 30 minutes;
- fails closed when wall-clock rollback would otherwise extend freshness;
- refuses a wait that outlives the least-fresh capture;
- persists one Beijing-midnight instant as the source for all four lanes;
- reconciles lane state from persisted targets after process recreation;
- resumes an armed workflow without resetting reached lanes;
- must start foreground immediately on every service path, including rejection and completed-state recovery;
- uses a bounded partial wake lock for only the remaining waiting interval;
- requests visible-notification permission on Android 13+;
- keeps one clean dashboard countdown while Logs retain lane detail;
- records Community evidence separately from timing and official-result state;
- permits explicit recording of only an official result actually observed by the user;
- offers a confirmed workflow reset that clears tokens, target, lanes and verification result while retaining Community evidence.

The app exposes three `android.permission.DUMP`-protected activities for ADB:

1. token import;
2. waiting start/resume;
3. state-only proof.

Those activities never return token values in logs or status output.

## PC Helper v3

The active entrypoint is:

```text
pc-helper/qt6/mibu_pc_helper_v3.py
```

The live four-control workflow is:

1. Device Check
2. Install APK
3. Login & Get Tokens
4. Phone Guide / Fastboot Verification

The PC helper:

- prioritises bundled Android platform-tools;
- requires exactly one normal online ADB device;
- verifies `adb_enabled=1`;
- requires Android app version `0.2.0-dev`;
- updates an older installed package and verifies the resulting `versionName`;
- falls back to the phone's package installer if silent ADB installation is blocked;
- validates capture size and control characters before transfer;
- uses URL-safe Base64 for transfer extras;
- generates a random correlation nonce for every import, status and waiting proof;
- filters Android proof by nonce rather than clearing the device's complete logcat;
- rejects stale markers from previous operations;
- treats activity launch as launch evidence only;
- accepts waiting only after a correlated service marker proves armed or already complete;
- parses only valid fastboot-device rows and rejects multiple-device ambiguity;
- refuses fastboot handoff until Android's state-only proof reports timing completion;
- hands the authoritative decision to the official Mi Unlock Tool.

## State authority

The following state domains remain separate:

- **Capture state** — whether both captures are present and fresh.
- **Lane state** — `PENDING`, `ARMED`, `WINDOW_REACHED`, plus diagnostic outcomes.
- **Timing state** — not started, armed, timing reached, or ready for official verification.
- **Community state** — confirmed, not found, not required, or unknown.
- **Official-result state** — wait time shown, account/device not added, Community authorisation required, or unlocked.

`VerificationStateRules.kt` is the shared authority for:

- what counts as timing complete;
- what counts as an authoritative official result;
- what blocks a new waiting cycle.

Timing reconciliation and service failure handling must never overwrite a completed timing state or official result.

## Time model

The reference zone is always:

```text
Asia/Shanghai
```

The first visible lane targets:

```text
23:59:58.600 Beijing time
```

All four targets derive from one persisted Beijing-midnight instant. Local display conversion never changes scheduling math.

## Proof correlation

ADB log proof is non-destructive and operation-specific:

```text
PC generates nonce
  -> passes nonce to DUMP-protected activity
  -> Android includes nonce in marker
  -> PC accepts only matching marker
```

This prevents an old successful log line from proving a new operation and avoids deleting unrelated device logs.

## Visual architecture

### PC UI

Approved raster references are converted into reusable logo, character and icon assets. Qt and Android render real controls and dynamic text around those assets; popup close controls are real buttons, not image hotspots.

### Android UI baseline

The restored approved reference is:

```text
resources/expected ui/android/approved_android_ui_baseline_sheet.svg
```

Its manifest records the recovered source uploads and SHA-256 values. The dedicated baseline workflow, main build and Windows release all enforce its presence.

## Release composition and integrity

A complete Windows release contains:

```text
MIBU-PC-Helper.exe
SHA256SUMS.txt
dist/MIBU.apk
platform-tools/adb.exe
platform-tools/fastboot.exe
platform-tools/AdbWinApi.dll
platform-tools/AdbWinUsbApi.dll
resources/expected ui/pc/*
resources/expected ui/android/approved_android_ui_baseline_sheet.svg
resources/expected ui/android/README.md
```

The build performs source review, Android-baseline validation, live-asset generation, all discovered PC tests and a clean PyInstaller build. It then hashes the protected release files. A missing APK, tool, UI asset or checksum manifest is a build failure.

Approved audio remains optional; absent audio is reported rather than fabricated.

## Proof boundary

Static review and CI are designed to prove:

- source and documentation contracts;
- Android lint, compilation and unit tests;
- timing and freshness math;
- state authority and idempotent resume rules;
- nonce-correlated proof handling;
- version-aware installation;
- ADB/fastboot parsing;
- compact live-widget construction, dialog controls and deterministic branded assets;
- release composition and SHA-256 manifest generation.

A physical-device run remains necessary to prove external facts:

- USB authorisation and local driver behaviour;
- MIUI package-installer behaviour;
- foreground-service behaviour on the target ROM;
- fastboot detection on the servicing PC;
- Xiaomi server behaviour and the official Mi Unlock Tool result.

Tests confirm reviewed engineering. They do not replace understanding the implementation first.
