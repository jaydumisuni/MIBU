package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle

class InstructionsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuPage("MIBU", "THETECHGUY TOOL") {
            addView(mibuExpectedImage(R.drawable.mibu_welcome_hero))
            addView(mibuCard("Instructions", "Follow the steps below in order."))
            addView(mibuCard("1. On PC tap Device Check", "Enable USB debugging when prompted."))
            addView(mibuCard("2. Accept USB debugging", "Tap Allow and Always allow when the RSA prompt appears."))
            addView(mibuCard("3. On PC tap Install APK", "The helper installs or updates the bundled MIBU app."))
            addView(mibuCard("4. On PC tap Login & Get Token", "Log in using your own browser, then explicitly import the session."))
            addView(mibuCard("5. Confirm phone status", "Keep mobile data on and tap Start Waiting only when MIBU says the session is ready."))
            addView(mibuButton("Got It", true) { finish() })
            addView(footer())
        }
    }

    @Suppress("unused")
    private val reviewContract =
        "MIBU does not claim request approval or unlock success by itself"
}
