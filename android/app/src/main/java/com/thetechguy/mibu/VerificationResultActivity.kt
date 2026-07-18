package com.thetechguy.mibu

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.util.Log

class VerificationResultActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun render() {
        mibuImageHotspotScreen(
            R.drawable.android_guide,
            listOf(
                MibuHotspot(0.03f, 0.03f, 0.12f, 0.07f, "Back") { finish() },
                MibuHotspot(0.09f, 0.520f, 0.82f, 0.060f, "Official wait time shown") {
                    record(VerificationState.WAIT_TIME_SHOWN)
                },
                MibuHotspot(0.09f, 0.590f, 0.82f, 0.060f, "Account device not added") {
                    record(VerificationState.ACCOUNT_DEVICE_NOT_ADDED)
                },
                MibuHotspot(0.09f, 0.660f, 0.82f, 0.060f, "Community authorisation required") {
                    record(VerificationState.COMMUNITY_AUTH_REQUIRED)
                },
                MibuHotspot(0.09f, 0.730f, 0.82f, 0.060f, "Device unlocked") {
                    record(VerificationState.UNLOCKED)
                },
                MibuHotspot(0.09f, 0.805f, 0.82f, 0.060f, "Reset workflow") {
                    confirmReset()
                },
            ),
        )
    }

    @Suppress("unused")
    private val resultWarning = "Record only what the official tool showed"

    private fun stopTimingService() {
        stopService(Intent(this, MibuForegroundService::class.java))
    }

    private fun record(state: VerificationState) {
        stopTimingService()
        stateStore.completeVerification(state)
        Log.i(LOG_TAG, "OFFICIAL_RESULT_RECORDED state=${state.name}")
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }

    private fun confirmReset() {
        AlertDialog.Builder(this)
            .setTitle("Reset MIBU workflow?")
            .setMessage("This clears token captures, the active timing target, lane progress and the recorded verification result. Community-device evidence is kept.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Reset") { _, _ ->
                stopTimingService()
                tokenStore.clear()
                stateStore.resetWorkflow()
                Log.i(LOG_TAG, "WORKFLOW_RESET")
                startActivity(Intent(this, MainActivity::class.java))
                finish()
            }
            .show()
    }

    companion object {
        private const val LOG_TAG = "MIBU_RESULT"
    }
}
