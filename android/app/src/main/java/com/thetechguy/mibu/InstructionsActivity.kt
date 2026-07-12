package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle

class InstructionsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuPage("MIBU", "Instructions / THETECHGUY TOOL") {
            addView(mibuCard("Small disclaimer", "Bootloader unlocking can erase data, affect warranty/security features, and may stop services such as Find Device from working normally. Continue only if you understand the risk, own or are authorised to service the device, and have backed up important data."))
            addView(mibuCard("Phone preparation", "Use official HyperOS, insert a working SIM, add the Xiaomi account and Google account, enable Find Device / Find Hub, enable OEM unlocking and USB debugging, then accept the PC RSA prompt."))
            addView(mibuCard("Network", "Before the timed stage, turn Wi-Fi/WLAN off and use the working SIM's carrier/mobile data."))
            addView(mibuCard("Token setup", "Capture the Firefox new_bbs_serviceToken once and the Chrome popRunToken once, no more than 30 minutes before use. MIBU maps Firefox to lanes 1/3 and Chrome to lanes 2/4. It rejects malformed or stale captures."))
            addView(mibuCard("Waiting", "Tap Start Waiting only after both fresh captures are ready and the timing window is close enough for them to remain fresh. Allow notifications when Android asks so the foreground state remains visible. The main screen shows one live countdown; four lane states remain in Logs."))
            addView(mibuCard("Resume", "If the app or service is reopened while a wait is already armed, MIBU resumes the persisted target and remaining lanes. It does not reset lanes that already reached their windows."))
            addView(mibuCard("Community check", "For China-routed or Community-routed devices, save what you observe in Xiaomi Community. This is evidence, not an automatic success or failure claim."))
            addView(mibuCard("Verification", "After MIBU reaches the timing windows, use PC Helper to reboot to fastboot and continue with the official Mi Unlock Tool. MIBU does not claim request approval or unlock success by itself. Return to Mi Unlock Status binding only if the official route reports that the account/device is not added."))
            addView(mibuCard("Record the result", "After the official tool responds, open Logs and choose Record Official Mi Unlock Result. Record only the result actually shown. A recorded wait, account/device issue, Community requirement or unlocked state blocks another timing cycle until an explicit reset."))
            addView(mibuButton("Back", true) { finish() })
            addView(footer())
        }
    }
}
