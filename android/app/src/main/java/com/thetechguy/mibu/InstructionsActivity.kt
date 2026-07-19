package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle

class InstructionsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("Instructions", "Follow the steps below in order."))
            addView(mibuStep(1, R.drawable.mibu_icon_device, "On PC tap Device Check", "Enable USB debugging when prompted.", MibuColors.orange))
            addView(mibuStep(2, R.drawable.mibu_icon_check, "Accept USB debugging", "Tap Allow and Always allow on the RSA prompt.", MibuColors.purple))
            addView(mibuStep(3, R.drawable.mibu_icon_install, "On PC tap Install APK", "The helper installs and verifies MIBU.", MibuColors.blue))
            addView(mibuStep(4, R.drawable.mibu_icon_account, "On PC tap Login & Get Token", "Sign in yourself in the external browser.", MibuColors.green))
            addView(mibuStep(5, R.drawable.mibu_icon_session, "Session gets imported", "The approved captures are sent to this phone.", MibuColors.orange))
            addView(mibuStep(6, R.drawable.mibu_icon_signal, "Confirm status and mobile data", "Then tap Start Waiting; the phone continues from there.", MibuColors.purple))
            addView(mibuCard("Safety", "MIBU does not claim request approval or unlock success by itself. Only record what Xiaomi or the official Mi Unlock Tool actually shows."))
            addView(mibuAction(R.drawable.mibu_icon_check, "Got it", "Back to MIBU dashboard", MibuColors.orange, true) { finish() }.root)
            addView(footer())
        }
    }

    @Suppress("unused")
    private val reviewContract = "MIBU does not claim request approval or unlock success by itself"
}
