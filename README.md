# MIBU

**MIBU = Mi Bootloader Unlock Helper**  
**Product family:** THETECHGUY TOOL  
**Footer:** By the THETECHGUY TOOL team

MIBU is a two-part timing and verification assistant.

## 1. MIBU Android app

The Android app:

- accepts two explicit user-provided captures:
  - Firefox `new_bbs_serviceToken`
  - Chrome `popRunToken`
- maps them internally to four slots:
  - slot 1 Firefox
  - slot 2 Chrome
  - slot 3 Firefox
  - slot 4 Chrome
- tracks the two capture timestamps independently
- expires each locally stored capture after 30 minutes
- prevents waiting from being armed when either capture cannot remain fresh until the selected Beijing timing window
- persists the target Beijing midnight so the countdown, foreground service, logs and PC proof bridge use one schedule
- shows one live countdown instead of four noisy countdowns
- tracks the four confirmed timing offsets in the foreground service:
  - 1400 ms
  - 900 ms
  - 400 ms
  - 100 ms
- reconciles timing state from persisted wall-clock targets if the Android process is recreated
- records when each timing window is reached
- stores Community-check and verification state
- exposes detailed lane state through Logs
- exposes a restricted ADB status bridge that returns state only, never token values

MIBU does **not** claim request approval, account/device binding, or unlock success by itself.

## 2. MIBU PC Helper

The PC helper provides the guided four-step workflow:

1. Device Check
2. Install APK
3. Login & Get Tokens
4. Phone Guide / Fastboot Verification

It:

- uses the platform-tools bundled inside the release before any unrelated system ADB installation
- rejects ambiguous multiple-device ADB or fastboot states
- distinguishes no device, unauthorized, offline, and online ADB states
- requires Android to report `adb_enabled=1`
- installs and verifies the bundled APK
- falls back to copying the APK and opening the Android/MIUI system installer when silent ADB install is blocked
- transfers one legacy service capture or the preferred two-token capture using URL-safe Base64 extras
- confirms token import through an Android log proof marker
- starts the phone waiting activity through the restricted ADB bridge
- queries the restricted Android state bridge before and after waiting
- refuses fastboot handoff until Android reports the timing stage complete
- reboots the phone to bootloader
- waits for exactly one fastboot device
- reads available fastboot device/unlocked information
- hands the user to the official Mi Unlock Tool for the authoritative result

## Guardrails

MIBU is for legitimate servicing of a device the user owns or is authorised to service.

It must not:

- ask for the Xiaomi account password
- silently read unrelated browser data
- expose token values through the status bridge or logs
- claim success from a Settings toast alone
- bypass ownership checks, device locks, waiting periods, rate limits, or official restrictions
- claim that reaching the timing window means Xiaomi approved the request

If Xiaomi or Mi Unlock reports a restriction, waiting period, account/device-not-added state, or Community requirement, MIBU records and explains that result rather than inventing success.

## User-owned token flow

```text
Firefox login/capture -> new_bbs_serviceToken -> slots 1 and 3
Chrome login/capture  -> popRunToken           -> slots 2 and 4

Two captures only. No four-login flow.
```

The captures can be imported manually in the Android app or pushed from PC Helper after the user obtains them themselves.

## Monorepo layout

```text
android/      Android APK source and unit tests
pc-helper/    PC helper actions, proof-gated Qt UI, visual renderer, packaging
resources/    Source-controlled SVG artwork, icon and rendered hotspot assets
tools/        THETECHGUY source-contract reviewer
docs/         architecture, review status, flow and build standards
.github/      Android, PC, visual-contract and Windows release CI
```

## Complete Windows build

From the repository root:

```powershell
.\pc-helper\build_windows.ps1
```

The build script:

1. locates Python
2. locates the Android SDK and Gradle when an APK must be built
3. runs Android unit tests and creates the debug APK when needed
4. verifies Android platform-tools for a self-contained release
5. validates SVG button geometry against the shared hotspot contract
6. renders the five required PNG screens plus branded PNG/ICO application icons
7. runs PC helper unit tests
8. performs an offscreen proof-gated v3 import smoke check
9. builds `mibu_pc_helper_v3.py` with the branded Windows icon
10. bundles and verifies the EXE, APK, platform-tools, resources, icon and required UI images

Complete release output:

```text
pc-helper/release/MIBU-PC-Helper/
├── MIBU-PC-Helper.exe
├── dist/
│   └── MIBU.apk
├── platform-tools/
│   ├── adb.exe
│   ├── fastboot.exe
│   ├── AdbWinApi.dll
│   └── AdbWinUsbApi.dll
└── resources/expected ui/pc/
    ├── 01_pc_main_four_button_workflow.png
    ├── 02_popup_device_check_guide.png
    ├── 03_popup_install_apk.png
    ├── 04_popup_login_get_token.png
    ├── 05_popup_phone_guide.png
    ├── mibu_app_icon.png
    └── mibu_app_icon.ico
```

The build fails instead of producing an incomplete release when the APK, platform-tools, application icon, or required hotspot artwork is missing.

## Android-only build

```powershell
gradle :android:app:testDebugUnitTest :android:app:assembleDebug
```

Output:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## PC helper source run

Render the required images and icon first, then run the proof-gated v3 helper:

```powershell
python pc-helper\qt6\validate_ui_contract.py
python pc-helper\qt6\render_svg_assets.py
python pc-helper\qt6\mibu_pc_helper_v3.py
```

## CI proof

GitHub Actions checks:

- THETECHGUY source contracts
- Android timing unit tests
- Android APK compilation
- Python syntax for active helper modules
- PC device/status/timing/geometry unit tests
- one shared source of truth for visual and hotspot geometry
- SVG-to-PNG rendering and PNG-to-ICO branding generation
- Qt offscreen v3 construction and application icon loading
- Beijing target-time math
- complete Windows release packaging
- non-empty EXE, APK, platform-tools, icon and required UI assets

## Proof boundary

Source review and CI can prove architecture, compilation, timing math, visual contracts, button wiring, status gating and release contents.

A physical device run remains the final proof for external facts such as USB authorization, driver state, the connected phone's fastboot response, and the official Mi Unlock Tool result.
