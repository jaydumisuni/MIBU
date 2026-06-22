# MIBU binding / verification plan

This document clarifies the part after the timed request lanes.

## Important correction

The user is not asking MIBU to operate in fastboot from the Android APK.

The user is asking MIBU to avoid forcing the user to manually open Developer Options > Mi Unlock Status when the device is already prepared and the Xiaomi account is already logged in on the phone.

## Two separate stages

MIBU must treat these as two separate stages:

1. Request / authorization stage
   - Handled by token captures and timed request lanes.
   - Uses the original script API behavior.
   - Can be checked by the app through the same API state endpoint.

2. Device unlock verification stage
   - Handled by PC Helper / Mi Unlock Tool after the phone is rebooted to fastboot.
   - Android APK cannot run while the phone is in fastboot.

## Do not force Settings first

After the request lanes run, MIBU should not automatically force the user into Xiaomi Settings first.

Preferred flow:

1. MIBU runs request lanes.
2. MIBU checks server/account state using the same request-state logic from the script.
3. If state looks approved/ready/unknown-but-possible, MIBU shows `Ready for Mi Unlock verification`.
4. PC Helper reboots the phone to fastboot through ADB.
5. PC Helper guides the user through Mi Unlock Tool.
6. Mi Unlock Tool result becomes the real proof:
   - Wait time shown = accepted/bound enough to proceed later.
   - Already unlockable/unlocked = success.
   - Account/device not added = phone-side Mi Unlock Status binding still needed.
   - Community/auth required = request/account still gated.

## APK limitation

The APK cannot continue running after the phone enters fastboot.

So the APK should prepare and report state, while PC Helper performs fastboot verification:

- APK: token setup, precheck, waiting, lane results, account/server state.
- PC Helper: ADB device check, reboot to bootloader, fastboot detection, Mi Unlock guidance/result capture.

## Settings fallback

The Settings screen remains a fallback, not the first required step.

If Mi Unlock Tool reports `account/device not added`, then MIBU should guide the user back to:

```text
Developer Options > Mi Unlock Status > Add account and device
```

If the Settings toast says `Couldn't add. Please go to Mi Community...`, MIBU must treat it as evidence, not final truth, and ask for Mi Unlock Tool verification where possible.

## UI wording

Use this flow on the app/PC helper:

```text
Request stage complete

Next step:
Verify with Mi Unlock Tool

If Mi Unlock says account/device not added, return to Mi Unlock Status binding.
```

Avoid wording that implies Settings is always mandatory before verification.
