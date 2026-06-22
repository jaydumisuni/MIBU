# MIBU hotspot UI expected assets

The PC helper should keep the rendered image-based UI as the visual source of truth.
The code must only add transparent clickable hotspot regions on top of those renders.

## Main PC workflow image
Place this in `resources/expected ui/pc/`:

- `01_pc_main_four_button_workflow.png`

This image represents the 4-button guided workflow:

1. Device Check
2. Install APK
3. Login & Get Token
4. Phone Guide

## Popup images
Place these in `resources/expected ui/pc/`:

- `02_popup_device_check_guide.png`
- `03_popup_install_apk.png`
- `04_popup_login_get_token.png`
- `05_popup_phone_guide.png`

Each popup image should keep the final branded look. The code only wires hotspot click areas.

## Android reference screens
Place these in `resources/expected ui/android/`:

- `01_android_welcome_import.png`
- `02_android_dashboard_waiting.png`
- `03_android_guide.png`
- `04_android_settings.png`
- `05_android_instructions.png`
- `06_android_activity_logs.png`
- `07_android_account_session.png`

These are reference assets for branding and app continuity.

## Audio assets
Place these in `resources/expected ui/`:

- `TTG_v4_clean_connected_success.wav`
- `TTG_v4_clean_speaker_turn_on.wav`

## Build rule
`pc-helper/build_windows.ps1` should bundle:

- the built `MIBU.apk`
- the full `resources/` folder
- both WAV files when present

## Design rule
Do not redesign the MIBU UI in code.
Do not replace the branded images with generic widgets.
Use the hotspot method so the exact rendered UI remains intact while buttons still work.
