package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.Toast

class StartWaitingActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!tokenStore.hasRequiredCaptures()) {
            Toast.makeText(
                this,
                "Waiting was not armed. Import fresh Firefox and Chrome token captures first.",
                Toast.LENGTH_LONG
            ).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        stateStore.armWaiting()

        try {
            val serviceIntent = Intent(this, MibuForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(serviceIntent)
            } else {
                startService(serviceIntent)
            }
            Toast.makeText(
                this,
                "MIBU waiting armed. One countdown is visible; four lanes are tracked in the background.",
                Toast.LENGTH_SHORT
            ).show()
        } catch (exc: Exception) {
            Toast.makeText(this, "Could not start waiting service: ${exc.message}", Toast.LENGTH_LONG).show()
        }

        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}
