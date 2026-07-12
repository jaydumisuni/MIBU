package com.thetechguy.mibu

import android.content.Intent

object ProofNonce {
    const val EXTRA = "mibu_proof_nonce"
    private val SAFE = Regex("^[A-Za-z0-9_-]{8,64}$")

    fun from(intent: Intent?): String {
        val value = intent?.getStringExtra(EXTRA)?.trim().orEmpty()
        return if (SAFE.matches(value)) value else "none"
    }
}
