package com.thetechguy.mibu

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.LinearLayout
import android.widget.Toast
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class CommunityCheckActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }
    private val tokenStore by lazy { TokenStore(this) }
    private val logStore by lazy { LogStore(this) }
    private val preferences by lazy { getSharedPreferences("mibu_ui_settings", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun render() {
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("Settings", "Live controls for session, alerts, time, mobile data guidance and service behavior."))

            addView(mibuSection("Session & Token"))
            addView(mibuAction(R.drawable.mibu_icon_session, "Session & Token", tokenSummary(), MibuColors.orange) {
                startActivity(Intent(this@CommunityCheckActivity, TokenImportActivity::class.java))
            }.root)
            val sessionButtons = LinearLayout(this@CommunityCheckActivity).apply { orientation = LinearLayout.HORIZONTAL }
            val replace = mibuAction(R.drawable.mibu_icon_account, "Replace Session", "Import fresh", MibuColors.orange) {
                startActivity(Intent(this@CommunityCheckActivity, TokenImportActivity::class.java))
            }.root
            val clear = mibuAction(R.drawable.mibu_icon_info, "Clear Session", "Remove saved", MibuColors.red) { confirmClearSession() }.root
            sessionButtons.addView(replace, LinearLayout.LayoutParams(0, dp(62), 1f).apply { setMargins(0, 0, dp(4), 0) })
            sessionButtons.addView(clear, LinearLayout.LayoutParams(0, dp(62), 1f).apply { setMargins(dp(4), 0, 0, 0) })
            addView(sessionButtons)

            addView(mibuSection("Notifications & Alerts"))
            addView(mibuToggle("Sound Alerts", "Play a sound when attention is needed", setting("sound", true), MibuColors.purple) { save("sound", it) })
            addView(mibuToggle("Completion Vibrate", "Vibrate when a waiting lane completes", setting("vibrate", true), MibuColors.purple) { save("vibrate", it) })

            addView(mibuSection("Beijing Time Sync"))
            addView(mibuToggle("Sync with Beijing Time", "Refresh the live conversion every second", setting("sync", true), MibuColors.blue) { save("sync", it) })
            val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
            val local = nowChina.withZoneSameInstant(ZoneId.systemDefault())
            addView(mibuLiveRow(R.drawable.mibu_icon_clock, "Local Time Conversion", local.format(DateTimeFormatter.ofPattern("HH:mm:ss  z")), MibuColors.purple).root)

            addView(mibuSection("Network"))
            addView(mibuAction(R.drawable.mibu_icon_signal, "Mobile Data Reminder", "Open Xiaomi network settings and confirm mobile data", MibuColors.green, true) {
                openSystemSettings(Settings.ACTION_DATA_ROAMING_SETTINGS)
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_signal, "Internet Panel", "Choose mobile data or Wi-Fi", MibuColors.green) {
                val action = if (android.os.Build.VERSION.SDK_INT >= 29) Settings.Panel.ACTION_INTERNET_CONNECTIVITY else Settings.ACTION_WIRELESS_SETTINGS
                openSystemSettings(action)
            }.root)

            addView(mibuSection("Foreground Service"))
            addView(mibuToggle("Foreground Service", "Keep the armed timer running in the background", stateStore.verificationState() == VerificationState.WAITING_ARMED, MibuColors.blue) { enabled ->
                if (enabled) {
                    startActivity(Intent(this@CommunityCheckActivity, StartWaitingActivity::class.java))
                } else {
                    stopService(Intent(this@CommunityCheckActivity, MibuForegroundService::class.java))
                    logStore.add("Foreground service stopped from Settings")
                }
            })

            addView(mibuSection("Community Device State"))
            addView(mibuAction(R.drawable.mibu_icon_check, "Mi Unlock & Binding", "Open Mi Unlock Status and recovery methods", MibuColors.orange, true) {
                startActivity(Intent(this@CommunityCheckActivity, UnlockMethodsActivity::class.java))
            }.root)
            addView(mibuLiveRow(R.drawable.mibu_icon_check, "Current state", friendlyCommunityState(), MibuColors.cyan).root)
            val communityButtons = LinearLayout(this@CommunityCheckActivity).apply { orientation = LinearLayout.HORIZONTAL }
            communityButtons.addView(mibuButton("Confirmed") { updateCommunity(CommunityDeviceState.COMMUNITY_DEVICE_CONFIRMED) }, LinearLayout.LayoutParams(0, dp(52), 1f).apply { setMargins(0, 0, dp(3), dp(8)) })
            communityButtons.addView(mibuButton("Not Found") { updateCommunity(CommunityDeviceState.COMMUNITY_DEVICE_NOT_FOUND) }, LinearLayout.LayoutParams(0, dp(52), 1f).apply { setMargins(dp(3), 0, dp(3), dp(8)) })
            communityButtons.addView(mibuButton("Not Required") { updateCommunity(CommunityDeviceState.COMMUNITY_ROUTE_NOT_REQUIRED) }, LinearLayout.LayoutParams(0, dp(52), 1f).apply { setMargins(dp(3), 0, 0, dp(8)) })
            addView(communityButtons)

            addView(mibuSection("App"))
            addView(mibuAction(R.drawable.mibu_icon_settings, "Open App Settings", "Permissions, battery and notifications", MibuColors.blue) {
                openSystemSettings(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, "package:$packageName")
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_info, "Reset Workflow", "Clear waiting state and recorded result", MibuColors.red) { confirmReset() }.root)
            addView(mibuLiveRow(R.drawable.mibu_icon_info, "About MIBU", "Version ${BuildConfig.VERSION_NAME} - THETECHGUY TOOL", MibuColors.blue, "LIVE").root)
            addView(footer())
        }
    }

    private fun tokenSummary(): String = when {
        tokenStore.hasRequiredCaptures() -> "Two approved captures ready"
        tokenStore.hasSession() -> "Partial capture - import the second token"
        else -> "No active session"
    }

    private fun setting(name: String, default: Boolean): Boolean = preferences.getBoolean(name, default)

    private fun save(name: String, value: Boolean) {
        preferences.edit().putBoolean(name, value).apply()
        logStore.add("Setting changed: $name=$value")
    }

    private fun updateCommunity(state: CommunityDeviceState) {
        stateStore.setCommunityState(state)
        logStore.add("Community device state: ${state.name}")
        render()
    }

    private fun friendlyCommunityState(): String = when (stateStore.communityState()) {
        CommunityDeviceState.COMMUNITY_DEVICE_CONFIRMED -> "Device confirmed"
        CommunityDeviceState.COMMUNITY_DEVICE_NOT_FOUND -> "Device not found"
        CommunityDeviceState.COMMUNITY_ROUTE_NOT_REQUIRED -> "Community route not required"
        CommunityDeviceState.COMMUNITY_ROUTE_UNKNOWN -> "Not checked"
    }

    private fun confirmClearSession() {
        AlertDialog.Builder(this)
            .setTitle("Clear saved session?")
            .setMessage("This removes both approved captures from MIBU on this phone.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Clear") { _, _ ->
                tokenStore.clear()
                logStore.add("Saved session cleared")
                render()
            }
            .show()
    }

    private fun confirmReset() {
        AlertDialog.Builder(this)
            .setTitle("Reset MIBU workflow?")
            .setMessage("This stops the service and clears the timer, lane state, saved captures and recorded verification result.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Reset") { _, _ ->
                stopService(Intent(this, MibuForegroundService::class.java))
                tokenStore.clear()
                stateStore.resetWorkflow()
                logStore.add("Workflow reset from Settings")
                Toast.makeText(this, "MIBU workflow reset", Toast.LENGTH_SHORT).show()
                startActivity(Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP))
                finish()
            }
            .show()
    }

    private fun openSystemSettings(action: String, data: String? = null) {
        val intent = Intent(action).apply { if (data != null) this.data = Uri.parse(data) }
        runCatching { startActivity(intent) }
            .onFailure { startActivity(Intent(Settings.ACTION_WIRELESS_SETTINGS)) }
    }
}
