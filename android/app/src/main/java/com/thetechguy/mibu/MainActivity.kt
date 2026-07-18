package com.thetechguy.mibu

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle

class MainActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermissionIfNeeded()
        refreshContractState()
        buildUi()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
        }
    }

    private fun buildUi() {
        mibuImageHotspotScreen(
            R.drawable.android_dashboard_waiting,
            listOf(
                MibuHotspot(0.81f, 0.075f, 0.10f, 0.065f, "Settings") {
                    startActivity(Intent(this, CommunityCheckActivity::class.java))
                },
                MibuHotspot(0.10f, 0.285f, 0.80f, 0.070f, "Account session") {
                    startActivity(Intent(this, TokenImportActivity::class.java))
                },
                MibuHotspot(0.10f, 0.365f, 0.80f, 0.070f, "Import session") {
                    startActivity(Intent(this, TokenImportActivity::class.java))
                },
                MibuHotspot(0.10f, 0.815f, 0.80f, 0.075f, "Start Waiting") {
                    startActivity(Intent(this, StartWaitingActivity::class.java))
                },
                MibuHotspot(0.10f, 0.900f, 0.38f, 0.055f, "Open Logs") {
                    startActivity(Intent(this, LogsActivity::class.java))
                },
                MibuHotspot(0.52f, 0.900f, 0.38f, 0.055f, "Instructions") {
                    startActivity(Intent(this, InstructionsActivity::class.java))
                },
            ),
        )
    }

    private fun refreshContractState(): String {
        val nowChina = java.time.ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val verification = stateStore.reconcileTimingState(nowChina)
        val buttonLabel = if (verification == VerificationState.WAITING_ARMED) "Resume Waiting" else "Start Waiting"
        val targetLabel = if (verification.blocksNewWaitingCycle()) "No active target" else friendlyVerification(verification)
        return "$buttonLabel / $targetLabel / ${verificationGuidance(verification)}"
    }

    private fun friendlyVerification(state: VerificationState): String = when (state) {
        VerificationState.NOT_STARTED -> "Not started"
        VerificationState.WAITING_ARMED -> "Waiting armed"
        VerificationState.TIMING_WINDOW_REACHED -> "Timing window reached"
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Ready for Mi Unlock"
        VerificationState.WAIT_TIME_SHOWN -> "Official wait time shown"
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED -> "Account/device not added"
        VerificationState.COMMUNITY_AUTH_REQUIRED -> "Community authorisation required"
        VerificationState.UNLOCKED -> "Unlocked"
        VerificationState.UNKNOWN -> "Unknown - review Logs"
    }

    private fun verificationGuidance(state: VerificationState): String = when (state) {
        VerificationState.TIMING_WINDOW_REACHED,
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Continue with PC Helper and the official Mi Unlock Tool."
        VerificationState.WAIT_TIME_SHOWN -> "Keep the official waiting period; do not restart the timing cycle."
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED -> "Resolve the phone-side account/device association before retrying."
        VerificationState.COMMUNITY_AUTH_REQUIRED -> "Complete the Xiaomi Community authorisation route first."
        VerificationState.UNLOCKED -> "The authoritative result is already complete."
        else -> "No active target"
    }

    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST = 49
    }
}
