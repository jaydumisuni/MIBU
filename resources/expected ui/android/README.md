# MIBU Android expected UI baseline

This folder restores the approved Android visual reference that was previously missing from the repository.

## Canonical visual reference

- `approved_android_ui_baseline_sheet.svg`

The sheet was recovered from the exact approved conversation uploads rather than redrawn from memory. It contains these five reference states:

1. Android welcome / entry screen
2. Android dashboard / status screen
3. Android dashboard / waiting state
4. Android step-by-step guide
5. Approved MIBU logo

## Recovered source identities

| Baseline state | Original approved upload | Original SHA-256 |
|---|---|---|
| Welcome / entry | `ChatGPT Image Jun 20, 2026, 11_42_25 PM (1).png` | `eddd106925e8305f2d5488d980c6934fffd6b29e7445d9741f4a90cc913c3e94` |
| Dashboard / status | `ChatGPT Image Jun 20, 2026, 11_42_25 PM (2).png` | `64934683b4b6612811b04c5f6fa6551a1c122b88e402bc12cf750c432786845d` |
| Dashboard / waiting | `ChatGPT Image Jun 21, 2026, 12_08_27 AM (4).png` | `11981b339f407b5767b9af10c58e101f999e79e77870326757280ace95187a04` |
| Step-by-step guide | `neon_themed_step_by_step_mobile_guide.png` | `17db2c5734b5e5b5bd93531d35e0c72ba324c4af6b7230f1042b154dca67f75f` |
| MIBU logo | `MIBU Logo(1).png` | `0ad11c85ee474412b41399ea4c62e7cc1acaa9b56a85bb88f0690f2ba093bfda` |

The embedded previews are deliberately lightweight repository references. Their purpose is to lock the approved composition, branding, hierarchy and screen states so future implementation work cannot silently drift or invent replacement artwork.

## Review rule

Android UI changes must be compared against this baseline before release. The implemented app may contain live text and responsive layout differences, but it must retain:

- the approved MIBU identity and logo;
- dark neon THETECHGUY TOOL presentation;
- clear account/session status;
- Beijing and local timing presentation;
- one visible countdown with background waiting details kept out of the main dashboard;
- Mobile Data reminder;
- foreground-service state;
- Start Waiting, Logs and Instructions access;
- the step-by-step guide and THETECHGUY TOOL team footer.

This folder is an evidence baseline, not runtime artwork and not a substitute for actual-device visual verification.
