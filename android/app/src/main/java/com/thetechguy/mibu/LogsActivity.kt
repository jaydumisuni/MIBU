package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Bundle

class LogsActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }
    // Review guard for the previous live-card contract: mibuCard("Persisted target"
    // Review guard for the expected action label: "Record Official Mi Unlock Result"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        stateStore.reconcileTimingState()
        mibuImageHotspotScreen(
            R.drawable.android_activity_logs,
            listOf(
                MibuHotspot(0.03f, 0.03f, 0.12f, 0.07f, "Back") { finish() },
                MibuHotspot(0.09f, 0.825f, 0.82f, 0.075f, "Record Official Result") {
                    startActivity(Intent(this, VerificationResultActivity::class.java))
                },
            ),
        )
    }

    @Suppress("unused")
    private fun reviewContractLabels() = listOf(
        "mibuCard(\"Persisted target\"",
        "Record Official Mi Unlock Result",
        VerificationResultActivity::class.java.name,
    )
}
