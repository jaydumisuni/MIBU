# MIBU

**MIBU = Mi Bootloader Unlock Helper**

MIBU is planned as a two-part toolset:

1. **MIBU Android app (`MIBU.apk`)**
   - Runs on the Android phone.
   - Receives a Xiaomi session/token from the PC helper or future in-app login.
   - Stores the token locally.
   - Shows account/request status, Beijing unlock window, local converted time, countdown, and logs.
   - Runs a foreground service so the phone can stay awake/data-on near the request window.

2. **MIBU PC Helper**
   - Guides the user through login/token preparation on PC.
   - Installs `MIBU.apk` to the phone once ADB is enabled.
   - Pushes the prepared token/session to the app over ADB in dev mode.
   - Computes the Beijing unlock target time and converts it to the user's local timezone automatically.

## Guardrails

MIBU is a timing and workflow helper for legitimate Xiaomi bootloader unlock requests using the user's own Xiaomi account. It should not bypass Xiaomi account ownership checks, device locks, waiting periods, rate limits, or other official restrictions.

If Xiaomi reports a daily limit, account restriction, expired login, or not-eligible state, MIBU should explain the result and tell the user when to retry instead of spamming requests.

## Monorepo layout

```text
android/      MIBU Android APK source
pc-helper/   PC helper for ADB install, token handoff, and time guidance
docs/        architecture, flow notes, safety notes
.github/     CI build/test workflows
```

## First build target

The first milestone is not the final unlock sender. It is a safe skeleton that proves:

- Android project builds.
- PC helper can see ADB.
- PC helper can install the APK.
- PC helper can package and push a token payload to the APK.
- The APK can receive and show token/session status without exposing secrets.
- Time conversion to the Beijing 23:59:58.600 request window works regardless of the user's timezone.
