package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle

class CommunityCheckActivity : Activity() {
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        render()
    }

    private fun render() {
        mibuImageHotspotScreen(
            R.drawable.android_settings,
            listOf(
                MibuHotspot(0.03f, 0.03f, 0.12f, 0.07f, "Back") { finish() },
                MibuHotspot(0.09f, 0.515f, 0.82f, 0.065f, "Device confirmed") {
                    stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_DEVICE_CONFIRMED)
                    render()
                },
                MibuHotspot(0.09f, 0.590f, 0.82f, 0.065f, "Device not found") {
                    stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_DEVICE_NOT_FOUND)
                    render()
                },
                MibuHotspot(0.09f, 0.665f, 0.82f, 0.065f, "Route not required") {
                    stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_ROUTE_NOT_REQUIRED)
                    render()
                },
            ),
        )
    }
}
