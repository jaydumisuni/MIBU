package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.provider.Settings

class CommunityCheckActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun render() {
        mibuPage("MIBU", "Settings") {
            addView(mibuExpectedImage(R.drawable.mibu_welcome_hero))
            addView(mibuCard("Current community/device state", stateStore.communityState().name))
            addView(mibuCard("Mobile Data", "Android does not allow a normal app to silently toggle mobile data. This opens the system panel so you can turn it on, then return to MIBU."))
            addView(mibuButton("Open Mobile Data Settings", true) {
                openSystemSettings(Settings.ACTION_DATA_ROAMING_SETTINGS)
            })
            addView(mibuButton("Open Network Settings") {
                openSystemSettings(Settings.ACTION_WIRELESS_SETTINGS)
            })
            addView(mibuButton("Open App Settings") {
                openSystemSettings(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, "package:$packageName")
            })
            addView(mibuCard("Community route", "Record only what you actually see in Xiaomi Community or the official flow."))
            addView(mibuButton("Device Confirmed") {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_DEVICE_CONFIRMED)
                render()
            })
            addView(mibuButton("Device Not Found") {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_DEVICE_NOT_FOUND)
                render()
            })
            addView(mibuButton("Route Not Required") {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_ROUTE_NOT_REQUIRED)
                render()
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

    private fun openSystemSettings(action: String, data: String? = null) {
        val intent = Intent(action).apply {
            if (data != null) setData(android.net.Uri.parse(data))
        }
        startActivity(intent)
    }
}
