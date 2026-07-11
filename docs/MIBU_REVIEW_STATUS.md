# MIBU Review Status

Review date: 2026-07-05

This review applies the THETECHGUY Build Standard: finish first, review hard, freeze, then prove.

## Current conclusion

MIBU has moved past the old one-token visual shell.

The repo now contains the safe state/control-flow layer needed before runtime proof:

- two token captures
- four derived internal request slots
- lane metadata for 1400 / 900 / 400 / 100 ms
- one visible countdown on Android
- waiting service that arms lane state
- Android Community Device Check screen
- Android Logs screen showing real stored token/slot/lane/community/verification state
- shared Android UI helper functions restored for all simple activity screens
- compile-safe Android hero artwork resource present
- PC helper two-token push
- PC helper fastboot verification guide
- PC helper build script that handles locked release folders by renaming them instead of failing immediately

This still must be clean-built and runtime-tested on the user's PC/phone before it can be claimed as fully proven.

## What is present

### Android APK

- MainActivity renders a phone dashboard with one visible countdown and state cards for token setup, hidden request lanes, community check, and verification.
- TokenStore supports two captures:
  - Firefox/service token
  - Chrome/pop token
- TokenStore maps those captures into four slots:
  - Slot 1 Firefox
  - Slot 2 Chrome
  - Slot 3 Firefox
  - Slot 4 Chrome
- MibuLane models the four lane offsets:
  - 1400 ms
  - 900 ms
  - 400 ms
  - 100 ms
- MibuStateStore tracks lane state, community state, and verification state.
- TokenImportActivity accepts either:
  - two pushed tokens from PC Helper
  - one legacy token/session
  - manual two-token paste
- StartWaitingActivity arms lane state before starting the foreground service.
- MibuForegroundService logs and notifies that waiting is armed.
- CommunityCheckActivity lets the user set:
  - COMMUNITY_DEVICE_CONFIRMED
  - COMMUNITY_DEVICE_NOT_FOUND
  - COMMUNITY_ROUTE_NOT_REQUIRED
  - COMMUNITY_ROUTE_UNKNOWN
- LogsActivity displays current stored token preview, four-slot status, lane state, community state, and verification state.
- MibuUiHelpers provides shared `mibuPage`, `mibuCard`, `mibuButton`, `footer`, `dp`, and `rounded` helpers used by TokenImportActivity, LogsActivity, InstructionsActivity, and CommunityCheckActivity.
- AndroidManifest registers CommunityCheckActivity, TokenImportActivity, StartWaitingActivity, LogsActivity, InstructionsActivity, MainActivity, and MibuForegroundService.
- Drawable resources include `ic_mibu` and `mibu_hero_art`, so MainActivity's hero image reference has a repo resource behind it.

### PC Helper

- PC helper has four main workflow actions:
  - Device Check
  - Install APK
  - Login & Get Token
  - Phone Guide
- PC helper checks ADB device state and distinguishes no device, unauthorized, offline, and online states.
- PC helper can install an APK, launch MIBU, push one token/session, push two token captures, and start phone waiting.
- PC helper includes fastboot verification helpers:
  - reboot to bootloader
  - detect fastboot devices
  - query fastboot device info / unlocked state
- Phone Guide has a Verify Fastboot path that hands off to official Mi Unlock Tool result interpretation.
- PC helper supports image-hotspot UI with fallback controls when resources are missing.
- PC helper sets the window maximize button hint and minimum size.
- Build script copies APK/resources/audio when present and handles locked release folders by renaming old folders.

## Remaining gaps before runtime proof

### Android APK

- The lane request execution engine is intentionally not implemented in this safe patch.
- Real endpoint/result handling must not be claimed until a permitted implementation and test exist.

### PC Helper

- Fastboot verification opens the correct technical path, but official Mi Unlock Tool result is still recorded by user interpretation, not automatic OCR/API.
- Settings fallback is documented and guided, but not yet a separate wizard screen.
- Image UI fidelity still depends on expected image resources being present in the local resource folder.

### Build/runtime proof

- Clean build proof has not been run inside this GitHub-only review.
- Runtime proof on the connected phone has not been run inside this GitHub-only review.
- Final confidence requires the user's PC to pull, build, install, and run the APK/PC helper.

## Review gate status

- Implementation complete for safe state/control-flow layer: YES
- Code/docs match for safe layer: YES
- Known gaps documented: YES
- Clean build proof: NOT DONE IN THIS REVIEW
- Runtime proof: NOT DONE IN THIS REVIEW
- Ready to claim fully working on device: NO
- Ready for clean build + runtime proof: YES

## Next proof command group

On the user's PC:

```powershell
cd "D:\projects\in progress\#MIBU"
git pull
.\pc-helper\build_windows.ps1
```

Then build/install Android using the available project build path, open the PC helper, and test:

1. Device Check
2. Install APK
3. Login & Get Token -> Paste Two Tokens
4. Phone Guide -> Open MIBU
5. Phone Guide -> Start Phone Waiting
6. Community Check -> save current Community route evidence
7. Open Logs -> confirm stored state shows correctly
8. Phone Guide -> Verify Fastboot

## Current confidence

I am confident the repo now matches the safe architecture we agreed on, based on source review.

I also corrected the important code-level compile risk introduced by moving UI helper logic out of MainActivity: MibuUiHelpers now supplies the shared helpers used by the other Android screens.

I am not claiming runtime success until the clean build and phone test are completed.
