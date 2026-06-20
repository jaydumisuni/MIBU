# MIBU

**MIBU = Mi Bootloader Unlock Helper**  
**Product family:** THETECHGUY TOOL  
**Footer:** By the THETECHGUY TOOL team

MIBU is a two-part helper:

1. **MIBU Android app (`MIBU.apk`)**
   - Runs on the Android phone.
   - Lets the user explicitly import their own token/session.
   - Shows session status, Beijing target time, local converted time, countdown, reminders, logs, and instructions.
   - Runs a foreground service so the phone can stay awake/data-on near the request window.

2. **MIBU PC Helper**
   - Opens the normal browser login page so the user logs in themselves.
   - Checks dependencies and ADB availability.
   - Installs `MIBU.apk` to the phone once ADB is enabled.
   - Opens MIBU on the phone.
   - Shows Beijing target time and local converted time automatically.

## Guardrails

MIBU is a timing, workflow, and installation helper for legitimate Xiaomi bootloader unlock requests using the user's own Xiaomi account/device. It must not ask for the Xiaomi password, silently read unrelated browser data, bypass Xiaomi ownership checks, device locks, waiting periods, rate limits, or other official restrictions.

If Xiaomi reports a daily limit, account restriction, expired login, not-eligible state, or waiting period, MIBU should explain the result and tell the user the next safe retry path instead of spamming requests.

## User-owned token flow

```text
PC Helper opens normal browser login
  -> User logs in themselves
  -> User obtains/approves the needed token/session value
  -> User imports token/session explicitly into MIBU.apk
  -> MIBU stores it locally and shows only a masked/length preview
  -> MIBU handles timing, countdown, reminders, logs, and guide
```

## Monorepo layout

```text
android/      MIBU Android APK source
pc-helper/   PC helper CLI, Qt6 UI, dependency checker, packaging script
docs/        architecture, branding, UI baseline, token/login flow notes
.github/     CI build/test workflows
```

## Android build

```powershell
gradle :android:app:assembleDebug
```

Debug APK output:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## PC helper local run

```powershell
cd MIBU
python -m venv .venv
.\.venv\Scripts\activate
pip install -r pc-helper\qt6\requirements.txt
python pc-helper\qt6\mibu_pc_helper_final.py
```

## PC helper dependency check

```powershell
python pc-helper\qt6\dependency_check.py
```

Checks:

```text
Python 3.10+
PySide6 / Qt6
ADB platform-tools
```

## Windows helper packaging

Build Android first, then package the PC helper:

```powershell
.\pc-helper\build_windows.ps1
```

The script packages the Qt6 helper and tries to bundle the debug APK as:

```text
pc-helper/qt6/dist/MIBU.apk
```

## V1 source readiness

The v1 source baseline includes:

- Android dashboard UI
- Android token/session import screen
- Android logs and instructions screens
- Foreground service shell
- Pullable MIBU launcher and hero drawable assets
- Beijing/local time conversion
- PC CLI helper
- Final Qt6 helper UI with dependency panel
- Browser login button
- ADB device check
- APK install flow
- Open app flow
- CI syntax/build checks

Final confirmation still requires a real build and real device run.
