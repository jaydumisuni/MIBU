# Safe Completion Matrix

## Covered in repo

- Android app project and build skeleton.
- MIBU launcher icon placeholder.
- MIBU Android dashboard shell.
- Logs and Instructions screens.
- Foreground service shell.
- Qt6 compact PC helper visual shell.
- PC helper CLI for device listing, APK install, and local time guide.
- THETECHGUY TOOL branding breadcrumbs.
- GitHub Actions build and syntax checks.

## To finish locally before device test

- Replace placeholder vector icon with the final MIBU PNG/SVG assets.
- Replace text ghost placeholder with the final large ghost artwork.
- Package the Qt6 helper with your PC builder.
- Build the debug APK through Gradle or GitHub Actions.
- Use the PC helper CLI/GUI to install the APK after ADB is enabled.

## Safety boundary

MIBU should remain a guided workflow, timing, and installation helper for a user-owned Xiaomi account and device. It must not implement credential stealing, hidden account access, account lock bypass, rate-limit bypass, or restriction bypass logic.

The secure handoff flow should be built only as a user-consented import/export path and should avoid printing sensitive values in logs.
