# MIBU 0.2 Review Status

This file separates what the repository is designed to prove from what still requires ATHENA and a physical phone.

## Source-reviewed contracts

The current source contract covers:

- Android version `0.2.0-dev` and proof protocol `2`;
- two validated captures mapped to four timing lanes;
- 30-minute independent freshness and fail-closed clock rollback;
- one persisted Beijing-midnight target;
- idempotent waiting resume without resetting reached lanes;
- immediate foreground entry on every service path;
- authoritative-result preservation against delayed callbacks;
- nonce-correlated import, status and service proof;
- state-only proof that does not expose token values;
- explicit official-result recording and confirmed workflow reset;
- exactly one supported ADB device and one supported fastboot device;
- version-aware APK installation/update verification;
- restored Android expected-UI baseline and provenance;
- shared PC artwork/hotspot geometry;
- source-fresh local Android builds;
- explicit current-commit APK reuse only inside CI;
- clean PyInstaller release creation;
- required APK, platform-tools, UI evidence and `SHA256SUMS.txt`.

## Automated proof designed in CI

The workflows are configured to run:

- the architecture source review;
- the focused proof-v2 review;
- Android UI-baseline validation;
- Android lint;
- Android unit tests;
- Android APK assembly;
- complete Python unittest discovery;
- offscreen Qt construction and geometry checks;
- deterministic SVG-to-PNG/ICO rendering;
- a Windows release build from the Android artifact;
- release-content and checksum-manifest verification.

A CI run must complete successfully before this document is treated as an automated proof result.

## Physical runtime proof still required

Only a real ATHENA/phone run can prove:

- Windows USB driver behaviour;
- ADB authorisation on the target phone;
- MIUI/HyperOS installer behaviour;
- foreground-service survival and notifications on the target ROM;
- the actual sub-second waiting run on the phone;
- reboot and fastboot enumeration on ATHENA;
- the result shown by Xiaomi's official Mi Unlock Tool.

## Product claim boundary

MIBU currently proves local timing, freshness, state persistence, workflow correlation and handoff readiness. It does not currently submit or replay Xiaomi network requests and does not treat timing completion, a toast or fastboot presence as official unlock approval.
