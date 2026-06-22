# MIBU original script flow understanding

This document locks the current understanding before the Android app is upgraded. The goal is to avoid guessing and avoid over-correcting the UI or logic.

## What the original guide/script is doing

The guide is not just a countdown screen. It is a timed multi-lane request flow.

### Requirements from the guide

- Xiaomi account and Google account added on the phone.
- Find My Device / Find Hub enabled.
- Valid SIM inserted.
- Carrier/mobile data enabled.
- Wi-Fi/WLAN disabled.
- Official HyperOS firmware.
- Developer Options enabled.
- USB Debugging enabled.
- OEM Unlocking enabled.
- Cookies/session tokens collected shortly before running, usually within 30 minutes.
- Xiaomi account/device must not be forced into the qualification/community-only path.
- Xiaomi account limits still apply: one phone per month, three phones per year.
- Even if the request is accepted, normal MIUI/Mi Unlock waiting time may still apply, such as 72 hours.

## User-risk disclaimer rule

MIBU is for users who already understand bootloader unlocking and device servicing risk. Do not make the app feel like a fear screen or a legal lecture.

Use a small factual disclaimer in onboarding/about/instructions:

```text
Bootloader unlocking can erase data, affect warranty/security features, and may stop services such as Find Device from working normally. Continue only if you understand the risk, own or are authorised to service the device, and have backed up important data.
```

Do not repeat the disclaimer on every screen. Show it once during onboarding and keep it available in Instructions/About.

## China / Mainland / Community-app uncertainty

The current public information around Xiaomi HyperOS bootloader unlock is messy and changes often. Treat this as a high-risk decision point, not a solved step.

Current working rule:

- For China / Mainland-China-targeted devices, MIBU must warn that normal bootloader unlock may be unavailable or much more restricted depending on policy, account, ROM, device, and date.
- If the device/account is on a China/Chinese Community path, MIBU should include a manual Community-app check step before the timed request attempt.
- The user found that manually adding/checking the device inside Xiaomi Community may be needed for China devices. This is not proven universal, so the app should present it as `China device manual Community device check`, not as a guaranteed requirement.
- MIBU must not silently skip this check. It should ask the user to confirm whether the device appears in Community / My Devices when the device looks China/Chinese-community routed.

Suggested status values:

- `COMMUNITY_DEVICE_CONFIRMED`
- `COMMUNITY_DEVICE_NOT_FOUND`
- `COMMUNITY_ROUTE_NOT_REQUIRED`
- `COMMUNITY_ROUTE_UNKNOWN`

The app should save this as evidence so later results can be compared.

## Token sources

The script uses four token positions.

Based on the guide:

- Firefox/Cookie Editor provides `new_bbs_serviceToken`.
  - This token is pasted into positions 1 and 3 of `token.txt`.
- Chrome/Javascript prompt provides `popRunToken`.
  - This token is pasted into positions 2 and 4 of `token.txt`.

So MIBU must support at least:

- Token slot 1: serviceToken lane
- Token slot 2: popRunToken lane
- Token slot 3: serviceToken lane
- Token slot 4: popRunToken lane

The app should not pretend this is only one token unless we later prove only one lane is needed.

## Time-shift lanes

The original `timeshift.txt` shown by the user contains:

```text
1400
900
400
100
```

The visible script output suggests each terminal lane targets a shifted send time near Chinese midnight:

- Lane 1: 1400 ms offset, waits until 23:59:58.600 CST
- Lane 2: 900 ms offset, waits until 23:59:59.100 CST
- Lane 3: 400 ms offset, waits until 23:59:59.600 CST
- Lane 4: 100 ms offset, waits until 23:59:59.900 CST

This appears to mean: submit just before 00:00:00 China time, using different offsets to hit the server window.

## Four terminal behavior

The PC script guide says:

- Run Script.py and enter `1`.
- Without closing the first window, run Script.py again and enter `2`.
- Repeat for `3` and `4`.
- Each script instance uses its corresponding token slot and timeshift.
- All four windows wait and then send automatically around 00:00 China time.

MIBU should model this as four internal request lanes, not four visible terminals.

## Important uncertainty

