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
        mibuPage("MIBU", "Official Result / THETECHGUY TOOL") {
            addView(mibuCard(
                "Record only what the official tool showed",
                "Use these buttons only after Mi Unlock or Xiaomi's official account/device route returned the matching result. MIBU does not infer approval from timing, a toast, or fastboot presence."
            ))
            addView(mibuCard("Current verification state", stateStore.verificationState().name))
            addView(mibuButton("Official wait time shown", true) {
                record(VerificationState.WAIT_TIME_SHOWN)
            })
            addView(mibuButton("Account/device not added") {
                record(VerificationState.ACCOUNT_DEVICE_NOT_ADDED)
            })
            addView(mibuButton("Community authorisation required") {
                record(VerificationState.COMMUNITY_AUTH_REQUIRED)
            })
            addView(mibuButton("Device unlocked") {
                record(VerificationState.UNLOCKED)
            })
            addView(mibuButton("Reset workflow for a fresh authorised attempt") {
                confirmReset()
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

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
