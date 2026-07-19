package com.thetechguy.mibu

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.util.Log

class VerificationResultActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }
    private val logStore by lazy { LogStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun render() {
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("Official Result", "Record only what the official tool showed. Choosing a result stops the phone timer."))
            addView(mibuAction(R.drawable.mibu_icon_clock, "Official wait time shown", "Keep the waiting period; do not restart", MibuColors.purple) {
                record(VerificationState.WAIT_TIME_SHOWN)
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_info, "Account/device not added", "Resolve the phone association before retrying", MibuColors.red) {
                record(VerificationState.ACCOUNT_DEVICE_NOT_ADDED)
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_account, "Community authorisation required", "Complete the official community route", MibuColors.orange) {
                record(VerificationState.COMMUNITY_AUTH_REQUIRED)
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_check, "Device unlocked", "Use only after official unlock confirmation", MibuColors.green) {
                record(VerificationState.UNLOCKED)
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_info, "Reset workflow", "Clear captures, target, lanes and recorded result", MibuColors.red) { confirmReset() }.root)
            addView(footer())
        }
    }

    @Suppress("unused")
    private val resultWarning = "Record only what the official tool showed"

    private fun stopTimingService() {
        stopService(Intent(this, MibuForegroundService::class.java))
    }

    private fun record(state: VerificationState) {
        stopTimingService()
        stateStore.completeVerification(state)
        logStore.add("Official result recorded: ${state.name}")
        Log.i(LOG_TAG, "OFFICIAL_RESULT_RECORDED state=${state.name}")
        startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
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
                logStore.add("Workflow reset from official result screen")
                Log.i(LOG_TAG, "WORKFLOW_RESET")
                startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
                finish()
            }
            .show()
    }

    companion object {
        private const val LOG_TAG = "MIBU_RESULT"
    }
}