We do not yet know whether all four lanes are always required in the upgraded app.

Current rule:

- Keep four lanes in the design model.
- Do not remove the lanes until testing proves a simpler model is reliable.
- The UI may show them as advanced details instead of making the home screen too busy.

## Correct Android app state machine

The app should have these states:

1. `PRECHECK`
   - SIM present guidance
   - Mobile data ON
   - Wi-Fi/WLAN OFF
   - Find My Device / Find Hub enabled guidance
   - Xiaomi account present/confirmed by user
   - Google account present/confirmed by user when required by the guide
   - Developer settings guidance where needed
   - China/Community device check if the device/account is routed through Chinese Community

2. `SESSION_IMPORT`
   - User logs in themselves.
   - MIBU does not ask for the Xiaomi password.
   - Session/token imported explicitly.
   - Token slots should support the original four-lane script model.

3. `WAITING_ARMED`
   - Beijing target time shown.
   - Local target time shown.
   - Time remaining shown.
   - Four time-shift lanes shown as armed/pending.
   - Foreground service started.

4. `REQUEST_WINDOW_OPEN`
   - The app fires the lane requests according to their offsets if the app is responsible for request submission.
   - If the app is only guiding the phone-side binding stage, it should alert the user exactly when the target window opens.

5. `LANE_RESULTS`
   - Each lane records a result:
     - `REQUEST_SENT`
     - `QUOTA_LIMIT`
     - `COMMUNITY_GATE`
     - `NETWORK_ERROR`
     - `TOKEN_EXPIRED`
     - `UNKNOWN`

6. `BINDING_GUIDE`
   - Open/guide Mi Unlock Status.
   - User taps Add account and device.
   - Settings toast is captured as evidence, not final truth.

7. `BINDING_RESULT`
   - Possible final states:
     - `BIND_SUCCESS`
     - `BIND_FAILED_COMMUNITY_GATE`
     - `BIND_RESULT_UNKNOWN`

8. `VERIFY_WITH_MI_UNLOCK`
   - Mi Unlock Tool response is the reliable confirmation if Settings gives an unclear toast.
   - If Mi Unlock reports a wait time, binding likely worked.
   - If Mi Unlock reports not bound or authorization required, binding did not land or is gated.

## UI rule

Do not redesign away from the user's visual baseline.

The Android UI should show the real flow states:

- Session/token slots
- Target time
- Start Waiting
- Time-shift queue/lane status
- China/Community manual device check where relevant
- Binding check/result capture
- Logs
- Instructions

The PC helper should not replace the Android app experience. It should support:

1. Device Check
2. Install APK
3. Login/Get Token or Token Push
4. Phone Guide / Binding / Verification support

## ADB rule

Do not assume ADB already works.

Device Check must support the real ADB enabling flow:

- No device: cable/driver/USB mode issue.
- Unauthorized: user must accept RSA prompt.
- Offline: restart ADB/reconnect/toggle USB debugging.
- Device online: proceed.

The user's older ADB enabler script is a guide for this logic.

## Proof-check / CodeRabbit review checklist

Before coding the upgraded app, every implementation must pass this checklist:

- Does the app preserve the original four-lane script model?
- Does it support four token slots, not just one session string?
- Does it show the 1400 / 900 / 400 / 100 ms lanes somewhere?
- Does `Start Waiting` arm the wait stage rather than jumping straight to binding result?
- Does the app show precheck status for SIM/mobile data/Wi-Fi/Find Device/Xiaomi account/Google account?
- Does it include a China/Community device check state for China-routed devices?
- Does it show the concise risk disclaimer once during onboarding/about/instructions without turning the app into a fear screen?
- Does it distinguish Settings toast from real server/binding confirmation?
- Does it save lane results and binding evidence to logs?
- Does the PC helper respect the real ADB enabling flow?
- Does the UI remain close to the user's branding and not revert to a generic layout?
- Does the build include resources safely and avoid `git clean -fd` wiping UI assets?
- Does the final result avoid claiming success when the state is unknown?

## Core lesson

The app should not be built from assumptions. It should first preserve the original script behavior as a state machine, then improve the UI and reliability around that behavior.
