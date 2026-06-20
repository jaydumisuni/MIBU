# MIBU Token Flow

## Principle

MIBU only needs the user-approved session/token material required for the workflow. The user must obtain or approve that token themselves through a visible browser/login flow.

MIBU must not ask for a Xiaomi password, silently read unrelated browser data, or hide-capture credentials.

## Approved model

```text
User opens login in browser
  -> User logs in themselves
  -> User copies/approves the required token/session value
  -> User imports it into MIBU explicitly
  -> MIBU validates the presence/format locally
  -> MIBU continues with status, timing, and phone-side guidance
```

## App behavior

The Android app should have an **Import session from PC** screen:

- Token/session input box.
- Clear warning that this is sensitive.
- Save button.
- Clear saved session button.
- Never print the token in logs.
- Show only a short masked preview or length.

## PC helper behavior

The PC helper should guide the user to:

- open login in the normal browser
- copy/approve the required token value
- paste/import it explicitly
- send only an explicit user-approved handoff to the phone later

## Storage

Development builds may use basic local storage. Production builds should move sensitive values to Android Keystore-backed storage and encrypted local storage on PC.
