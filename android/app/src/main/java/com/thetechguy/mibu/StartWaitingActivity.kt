package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import java.time.ZonedDateTime

class StartWaitingActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }
    private val logStore by lazy { LogStore(this) }
    private val proofNonce by lazy { ProofNonce.from(intent) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val currentState = stateStore.reconcileTimingState(nowChina)
        if (currentState.blocksNewWaitingCycle()) {
            Log.i(LOG_TAG, "WAITING_ALREADY_COMPLETE state=${currentState.name} nonce=$proofNonce")
            logStore.add("Start Waiting skipped: ${currentState.name}")
            if (currentState.isTimingComplete()) {
                startCompletedProofService()
            }
            Toast.makeText(this, completedMessage(currentState), Toast.LENGTH_LONG).show()
            returnToDashboard()
            return
        }

        if (!tokenStore.hasRequiredCaptures()) {
            Log.w(LOG_TAG, "WAITING_REJECTED_MISSING_CAPTURES nonce=$proofNonce")
            Log.w(SERVICE_PROOF_TAG, "WAITING_SERVICE_REJECTED_MISSING_CAPTURES nonce=$proofNonce")
            logStore.add("Start Waiting needs two fresh browser captures")
            Toast.makeText(this, "Waiting was not armed. Import fresh Firefox and Chrome token captures first.", Toast.LENGTH_LONG).show()
            startActivity(Intent(this, TokenImportActivity::class.java))
            finish()
            return
        }

        if (stateStore.serviceRunning()) {
            Log.i(LOG_TAG, "WAITING_ALREADY_RUNNING state=${currentState.name} nonce=$proofNonce")
            Toast.makeText(this, "The Xiaomi request service is already checking or waiting.", Toast.LENGTH_SHORT).show()
            returnToDashboard()
            return
        }

        val resuming = currentState == VerificationState.WAITING_ARMED ||
            currentState == VerificationState.PREFLIGHT_CHECKING ||
            currentState == VerificationState.REQUESTS_RUNNING
        val targetMidnight = stateStore.waitingTargetMidnight()
            ?.takeIf { resuming }
            ?: MibuLane.nextTargetMidnight(nowChina)

        // Only the service may promote this to WAITING_ARMED, after live Xiaomi,
        // cellular-network, token-freshness and server-clock checks all pass.
        stateStore.beginPreflight(targetMidnight)

        try {
            startWaitingService()
            val marker = if (resuming) "WAITING_ACTIVITY_RESUMED" else "WAITING_ACTIVITY_STARTED"
            Log.i(LOG_TAG, "$marker targetMidnight=${targetMidnight.toInstant().toEpochMilli()} nonce=$proofNonce")
            logStore.add(if (resuming) "Xiaomi preflight resumed" else "Xiaomi preflight started")
            Toast.makeText(
                this,
                if (resuming) "MIBU is resuming the saved Xiaomi request cycle."
                else "Checking Xiaomi eligibility, cellular data and server time before arming.",
                Toast.LENGTH_SHORT
            ).show()
        } catch (exc: Exception) {
            stateStore.setVerificationState(VerificationState.UNKNOWN)
            stateStore.setServiceRunning(false)
            Log.e(LOG_TAG, "WAITING_START_FAILED nonce=$proofNonce", exc)
            Log.e(SERVICE_PROOF_TAG, "WAITING_SERVICE_FAILED nonce=$proofNonce", exc)
            logStore.add("Waiting service failed: ${exc.message ?: "unknown error"}")
            Toast.makeText(this, "Could not start waiting service: ${exc.message}", Toast.LENGTH_LONG).show()
        }

        returnToDashboard()
    }

    private fun startCompletedProofService() {
        if (proofNonce == "none") return
        runCatching { startWaitingService() }
            .onFailure { Log.e(LOG_TAG, "WAITING_COMPLETION_PROOF_START_FAILED nonce=$proofNonce", it) }
    }

    private fun startWaitingService() {
        val serviceIntent = Intent(this, MibuForegroundService::class.java)
            .putExtra(ProofNonce.EXTRA, proofNonce)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun returnToDashboard() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    private fun completedMessage(state: VerificationState): String = when (state) {
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION ->
            "Xiaomi has already accepted this request. Continue with Mi Unlock Status instead of starting another cycle."
        VerificationState.TIMING_WINDOW_REACHED ->
            "This legacy timing marker is not Xiaomi approval. MIBU will run a fresh verified preflight."
        VerificationState.QUOTA_LIMIT_REACHED ->
            "Xiaomi returned application quota limit reached. Keep this result and retry only in the next valid window."
        VerificationState.BLOCKED_UNTIL_DEADLINE ->
            "Xiaomi has blocked new requests until the recorded deadline."
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

    companion object {
        private const val LOG_TAG = "MIBU_WAIT"
        private const val SERVICE_PROOF_TAG = "MIBU_SERVICE"
    }
}
