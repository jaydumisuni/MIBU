package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Bundle

class GuideActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("Step-by-Step Guide", "Follow these steps in order to prepare your Xiaomi device safely."))
            addView(mibuStep(1, R.drawable.mibu_icon_device, "Connect your phone", "Use USB and enable USB debugging.", MibuColors.orange))
            addView(mibuStep(2, R.drawable.mibu_icon_device, "Open MIBU PC Helper", "Run Device Check and accept the RSA prompt.", MibuColors.purple))
            addView(mibuStep(3, R.drawable.mibu_icon_install, "Install MIBU.apk", "Let the PC helper install, verify and open this app.", MibuColors.blue))
            addView(mibuStep(4, R.drawable.mibu_icon_account, "Log in to Xiaomi", "Use your normal external browser; MIBU never asks for the password.", MibuColors.blue))
            addView(mibuStep(5, R.drawable.mibu_icon_session, "Import session from PC", "Push both approved captures into MIBU.", MibuColors.cyan))
            addView(mibuStep(6, R.drawable.mibu_icon_clock, "Start waiting", "Keep mobile data available and let the phone own the countdown.", MibuColors.purple))
            addView(mibuStep(7, R.drawable.mibu_icon_check, "Verify binding", "Open Mi Unlock & Binding; use the official result to choose recovery.", MibuColors.green))
            addView(mibuLiveRow(R.drawable.mibu_icon_signal, "Recommendation", "Keep a stable internet connection near the target time", MibuColors.orange, "IMPORTANT").root)
            addView(mibuAction(R.drawable.mibu_icon_play_clean, "Start Waiting", "Arm or resume the phone-side service", MibuColors.orange, true) {
                startActivity(Intent(this@GuideActivity, StartWaitingActivity::class.java))
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_logs, "Open Logs", "Review live activity and proof state", MibuColors.blue) {
                startActivity(Intent(this@GuideActivity, LogsActivity::class.java))
            }.root)
            addView(footer())
        }
    }
}
