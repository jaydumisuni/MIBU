package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle
import java.time.ZonedDateTime

class LogsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuPage("MIBU", "Logs / THETECHGUY TOOL") {
            addView(mibuCard("Session", "No real session logs yet. The secure import path comes before device testing."))
            addView(mibuCard("Foreground service", "Service events will appear here after the waiting helper is started."))
            addView(mibuCard("Timing", "Opened logs at ${ZonedDateTime.now()}"))
            addView(mibuCard("Build stage", "Visual shell first, wiring second, testing last."))
            addView(mibuButton("Back", true) { finish() })
            addView(footer())
        }
    }
}
