# MIBU Login Flow

## Principle

The user must log in themselves. MIBU must not ask for, store, or hide-capture a Xiaomi password.

The PC helper should redirect the user to the normal browser login flow. After the user completes login, MIBU continues with guided setup and timing.

## Approved login model

```text
PC Helper
  -> Open normal browser login page
  -> User logs in themselves
  -> User confirms login completed
  -> PC Helper continues to setup/timing
  -> Android app receives only an explicit user-approved handoff later
```

## Why browser redirect

- User sees the real login page.
- User controls the account login.
- Passwords are never entered into MIBU.
- The flow is easier to explain and support.

## PC Helper screens

1. Welcome / device checklist.
2. Open login in browser.
3. User confirms login completed.
4. Connect phone with ADB.
5. Install MIBU.apk.
6. Continue on phone app.
7. Show Beijing/local timing guide.

## Android app behavior

The Android app should not require the user to log in again during the first release. It should show:

- session/status waiting for PC helper
- local time conversion
- countdown
- mobile-data reminder
- logs/instructions

## Future handoff

A later handoff can be added only as an explicit consent import/export step. It must avoid printing secrets in logs and should not read unrelated browser data.
