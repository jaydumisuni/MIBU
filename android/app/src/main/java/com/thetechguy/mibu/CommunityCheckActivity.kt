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
        mibuPage("MIBU", "Community Device Check / THETECHGUY TOOL") {
            addView(mibuCard("Why this exists", "For China-routed or Community-routed Xiaomi devices, manually checking whether the same Xiaomi account/device appears in Xiaomi Community may be useful evidence. This is not treated as a guaranteed blocker."))
            addView(mibuCard("Current state", stateStore.communityState().name))
            addView(mibuCard("Manual check", "Open Xiaomi Community with the same Xiaomi account, then check My Devices / device area. Come back here and save what you saw."))
            addView(mibuButton("Device confirmed in Community", true) {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_DEVICE_CONFIRMED)
                render()
            })
            addView(mibuButton("Device not found") {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_DEVICE_NOT_FOUND)
                render()
            })
            addView(mibuButton("Community route not required") {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_ROUTE_NOT_REQUIRED)
                render()
            })
            addView(mibuButton("Unknown / skip for now") {
                stateStore.setCommunityState(CommunityDeviceState.COMMUNITY_ROUTE_UNKNOWN)
                render()
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }
}
