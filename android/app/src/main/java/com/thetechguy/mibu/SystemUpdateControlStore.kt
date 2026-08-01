package com.thetechguy.mibu

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.provider.Settings
import java.util.UUID

enum class SystemUpdateAction {
    DISABLE,
    ENABLE,
}

data class SystemUpdateControlState(
    val updaterInstalled: Boolean,
    val updaterEnabled: Boolean,
    val automaticUpdatesDisabled: Boolean,
    val requestId: String,
    val requestedAction: String,
    val resultState: String,
    val resultMessage: String,
) {
    val fullyDisabled: Boolean
        get() = updaterInstalled && !updaterEnabled && automaticUpdatesDisabled

    val fullyEnabled: Boolean
        get() = updaterInstalled && updaterEnabled && !automaticUpdatesDisabled
}

class SystemUpdateControlStore(private val context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun request(action: SystemUpdateAction): String {
        val requestId = "${System.currentTimeMillis()}-${UUID.randomUUID()}"
        prefs.edit()
            .putString(KEY_REQUEST_ID, requestId)
            .putString(KEY_REQUEST_ACTION, action.name)
            .putString(KEY_RESULT_STATE, "PENDING")
            .putString(KEY_RESULT_MESSAGE, "Waiting for MIBU PC Helper")
            .apply()
        return requestId
    }

    fun recordResult(requestId: String, state: String, message: String): Boolean {
        if (requestId.isBlank() || requestId != prefs.getString(KEY_REQUEST_ID, "")) return false
        prefs.edit()
            .putString(KEY_RESULT_STATE, state.take(MAX_STATE))
            .putString(KEY_RESULT_MESSAGE, message.take(MAX_MESSAGE))
            .apply()
        return true
    }

    fun readState(): SystemUpdateControlState {
        @Suppress("DEPRECATION")
        val updater = runCatching {
            context.packageManager.getApplicationInfo(
                UPDATER_PACKAGE,
                PackageManager.MATCH_DISABLED_COMPONENTS or PackageManager.MATCH_UNINSTALLED_PACKAGES,
            )
        }.getOrNull()
        val automaticDisabled = runCatching {
            Settings.Global.getString(context.contentResolver, OTA_AUTO_SETTING) == "1"
        }.getOrDefault(false)
        return SystemUpdateControlState(
            updaterInstalled = updater != null,
            updaterEnabled = updater?.enabled == true && updater.flags and ApplicationInfo.FLAG_INSTALLED != 0,
            automaticUpdatesDisabled = automaticDisabled,
            requestId = prefs.getString(KEY_REQUEST_ID, "").orEmpty(),
            requestedAction = prefs.getString(KEY_REQUEST_ACTION, "").orEmpty(),
            resultState = prefs.getString(KEY_RESULT_STATE, "").orEmpty(),
            resultMessage = prefs.getString(KEY_RESULT_MESSAGE, "").orEmpty(),
        )
    }

    companion object {
        const val UPDATER_PACKAGE = "com.android.updater"
        const val OTA_AUTO_SETTING = "ota_disable_automatic_update"
        private const val PREFS = "mibu_system_update_control"
        private const val KEY_REQUEST_ID = "request_id"
        private const val KEY_REQUEST_ACTION = "request_action"
        private const val KEY_RESULT_STATE = "result_state"
        private const val KEY_RESULT_MESSAGE = "result_message"
        private const val MAX_STATE = 32
        private const val MAX_MESSAGE = 320
    }
}
