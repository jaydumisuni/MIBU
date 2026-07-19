# MIBU

**MIBU = Mi Bootloader Unlock Helper**  
**Product family:** THETECHGUY TOOL  
**Footer:** By the THETECHGUY TOOL team

MIBU is a two-part timing, state-proof and official-tool handoff assistant for Xiaomi devices the user owns or is authorised to service.

MIBU does **not** send or replay Xiaomi request traffic in the current implementation. It does **not** claim that reaching a timing window means Xiaomi approved an unlock request. The official Mi Unlock Tool remains authoritative.

## Android app — `0.2.0-dev`

The Android app:

- accepts exactly two explicit user-provided captures:
  - Firefox `new_bbs_serviceToken`
  - Chrome `popRunToken`
- maps them internally to four timing lanes:
  - lane 1: Firefox, 1400 ms before Beijing midnight
  - lane 2: Chrome, 900 ms before Beijing midnight
  - lane 3: Firefox, 400 ms before Beijing midnight
  - lane 4: Chrome, 100 ms before Beijing midnight
- validates capture length and rejects control characters;
- limits each capture to 8192 characters;
- tracks the two capture timestamps independently;
- expires each capture after 30 minutes;
- fails closed if the phone clock moves backwards rather than extending token lifetime;
- refuses to arm if the captures cannot remain fresh until the final lane;
- persists one Beijing-midnight target for the dashboard, foreground service, Logs and PC proof bridge;
- shows one user-facing countdown while keeping four-lane detail in Logs;
- reconciles reached lanes after Android process recreation;
- resumes an already-armed wait without resetting completed lanes;
- enters foreground immediately on every foreground-service start path;
- uses a bounded partial wake lock only for the remaining waiting interval;
- requests notification permission on Android 13+ so the foreground state can remain visible;
- preserves timing completion and every recorded official result;
- lets the user record only results actually shown by the official route:
  - official wait time shown;
  - account/device not added;
  - Xiaomi Community authorisation required;
  - device unlocked;
- provides an explicit confirmed reset for a fresh authorised workflow;
- exposes DUMP-protected ADB activities for import, waiting and state-only proof;
- never returns token values through its status proof.

## PC Helper v3

The active helper is:

```text
pc-helper/qt6/mibu_pc_helper_v3.py
```

Its compact live four-control workflow is:

1. Device Check
2. Install APK
3. Login & Get Tokens
4. Phone Guide / Fastboot Verification

The helper:

- uses a frameless `760 x 560` window with custom minimize, maximize and close controls;
- renders real Qt controls and status text rather than placing click regions over screenshots;
- includes a floating MIBU assistant with One-Click Assist, local command chat and an illustrated offline manual;
- detects or installs Firefox and Chrome and keeps the explicit session handoff inside the UI;
- prioritises platform-tools bundled with the release;
- requires exactly one normal online ADB device;
- distinguishes missing, unauthorised, offline and unsupported ADB states;
- verifies Android reports `adb_enabled=1`;
- requires Android app version `0.2.0-dev`;
- updates an older installed MIBU version instead of treating any installed package as current;
- verifies the installed version after ADB installation;
- falls back to the Android/MIUI system installer when silent installation is blocked;
- rejects malformed or oversized captures before transfer;
- transfers captures with URL-safe Base64 extras;
- gives every import, status and service-proof request a random correlation nonce;
- never clears the phone's whole logcat merely to establish proof;
- ignores stale proof lines carrying a different nonce;
- treats `WAITING_ACTIVITY_STARTED` as activity-launch evidence only;
- reports waiting success only after the foreground service emits:
  - `WAITING_SERVICE_ARMED`, or
  - a correlated completed-state marker when the timing stage races ahead;
