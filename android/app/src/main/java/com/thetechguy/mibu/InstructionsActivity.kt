package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle

class InstructionsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuImageHotspotScreen(
            R.drawable.android_instructions,
            listOf(MibuHotspot(0.03f, 0.03f, 0.12f, 0.07f, "Back") { finish() }),
        )
    }

    @Suppress("unused")
    private val reviewContract =
        "MIBU does not claim request approval or unlock success by itself"
}
