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
    private val proofNonce by lazy { ProofNonce.from(intent) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val currentState = stateStore.reconcileTimingState(nowChina)
        if (currentState.blocksNewWaitingCycle()) {
            Log.i(LOG_TAG, "WAITING_ALREADY_COMPLETE state=${currentState.name} nonce=$proofNonce")
            Toast.makeText(this, completedMessage(currentState), Toast.LENGTH_LONG).show()
            returnToDashboard()
            return
        }

        if (!tokenStore.hasRequiredCaptures()) {
            Log.w(LOG_TAG, "WAITING_REJECTED_MISSING_CAPTURES nonce=$proofNonce")
            Toast.makeText(this, "Waiting was not armed. Import fresh Firefox and Chrome token captures first.", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        val resuming = currentState == VerificationState.WAITING_ARMED
        val targetMidnight = if (resuming) {
            stateStore.waitingTargetMidnight() ?: run {
                Log.e(LOG_TAG, "WAITING_RESUME_REJECTED_MISSING_TARGET nonce=$proofNonce")
                stateStore.setVerificationState(VerificationState.UNKNOWN)
                Toast.makeText(this, "The saved waiting target is missing. Import fresh captures and start again.", Toast.LENGTH_LONG).show()
                returnToDashboard()
                return
            }
        } else {
            MibuLane.nextTargetMidnight(nowChina)
        }

        val remainingLanes = if (resuming) {
            stateStore.lanes().filter { it.status == LaneStatus.ARMED }
        } else {
            MibuLane.defaultLanes()
        }
        if (remainingLanes.isEmpty()) {
            stateStore.reconcileTimingState(nowChina)
            Log.i(LOG_TAG, "WAITING_ALREADY_COMPLETE state=${stateStore.verificationState().name} nonce=$proofNonce")
            returnToDashboard()
            return
        }

        val latestTarget = remainingLanes.maxOf { it.targetTimeForMidnight(targetMidnight) }
        val waitMs = Duration.between(nowChina, latestTarget).toMillis().coerceAtLeast(0L)
        val freshnessMs = tokenStore.millisRemaining()
        if (waitMs > freshnessMs) {
            val waitMinutes = (waitMs + 59_999L) / 60_000L
            val freshMinutes = tokenStore.minutesRemaining()
            Log.w(LOG_TAG, "WAITING_REJECTED_TOKEN_EXPIRY waitMs=$waitMs freshnessMs=$freshnessMs nonce=$proofNonce")
            Toast.makeText(
                this,
                "Tokens will expire before the timing window. Window is about $waitMinutes min away; tokens have about $freshMinutes min left. Capture fresh tokens closer to Beijing midnight.",
                Toast.LENGTH_LONG
            ).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        if (!resuming) {
            stateStore.armWaiting(targetMidnight)
        }

        try {
            val serviceIntent = Intent(this, MibuForegroundService::class.java)
                .putExtra(ProofNonce.EXTRA, proofNonce)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(serviceIntent) else startService(serviceIntent)
            val marker = if (resuming) "WAITING_ACTIVITY_RESUMED" else "WAITING_ACTIVITY_STARTED"
            Log.i(LOG_TAG, "$marker targetMidnight=${targetMidnight.toInstant().toEpochMilli()} nonce=$proofNonce")
            Toast.makeText(
                this,
                if (resuming) "MIBU is resuming the saved waiting service without resetting reached windows."
                else "MIBU is starting the waiting service. The PC helper confirms when the service is actually armed.",
                Toast.LENGTH_SHORT
            ).show()
        } catch (exc: Exception) {
            if (!resuming) {
                stateStore.setVerificationState(VerificationState.UNKNOWN)
                stateStore.clearWaitingTarget()
            }
            Log.e(LOG_TAG, "WAITING_START_FAILED nonce=$proofNonce", exc)
            Toast.makeText(this, "Could not start waiting service: ${exc.message}", Toast.LENGTH_LONG).show()
        }

        returnToDashboard()
    }

    private fun returnToDashboard() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    private fun completedMessage(state: VerificationState): String = when (state) {
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