- accepts early, correlated rejection markers instead of timing out ambiguously;
- refuses fastboot handoff until Android reports timing completion;
- parses only real fastboot-device rows and rejects multiple-device ambiguity;
- provides a read-only HyperOS/Settings build report before any legacy binding-recovery method is considered;
- reboots to bootloader, checks available device/unlocked information and hands off to the official Mi Unlock Tool.

## Guardrails

MIBU must not:

- ask for the Xiaomi account password;
- silently read unrelated browser data;
- expose token values through logs or the status bridge;
- claim success from a Settings toast, a timing marker or fastboot presence alone;
- bypass ownership checks, device locks, waiting periods, rate limits or official restrictions;
- automatically retry or spam official endpoints.

For China-routed or Community-routed devices, Community status is saved as manual evidence. It is not converted into an invented pass/fail result.

## Two captures, not four logins

```text
Firefox login/capture -> new_bbs_serviceToken -> lanes 1 and 3
Chrome login/capture  -> popRunToken           -> lanes 2 and 4
```

The user obtains each capture once. MIBU reuses those two values across the four local timing lanes.

## Complete Windows build

From the repository root:

```powershell
.\pc-helper\build_windows.ps1
```

The build script:

1. locates Python, Gradle and the Android SDK;
2. runs Android lint, unit tests and APK assembly when an APK must be built;
3. runs the THETECHGUY source-contract review;
4. validates the restored Android expected-UI baseline;
5. generates deterministic reusable assets from the approved MIBU logo and references;
6. validates the compact live UI, assistant, dialogs, manual and branded application icons;
7. discovers and runs every PC helper unit test;
8. performs an offscreen v3 import/version proof check;
9. removes or safely renames stale locked build/release folders;
10. creates a clean PyInstaller build;
11. bundles the APK, ADB, fastboot, Windows platform-tool DLLs, live UI assets and offline guide;
12. writes `SHA256SUMS.txt` for the protected release files;
13. fails rather than publishing a partial release.

Complete release contract:

```text
pc-helper/release/MIBU-PC-Helper/
├── MIBU-PC-Helper.exe
├── SHA256SUMS.txt
├── dist/
│   └── MIBU.apk
├── platform-tools/
│   ├── adb.exe
│   ├── fastboot.exe
│   ├── AdbWinApi.dll
│   └── AdbWinUsbApi.dll
└── resources/
    ├── logo.png
    ├── guide/index.html
    ├── live_ui/
    │   ├── mibu_logo.png
    │   ├── mibu_hood.png
    │   ├── mibu_app_icon.ico
    │   ├── firefox.png
    │   └── chrome.png
    └── expected ui/android/
        ├── approved_android_ui_baseline_sheet.svg
        └── README.md
```

The brand audio files remain optional. The build does not fabricate replacements when the approved audio is absent.

## Source runs

Android:

```powershell
gradle :android:app:lintDebug :android:app:testDebugUnitTest :android:app:assembleDebug
```

PC Helper:

```powershell
python tools\extract_live_ui_assets.py
cd pc-helper\qt6
python -m unittest discover -v
python mibu_pc_helper_v3.py
```

## CI proof

GitHub Actions is defined to check:

- the THETECHGUY source contract;
- the five-state restored Android UI baseline and provenance manifest;
- Android lint, timing/freshness/state unit tests and APK compilation;
- Python syntax and complete unittest discovery;
- nonce-correlated proof handling;
- version-aware APK update behaviour;
- ADB and fastboot parsing;
- live dialog close and custom window-control wiring;
- deterministic approved-logo PNG/ICO extraction;
- offscreen compact Qt construction and assistant-state sizing;
- complete Windows release contents and checksum manifest.

## Proof boundary

Static review and CI can prove source structure, compilation, time math, freshness rules, state transitions, proof correlation, UI geometry, button wiring and release composition.

A physical-device run is still required to prove external facts such as USB authorisation, local drivers, MIUI installer behaviour, foreground-service behaviour on the target ROM, fastboot detection on the servicing PC and the official Mi Unlock Tool result.
