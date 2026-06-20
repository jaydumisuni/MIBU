# MIBU PC Helper (Qt6)

This folder contains the compact Qt6 desktop helper.

## UI goals

- small centered window
- step-by-step wizard feel
- strong THETECHGUY TOOL branding
- dark neon theme matching the approved mockups

## First implementation scope

- device checklist view
- ADB connection check
- APK install action placeholder
- import-to-phone action placeholder
- timing guide panel with Beijing and local time

## Suggested build path

Use PySide6 for the Python reference build. Later, the same logic can be carried into your own builder/release flow.

Run locally with:

```bash
python mibu_pc_helper_qt.py
```
