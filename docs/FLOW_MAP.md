# MIBU Flow Map

This file explains how the reviewed PC helper and Android app fit together.

## Product split

MIBU has two cooperating apps:

### MIBU PC Helper

Runs on Windows and owns the guided four-step workflow:

1. Device Check
2. Install APK
3. Login & Get Tokens
4. Phone Guide / Fastboot Verification

### MIBU Android App

Runs on the phone and owns:

- explicit token import
- token freshness state
- one live Beijing countdown
- four hidden timing-window states
- Community evidence state
- Logs and Instructions

The Android app stops running when the phone enters fastboot. PC Helper owns the fastboot handoff.

## Exact user flow

```text
1. Device Check
   PC Helper checks ADB.
   Result is one of:
   - no device
   - unauthorized / RSA prompt required
   - offline
   - online and authorized

2. Install APK
   PC Helper installs the bundled MIBU.apk.
   It then verifies the Android package exists and opens MainActivity.

3. Login & Get Tokens
   User logs in themselves in normal browsers.
   User obtains two captures only:
   - Firefox new_bbs_serviceToken
   - Chrome popRunToken

   PC Helper transfers them through URL-safe Base64 extras.
   Android emits an explicit proof marker after saving both captures.

4. Android preparation
   Android shows:
   - token freshness
   - Beijing target time
   - local converted time
   - one live countdown
   - mobile-data / Wi-Fi reminder
   - Community check state

5. Start Waiting
   Android refuses to arm when:
   - either capture is missing
   - either capture is stale
   - the next timing window is farther away than the remaining freshness

   When valid, Android schedules four hidden timing windows around one Beijing midnight:
   - lane 1: 1400 ms before midnight
   - lane 2: 900 ms before midnight
   - lane 3: 400 ms before midnight
   - lane 4: 100 ms before midnight

   PC Helper treats Start Waiting as successful only after Android emits its proof marker.

6. Timing stage complete
   Android records each lane as WINDOW_REACHED.
   After all four, Android shows:
   - TIMING STAGE COMPLETE
   - Continue with PC verification

   This does not mean Xiaomi approved an unlock request.

7. Fastboot verification
   PC Helper:
   - sends adb reboot bootloader
   - waits for fastboot detection
   - reads available device/unlocked information
   - hands the user to the official Mi Unlock Tool

8. Result interpretation
   - Mi Unlock shows a wait time: accepted far enough to continue later
   - account/device not added: use Mi Unlock Status binding fallback
   - Community/authorisation required: account/device remains gated
   - unlocked/already unlocked: success
   - unclear response: record UNKNOWN, never invent success
```

## Token mapping

```text
Firefox capture -> slots 1 and 3
Chrome capture  -> slots 2 and 4
```

The user does not perform four logins.

## Visual rule

The PC helper is one image-hotspot application with four main actions and four matching popup screens. The orange outline is applied dynamically to the button the user clicks; it is not baked into the artwork.

The Android dashboard shows one countdown. Individual timing-window detail belongs in Logs, not on the main screen.

## Claim boundary

MIBU can prove:

- device/ADB state
- APK installation and launch
- explicit token import
- token freshness
- timing-window scheduling and completion
- fastboot detection

MIBU cannot by itself prove Xiaomi request approval, account/device binding, or bootloader unlock. The official Mi Unlock Tool remains the authoritative final verifier.
