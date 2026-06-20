# MIBU Flow Map

This file explains how the PC helper screens and Android app screens fit together.

## Important correction

The mockups are not all meant to be shown at the same time. They are different states of the same workflow.

## App pieces

MIBU has two apps:

1. **MIBU PC Helper**
   - Runs on Windows.
   - Prepares the phone.
   - Opens the Xiaomi login page in the normal browser.
   - Checks ADB.
   - Installs MIBU.apk.
   - Opens MIBU on the phone.
   - Shows timing guidance.

2. **MIBU Android App**
   - Runs on the phone.
   - Receives/imports the user-approved session/token.
   - Shows countdown, timing, logs, and guide.
   - Starts the foreground waiting service.

## Correct screen order

```text
PC Helper Screen 1: Welcome / checklist
  -> user connects phone
  -> user enables USB debugging / approves ADB
  -> helper checks device

PC Helper Screen 2: Ready / status
  -> shows connected device
  -> shows ADB authorized
  -> installs MIBU.apk
  -> opens MIBU on the phone
  -> user opens browser login and obtains/approves session/token

Android Screen 1: Welcome / import
  -> user imports session/token from PC/manual flow
  -> phone app saves session locally

Android Screen 2: Dashboard / waiting
  -> shows account/session status
  -> shows Beijing target time
  -> shows local target time
  -> shows countdown
  -> starts foreground waiting service
  -> logs actions and shows instructions
```

## What each mockup means

### PC compact wizard mockup

This is the first screen of the Windows helper. It should not be a huge full control panel. It is only the setup wizard.

### PC ready/status mockup

This is the second screen after device connection and install actions. It should show connected device, ADB authorized, APK install, session ready, timing, and final actions.

### Android welcome/import mockup

This is what the phone shows before the session/token is imported.

### Android dashboard/waiting mockup

This is what the phone shows after a session/token is imported and the app is ready to wait for the target time.

## Simplified user flow

```text
1. Open MIBU PC Helper.
2. Connect phone with USB debugging enabled.
3. PC Helper checks ADB.
4. PC Helper installs MIBU.apk.
5. PC Helper opens MIBU on phone.
6. User logs into Xiaomi in normal browser.
7. User imports/approves token/session.
8. Phone app shows dashboard and countdown.
9. User starts waiting service.
10. At the target time, user follows the official next step shown by MIBU.
```

## Design rule

Do not mix all mockup elements into one screen. The PC helper has its own two states, and the Android app has its own two states.
