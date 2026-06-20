# MIBU Product Flow

## Two-app model

MIBU should be built as two connected tools:

1. Android APK
2. PC Helper / installer

The PC helper is the guided setup tool. The Android APK is the phone-side waiting, status, and timing tool.

## PC helper responsibilities

- Show setup checklist.
- Confirm the phone is ready.
- Check that ADB sees the phone.
- Install or update MIBU.apk.
- Show Beijing target time and local converted time.
- Later: guide user-owned login/session handoff to the phone app.
- Later: provide a proper Windows GUI installer.

## Android app responsibilities

- Receive the prepared user-owned login/session handoff.
- Show account/session status.
- Show Beijing target time.
- Show local converted target time.
- Keep a foreground service active near the timing window.
- Keep logs local to the device.

## Setup checklist shown by PC helper

- Back up the phone first.
- Official HyperOS build only.
- Insert a valid SIM with working mobile data.
- Add Xiaomi account on the phone.
- Add Google account if required by the user's Xiaomi flow.
- Turn off Wi-Fi when the guide requires carrier data.
- Enable Developer Options.
- Enable OEM unlocking.
- Enable USB debugging.
- Confirm ADB authorization prompt on the phone.

## Timing rule

The reference target is Beijing time, Asia/Shanghai.

MIBU should never ask the user to manually calculate timezone offsets. It should show:

- Beijing target time.
- Local target time.
- Remaining countdown.
- Internet/data readiness warning before the target time.

## Safety boundary

MIBU is a guided workflow and timing helper for the user's own account and device. If an official account, device, waiting-period, monthly/yearly, or rate-limit message appears, MIBU should show the message and tell the user the next safe retry path.
