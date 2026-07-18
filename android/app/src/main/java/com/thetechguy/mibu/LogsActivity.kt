package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import java.time.ZonedDateTime

class LogsActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        stateStore.reconcileTimingState()
        val target = stateStore.waitingTargetMidnight()
        mibuPage("MIBU", "Logs / THETECHGUY TOOL") {
            addView(mibuExpectedImage(R.drawable.android_activity_logs))
            addView(mibuCard("Token setup", tokenStore.getSessionPreview()))
            addView(mibuCard("Four internal slots", tokenStore.getSlotPreview()))
            addView(mibuCard("Persisted target", target?.toString() ?: "No waiting target armed"))
            addView(mibuCard("Lane state", stateStore.laneSummary()))
            addView(mibuCard("Community state", stateStore.communityState().name))
            addView(mibuCard("Verification state", stateStore.verificationState().name))
            addView(mibuCard("Timing", "Opened logs at ${ZonedDateTime.now()}"))
            addView(mibuCard("Reminder", "Logs show local stored state only. Final Mi Unlock result must be confirmed through the PC helper / official Mi Unlock Tool path."))
            addView(mibuButton("Record Official Mi Unlock Result", true) {
                startActivity(Intent(this@LogsActivity, VerificationResultActivity::class.java))
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }
}
