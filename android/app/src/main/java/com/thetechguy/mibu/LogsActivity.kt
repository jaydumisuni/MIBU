package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle
import java.time.ZonedDateTime

class LogsActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuPage("MIBU", "Logs / THETECHGUY TOOL") {
            addView(mibuCard("Token setup", tokenStore.getSessionPreview()))
            addView(mibuCard("Four internal slots", tokenStore.getSlotPreview()))
            addView(mibuCard("Lane state", stateStore.laneSummary()))
            addView(mibuCard("Community state", stateStore.communityState().name))
            addView(mibuCard("Verification state", stateStore.verificationState().name))
            addView(mibuCard("Timing", "Opened logs at ${ZonedDateTime.now()}"))
            addView(mibuCard("Reminder", "Logs show local stored state only. Final Mi Unlock result must be confirmed through the PC helper / official Mi Unlock Tool path."))
            addView(mibuButton("Back", true) { finish() })
            addView(footer())
        }
    }
}
