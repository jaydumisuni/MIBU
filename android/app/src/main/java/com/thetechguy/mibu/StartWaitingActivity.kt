package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import java.time.Duration
import java.time.ZonedDateTime

class StartWaitingActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (!tokenStore.hasRequiredCaptures()) {
            Log.w(LOG_TAG, "WAITING_REJECTED_MISSING_CAPTURES")
            Toast.makeText(this, "Waiting was not armed. Import fresh Firefox and Chrome token captures first.", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val latestTarget = MibuLane.defaultLanes().maxOf { it.targetTime(nowChina) }
        val waitMs = Duration.between(nowChina, latestTarget).toMillis().coerceAtLeast(0L)
        val freshnessMs = tokenStore.millisRemaining()
        if (waitMs > freshnessMs) {
            val waitMinutes = (waitMs + 59_999L) / 60_000L
            val freshMinutes = tokenStore.minutesRemaining()
            Log.w(LOG_TAG, "WAITING_REJECTED_TOKEN_EXPIRY waitMs=$waitMs freshnessMs=$freshnessMs")
            Toast.makeText(
                this,
                "Tokens will expire before the timing window. Window is about $waitMinutes min away; tokens have about $freshMinutes min left. Capture fresh tokens closer to Beijing midnight.",
                Toast.LENGTH_LONG
            ).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        stateStore.armWaiting()
        stateStore.setVerificationState(VerificationState.WAITING_ARMED)

        try {
            val serviceIntent = Intent(this, MibuForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(serviceIntent) else startService(serviceIntent)
            Log.i(LOG_TAG, "WAITING_ACTIVITY_STARTED")
            Toast.makeText(this, "MIBU waiting armed. One countdown is visible; four timing windows are tracked in the background.", Toast.LENGTH_SHORT).show()
        } catch (exc: Exception) {
            stateStore.setVerificationState(VerificationState.UNKNOWN)
            Log.e(LOG_TAG, "WAITING_START_FAILED", exc)
            Toast.makeText(this, "Could not start waiting service: ${exc.message}", Toast.LENGTH_LONG).show()
        }

        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    companion object {
        private const val LOG_TAG = "MIBU_WAIT"
    }
}
