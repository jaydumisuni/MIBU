package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast

class StartWaitingActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!tokenStore.hasSession()) {
            Toast.makeText(this, "No session imported yet. Import session first.", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        try {
            startForegroundService(Intent(this, MibuForegroundService::class.java))
            Toast.makeText(this, "MIBU waiting service started.", Toast.LENGTH_SHORT).show()
        } catch (exc: Exception) {
            Toast.makeText(this, "Could not start waiting service: ${exc.message}", Toast.LENGTH_LONG).show()
        }

        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
