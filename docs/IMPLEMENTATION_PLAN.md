# MIBU Completion Plan

## Build order before testing

1. Android visual shell
   - Welcome/import screen
   - Dashboard/countdown screen
   - Logs placeholder
   - Instructions placeholder
   - Foreground service notification

2. PC helper visual shell
   - Compact centered Qt6 window
   - Step list
   - Time guide panel
   - Helper actions

3. PC helper device actions
   - ADB device check
   - APK install
   - Open MIBU on phone
   - Show local target time

4. Session handoff design
   - Import screen
   - Local-only storage
   - No secrets in logs
   - Clear user consent

5. First device test
   - Build debug APK
   - Install through PC helper
   - Confirm UI scaling on real phone
   - Confirm Beijing/local time conversion
   - Confirm foreground service stays active

## Locked visual baseline

The generated Android and desktop mockups are the approved target. Code should preserve their layout and look as closely as possible.
