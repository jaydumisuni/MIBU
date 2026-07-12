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
            addView(mibuCard("Token setup", "Capture the Firefox new_bbs_serviceToken once and the Chrome popRunToken once, no more than 30 minutes before use. MIBU maps Firefox to slots 1/3 and Chrome to slots 2/4."))
            addView(mibuCard("Waiting", "Tap Start Waiting only after both fresh captures are ready. The main screen shows one live countdown. Four time-shift lanes remain hidden and their state is available in Logs."))
            addView(mibuCard("Community check", "For China-routed or Community-routed devices, save what you observe in Xiaomi Community. This is evidence, not an automatic success or failure claim."))
            addView(mibuCard("Verification", "After the request stage, use PC Helper to reboot to fastboot and continue with the official Mi Unlock Tool. Return to Mi Unlock Status binding only if Mi Unlock reports that the account/device is not added."))
            addView(mibuButton("Back", true) { finish() })
            addView(footer())
        }
    }
}
