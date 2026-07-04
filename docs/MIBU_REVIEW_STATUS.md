# MIBU Review Status

Review date: 2026-07-05

This review applies the THETECHGUY Build Standard: finish first, review hard, freeze, then prove.

## Current conclusion

MIBU is not ready to be claimed as fully working yet.

The current repo has a working shell and useful PC/APK wiring, but the implementation does not yet match the confirmed product plan.

## What is present

### Android APK

- MainActivity renders the current phone UI in native Android views.
- MainActivity shows one Beijing target countdown at 23:59:58.600.
- TokenStore stores one imported session string.
- StartWaitingActivity starts MibuForegroundService when a session exists.
- MibuForegroundService runs as a foreground service and stops cleanly if no session exists.

### PC Helper

- PC helper has four main workflow actions:
  - Device Check
  - Install APK
  - Login & Get Token
  - Phone Guide
- PC helper checks ADB device state and distinguishes no device, unauthorized, offline, and online states.
- PC helper can install an APK, launch MIBU, push one token/session, and start phone waiting.
- PC helper supports image-hotspot UI with fallback controls when resources are missing.
- PC helper sets the window maximize button hint and minimum size.

## Gaps against confirmed plan

### Android APK gaps

- TokenStore supports only one `session` string, not two token captures.
- There is no model for:
  - Firefox service token capture
  - Chrome pop token capture
  - four derived token slots
  - lane offsets 1400 / 900 / 400 / 100 ms
  - lane statuses
  - request result statuses
  - community device check statuses
  - verification states
- StartWaitingActivity only starts the foreground service; it does not arm a lane queue.
- MibuForegroundService only stays alive; it does not manage countdown execution, lane state, or result recording.
- The app still shows the simplified session dashboard, not the full account/precheck/waiting/verification state machine.

### PC Helper gaps

- PC helper currently pushes only one token/session value.
- It does not have a two-token capture/import model.
- It does not populate four lane slots.
- It does not have a fastboot verification action yet.
- It does not record Mi Unlock Tool result states.
- Settings fallback is not yet implemented as a formal post-verification branch.

### UI/resource gaps

- Expected UI image resources are optional/fallback-aware, but the actual expected images are not guaranteed to be present in repo.
- Popup screens can function without images, but image-based UI fidelity cannot be proven from repo alone.

## Required implementation before runtime proof

### Android

1. Add `MibuStateStore.kt` or equivalent.
2. Add model types for:
   - token captures
   - token slots
   - time-shift lanes
   - precheck states
   - community states
   - request results
   - verification states
3. Upgrade TokenStore from one session string to two captures mapped into four slots.
4. Upgrade Start Waiting to arm the confirmed hidden lane queue while the UI shows one countdown.
5. Add logs/result screen for request and verification status.
6. Keep concise disclaimer in onboarding/about/instructions only.

### PC Helper

1. Add two-token import/push flow.
2. Push both token captures to the APK.
3. Add fastboot verification guide:
   - check ADB online
   - reboot bootloader
   - detect fastboot device
   - guide Mi Unlock Tool
   - record result state
4. Treat Settings Mi Unlock Status as fallback only if Mi Unlock reports account/device not added.
5. Keep ADB/RSA checks intact.

## Review gate status

- Implementation complete: NO
- Code/docs match: PARTIAL
- Known gaps documented: YES
- Clean build proof: NOT DONE IN THIS REVIEW
- Runtime proof: NOT DONE IN THIS REVIEW
- Ready to claim working: NO

## Next safe patch target

Build the state model and safe UI/control flow first:

- state store
- two-token capture slots
- four hidden lane metadata
- one visible countdown
- fastboot verification guide states
- honest result statuses

Do not claim timed request automation, token capture, or unlock success until implementation and proof exist.
