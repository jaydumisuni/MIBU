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
| Dashboard / status | `ChatGPT Image Jun 20, 2026, 11_42_25 PM (2).png` | `53eba33bda7b491f098ebe1f7b99ca7d2701000b488ed3a8c1bed41badf1203c` |
| Dashboard / waiting | `ChatGPT Image Jun 21, 2026, 12_08_27 AM (4).png` | `0375aec08e26d73bd9cc8d920a998c196fdd6ffe3ccec7f89015d9e7ef8028bf` |
| Step-by-step guide | `neon_themed_step_by_step_mobile_guide.png` | `c7babc28a23ecbacbcd775752fd3eef465abfda9a85402613c4fc50445595528` |
| MIBU logo | `MIBU Logo(1).png` | `ab22eb530c56edbb5525ba874bac95c1bddfd83f6d76c2ebf102bfac273364c3` |

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
