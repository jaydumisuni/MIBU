package com.thetechguy.mibu

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast

class UnlockMethodsActivity : Activity() {
    private val logStore by lazy { LogStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("Mi Unlock & Binding", "Use Xiaomi's live result to choose the correct next method."))

            addView(mibuSection("Method 1 - Official Xiaomi"))
            addView(mibuAction(R.drawable.mibu_icon_check, "Open Mi Unlock Status", "Tap Add account and device inside Xiaomi Settings", MibuColors.green, true) {
                openMiUnlockStatus()
            }.root)
            addView(mibuCard("Before binding", "Keep the Xiaomi SIM inserted, disable Wi-Fi, enable mobile data, use the same Xiaomi account, and keep OEM unlocking enabled."))

            addView(mibuSection("Method 2 - Binding Recovery"))
            addView(mibuLiveRow(R.drawable.mibu_icon_info, "If Xiaomi says Couldn't add", "Treat it as a Community/account gate, not success", MibuColors.orange, "RECOVERY").root)
            addView(mibuAction(R.drawable.mibu_icon_account, "Open Xiaomi Community", "Check authorization and the account/device route", MibuColors.orange) {
                openUrl("https://c.mi.com/global/")
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_signal, "Check mobile network", "Open Android network settings", MibuColors.green) {
                openNetworkSettings()
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_check, "Record Official Result", "Save only what Xiaomi Settings or Mi Unlock showed", MibuColors.purple) {
                startActivity(Intent(this@UnlockMethodsActivity, VerificationResultActivity::class.java))
            }.root)

            addView(mibuSection("Method 3 - Legacy Compatibility"))
            addView(mibuCard("PC compatibility check required", "Older HyperSploit-style binding recovery worked only on specific unpatched Settings/HyperOS builds. MIBU PC Helper must identify the build before presenting any advanced action. It is never part of automatic One Click."))
            addView(mibuAction(R.drawable.mibu_icon_guide, "Open Recovery Instructions", "Review eligibility, risks and the official verification handoff", MibuColors.blue) {
                startActivity(Intent(this@UnlockMethodsActivity, InstructionsActivity::class.java))
            }.root)
            addView(footer())
        }
    }

    private fun openMiUnlockStatus() {
        val intents = listOf(
            Intent().setComponent(ComponentName("com.android.settings", "com.android.settings.MiuiUnlockStatusActivity")),
            Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS),
        )
        for (candidate in intents) {
            val opened = runCatching { startActivity(candidate); true }.getOrDefault(false)
            if (opened) {
                logStore.add("Opened Xiaomi Mi Unlock Status / Developer Options")
                return
            }
        }
        Toast.makeText(this, "Open Developer options, then Mi Unlock status.", Toast.LENGTH_LONG).show()
        logStore.add("Mi Unlock Status activity was not exposed by this Settings build")
    }

    private fun openNetworkSettings() {
        val opened = runCatching { startActivity(Intent(Settings.ACTION_DATA_ROAMING_SETTINGS)); true }.getOrDefault(false)
        if (!opened) startActivity(Intent(Settings.ACTION_WIRELESS_SETTINGS))
    }

    private fun openUrl(url: String) {
        runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
            .onFailure { Toast.makeText(this, "No browser is available.", Toast.LENGTH_LONG).show() }
    }
}
