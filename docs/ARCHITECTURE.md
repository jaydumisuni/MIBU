# MIBU Architecture

## Target product

MIBU has two apps:

```text
MIBU Android app
- Installed on the phone.
- Shows account/session status.
- Receives a user-owned prepared login package from PC helper or future in-app WebView login.
- Converts Beijing time to local time automatically.
- Runs a foreground service near the selected timing window.
- Saves local logs.

MIBU PC Helper
- Runs on Windows/macOS/Linux where ADB is available.
- Installs MIBU.apk after the phone has ADB enabled.
- Guides the user through the correct timing window.
- Later: prepares a secure handoff package for the Android app.
```

## Recommended flow

1. User enables ADB on the Xiaomi/Redmi phone.
2. PC Helper checks `adb devices`.
3. PC Helper installs MIBU.apk.
4. PC Helper guides user-owned login/session preparation.
5. Android app receives the handoff, verifies it, and shows status.
6. Android app displays Beijing target time and local converted time.
7. Android app runs a foreground service near the timing window.

## Time-zone rule

The reference timezone is always **Asia/Shanghai / Beijing time**.

MIBU should store all schedule calculations internally as instants, then display:

- Beijing target time.
- Device-local target time.
- Remaining countdown.

This means a user in Zambia, South Africa, Europe, India, or the US does not need to manually calculate the offset.

## Missing pieces to implement later

- Secure Android import screen.
- PC-to-phone secure handoff channel.
- Android WebView login fallback.
- Account status checker.
- Logs export.
- App icon and ghost hero assets.

## Safety rule

MIBU should be strict about account/device restrictions. It should help with timing and workflow only. It should not spam attempts or bypass official restrictions.
