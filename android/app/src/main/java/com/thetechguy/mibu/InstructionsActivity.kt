package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle

class InstructionsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuPage("MIBU", "Instructions / THETECHGUY TOOL") {
            addView(mibuCard("Before you start", "Back up the phone. Bootloader unlocking can wipe device data and may affect warranty."))
            addView(mibuCard("Phone setup", "Use official HyperOS, insert a working SIM, enable mobile data, add the Xiaomi account, and enable Developer Options."))
            addView(mibuCard("Developer options", "Enable OEM unlocking and USB debugging. Confirm the ADB authorization prompt when connected to the PC."))
            addView(mibuCard("PC helper", "Use MIBU PC Helper to check connection, install the APK, and show the local time for the Beijing timing window."))
            addView(mibuCard("Timing", "The reference timezone is Asia/Shanghai. MIBU converts the target window to your local time automatically."))
            addView(mibuButton("Back", true) { finish() })
            addView(footer())
        }
    }
}
