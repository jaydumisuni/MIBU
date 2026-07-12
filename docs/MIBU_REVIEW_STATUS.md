# MIBU Review Status

Review date: 2026-07-12

This review applies the THETECHGUY Build Standard: finish first, review hard, freeze, then prove.

## Current conclusion

The active v2 architecture is now substantially implemented and source-reviewed. The previous one-token shell, static button glow, unverified bridge actions, incomplete release package, and metadata-only lane model have been replaced.

The review is still open. Do not treat this document as permission to pull until the final source and CI pass is explicitly closed.

## Android implementation

### Token model

- Two explicit captures:
  - Firefox `new_bbs_serviceToken`
  - Chrome `popRunToken`
- Firefox maps to slots 1 and 3.
- Chrome maps to slots 2 and 4.
- Each capture has its own timestamp.
- The effective freshness is the shorter remaining freshness of the two captures.
- Each stale capture is removed independently.
- Token fields use password-style input.
- ADB transfer uses URL-safe Base64 extras.
- Android emits proof markers after successful import.

### Timing model

- One visible live countdown.
- Four hidden timing windows:
  - 1400 ms
  - 900 ms
  - 400 ms
  - 100 ms
- All four lanes are derived from one shared upcoming Beijing midnight.
- If the earliest window has passed, every lane rolls to the following midnight together.
- Android unit tests cover mapping, ordering, same-day target, next-day rollover, sub-second values, and China-zone normalisation.
- Start Waiting is rejected when captures cannot remain fresh until the latest timing window.
- Foreground service schedules all four windows, holds a bounded partial wake lock, updates lane state, and records timing-stage completion.

### Android UI and state

- Main dashboard updates every second.
- Main dashboard shows one countdown, not four.
- Detailed lane state stays in Logs.
- Completion wording is `TIMING STAGE COMPLETE`, not request approved.
- Community check records evidence states without inventing a universal requirement.
- Instructions and UI clearly state that MIBU does not prove Xiaomi approval or unlock success.
- ADB bridge activities are protected with the privileged shell `DUMP` permission.

## PC Helper implementation

### Workflow

1. Device Check
2. Install APK
3. Login & Get Tokens
4. Phone Guide / Fastboot Verification

### Action proof

- Device Check distinguishes no device, unauthorized, offline, and online.
- APK install is followed by package verification.
- App launch uses `am start -W` and requires Android confirmation.
- Token push clears logcat, opens the protected import activity, and waits for an Android proof marker.
- Start Waiting clears logcat, opens the protected waiting activity, and waits for an Android proof marker.
- Fastboot verification waits for device detection instead of checking immediately once.
- PC helper records exact command output rather than claiming success from process launch alone.

### Visual contract

- Five required source-controlled SVG screens.
- Five deterministically rendered PNG screens.
- One shared geometry source controls:
  - artwork validation
  - runtime hotspots
  - tests
- Every visible button rectangle must match exactly one runtime hotspot.
- Validator rejects baked orange active styling.
- Orange active glow comes from the button actually clicked.
- Main artwork reserves separate regions for live status, output, target time, and buttons so overlays do not cover instructional text.

## Build and release contract

The complete Windows build now requires and verifies:

- Android unit tests
- Android APK
- PC helper unit tests
- source-contract review
- visual geometry validation
- deterministic PNG rendering
- Qt offscreen construction/math smoke test
- PyInstaller EXE
- bundled MIBU.apk
- bundled ADB and fastboot platform-tools
- all five required UI PNGs

The build fails instead of publishing an incomplete release when any required component is missing or empty.

## CI contract

GitHub Actions is configured to prove:

- THETECHGUY source contracts
- Android unit tests and APK compilation
- Python syntax
- PC unit tests
- SVG/hotspot geometry
- no baked active glow
- deterministic image rendering
- Qt offscreen construction
- Beijing time math
- complete Windows release contents

Current CI completion status must be checked separately. Configuration is not the same thing as a passed workflow.

## Honest remaining boundary

Source review and CI can prove architecture, compilation, math, visual contracts, button wiring, bridge proof logic, and release contents.

Only a physical run can prove external state:

- ATHENA's current USB driver state
- the connected phone accepting RSA authorization
- the installed phone build running on that specific device
- the phone entering fastboot through the cable/driver combination
- Xiaomi/Mi Unlock's live response

These are runtime proof facts, not unfinished design work.

## Review gate

- Intended safe architecture complete: YES
- Two-capture/four-slot model complete: YES
- Consistent timing math implemented and unit-tested: YES
- One-countdown Android presentation: YES
- PC visual/hotspot contract: YES
- Android bridge actions require proof markers: YES
- Self-contained release contract: YES
- Documentation claims match current safe implementation: YES
- GitHub CI configured for full proof: YES
- GitHub CI confirmed green: PENDING
- Physical ATHENA/phone proof: PENDING
- Review frozen: NO — final review still in progress
