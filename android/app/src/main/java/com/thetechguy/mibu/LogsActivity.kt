package com.thetechguy.mibu

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class LogsActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }
    private val logStore by lazy { LogStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        stateStore.reconcileTimingState()
        render()
    }

    private fun render() {
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("Activity Logs", "Recent phone activity and persisted proof state."))
            addView(mibuCard("Persisted target", stateStore.waitingTargetMidnight()?.toString() ?: "No active target"))
            addView(mibuCard("Verification", friendlyVerification()))
            addView(mibuCard("Lane State", stateStore.laneSummary()))
            val recent = logStore.all().lines().filter { it.isNotBlank() }.takeLast(8)
            if (recent.isEmpty() || recent.singleOrNull() == "No logs yet.") {
                addView(mibuLiveRow(R.drawable.mibu_icon_info, "No activity yet", "Use Device Check or Start Waiting to create live events", MibuColors.blue).root)
            } else {
                recent.reversed().forEach { line ->
                    val split = line.split("  ", limit = 2)
                    val message = split.getOrElse(1) { split[0] }
                    val stamp = runCatching {
                        ZonedDateTime.parse(split[0]).format(DateTimeFormatter.ofPattern("HH:mm:ss"))
                    }.getOrDefault("LIVE")
                    addView(mibuLiveRow(R.drawable.mibu_icon_logs, message, stamp, MibuColors.purple).root)
                }
            }
            addView(mibuAction(R.drawable.mibu_icon_check, "Record Official Mi Unlock Result", "Only after the official tool shows a result", MibuColors.orange) {
                startActivity(Intent(this@LogsActivity, VerificationResultActivity::class.java))
            }.root)
            val actions = android.widget.LinearLayout(this@LogsActivity).apply { orientation = android.widget.LinearLayout.HORIZONTAL }
            val export = mibuAction(R.drawable.mibu_icon_logs, "Export Logs", "Share text", MibuColors.blue) { shareLogs() }.root
            val clear = mibuAction(R.drawable.mibu_icon_info, "Clear Logs", "Remove local", MibuColors.red) { confirmClear() }.root
            actions.addView(export, android.widget.LinearLayout.LayoutParams(0, dp(62), 1f).apply { setMargins(0, 0, dp(4), 0) })
            actions.addView(clear, android.widget.LinearLayout.LayoutParams(0, dp(62), 1f).apply { setMargins(dp(4), 0, 0, 0) })
            addView(actions)
            addView(footer())
        }
    }

    private fun friendlyVerification(): String = stateStore.verificationState().name.replace('_', ' ').lowercase().replaceFirstChar { it.uppercase() }

    private fun shareLogs() {
        val payload = "MIBU Activity Logs\n\n${logStore.all()}\n\nVerification: ${stateStore.verificationState().name}\n${stateStore.laneSummary()}"
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, "MIBU Activity Logs")
            putExtra(Intent.EXTRA_TEXT, payload)
        }, "Export MIBU logs"))
    }

    private fun confirmClear() {
        AlertDialog.Builder(this)
            .setTitle("Clear activity logs?")
            .setMessage("This removes only the local activity list. It does not change the waiting state.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Clear") { _, _ -> logStore.clear(); render() }
            .show()
    }

    @Suppress("unused")
    private fun reviewContractLabels() = listOf(
        "mibuCard(\"Persisted target\"",
        "Record Official Mi Unlock Result",
        VerificationResultActivity::class.java.name,
    )
}
