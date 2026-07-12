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

        val currentState = stateStore.reconcileTimingState()
        if (currentState.blocksNewWaitingCycle()) {
            Log.i(LOG_TAG, "WAITING_ALREADY_COMPLETE state=${currentState.name}")
            val message = when (currentState) {
                VerificationState.TIMING_WINDOW_REACHED,
                VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION ->
                    "The timing stage is already complete. Continue with PC verification instead of starting a new wait."
                VerificationState.WAIT_TIME_SHOWN ->
                    "Mi Unlock already returned a waiting period. Keep that result; do not start another timing cycle."
                VerificationState.ACCOUNT_DEVICE_NOT_ADDED ->
                    "The account/device result must be resolved before another timing cycle can be started."
                VerificationState.COMMUNITY_AUTH_REQUIRED ->
                    "Xiaomi Community authorisation is still required. Resolve that result before starting another timing cycle."
                VerificationState.UNLOCKED ->
                    "This device is already recorded as unlocked. No waiting cycle is required."
                else -> "A completed verification result is already recorded."
            }
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
            startActivity(Intent(this, MainActivity::class.java))
            finish()
            return
        }

        if (!tokenStore.hasRequiredCaptures()) {
            Log.w(LOG_TAG, "WAITING_REJECTED_MISSING_CAPTURES")
            Toast.makeText(this, "Waiting was not armed. Import fresh Firefox and Chrome token captures first.", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val targetMidnight = MibuLane.nextTargetMidnight(nowChina)
        val latestTarget = MibuLane.defaultLanes().maxOf { it.targetTimeForMidnight(targetMidnight) }
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

        stateStore.armWaiting(targetMidnight)

        try {
            val serviceIntent = Intent(this, MibuForegroundService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(serviceIntent) else startService(serviceIntent)
            Log.i(LOG_TAG, "WAITING_ACTIVITY_STARTED targetMidnight=${targetMidnight.toInstant().toEpochMilli()}")
            Toast.makeText(this, "MIBU is starting the waiting service. The PC helper confirms when the service is actually armed.", Toast.LENGTH_SHORT).show()
        } catch (exc: Exception) {
            stateStore.setVerificationState(VerificationState.UNKNOWN)
            stateStore.clearWaitingTarget()
            Log.e(LOG_TAG, "WAITING_START_FAILED", exc)
            Toast.makeText(this, "Could not start waiting service: ${exc.message}", Toast.LENGTH_LONG).show()
        }

        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    private fun VerificationState.blocksNewWaitingCycle(): Boolean = when (this) {
        VerificationState.TIMING_WINDOW_REACHED,
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION,
        VerificationState.WAIT_TIME_SHOWN,
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED,
        VerificationState.COMMUNITY_AUTH_REQUIRED,
        VerificationState.UNLOCKED -> true
        else -> false
    }

    companion object {
        private const val LOG_TAG = "MIBU_WAIT"
    }
}
