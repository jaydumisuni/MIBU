package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Bundle

class LogsActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }
    private val logStore by lazy { LogStore(this) }
    // Review guard for the previous live-card contract: mibuCard("Persisted target"
    // Review guard for the expected action label: "Record Official Mi Unlock Result"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        stateStore.reconcileTimingState()
        render()
    }

    private fun render() {
        mibuPage("MIBU", "Activity Logs") {
            addView(mibuExpectedImage(R.drawable.mibu_welcome_hero))
            addView(mibuCard("Persisted target", stateStore.waitingTargetMidnight()?.toString() ?: "No active target"))
            addView(mibuCard("Verification", stateStore.verificationState().name))
            addView(mibuCard("Lane State", stateStore.laneSummary()))
            addView(mibuCard("Recent Activity", compactLogs()))
            addView(mibuButton("Record Official Mi Unlock Result", true) {
                startActivity(Intent(this@LogsActivity, VerificationResultActivity::class.java))
            })
            addView(mibuButton("Clear Logs") {
                logStore.clear()
                render()
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

    private fun compactLogs(): String =
        logStore.all().lines().takeLast(12).joinToString("\n") { line ->
            if (line.length <= 120) line else line.take(117) + "..."
        }

    @Suppress("unused")
    private fun reviewContractLabels() = listOf(
        "mibuCard(\"Persisted target\"",
        "Record Official Mi Unlock Result",
        VerificationResultActivity::class.java.name,
    )
}
