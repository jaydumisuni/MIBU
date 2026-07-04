package com.thetechguy.mibu

import android.content.Context

class TokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("mibu_session", Context.MODE_PRIVATE)

    fun saveSession(session: String) {
        // Backward-compatible import path. Treat a single pushed value as a service-token capture.
        // TODO: replace with Android Keystore backed storage before production.
        prefs.edit()
            .putString(KEY_LEGACY_SESSION, session)
            .putString(KEY_SERVICE_TOKEN, session)
            .apply()
    }

    fun saveServiceToken(token: String) {
        prefs.edit().putString(KEY_SERVICE_TOKEN, token.trim()).apply()
    }

    fun savePopToken(token: String) {
        prefs.edit().putString(KEY_POP_TOKEN, token.trim()).apply()
    }

    fun saveCaptures(serviceToken: String, popToken: String) {
        prefs.edit()
            .putString(KEY_SERVICE_TOKEN, serviceToken.trim())
            .putString(KEY_POP_TOKEN, popToken.trim())
            .apply()
    }

    fun hasSession(): Boolean = hasServiceToken() || !prefs.getString(KEY_LEGACY_SESSION, null).isNullOrBlank()

    fun hasServiceToken(): Boolean = !prefs.getString(KEY_SERVICE_TOKEN, null).isNullOrBlank()

    fun hasPopToken(): Boolean = !prefs.getString(KEY_POP_TOKEN, null).isNullOrBlank()

    fun hasRequiredCaptures(): Boolean = hasServiceToken() && hasPopToken()

    fun getSessionPreview(): String {
        val service = prefs.getString(KEY_SERVICE_TOKEN, null)
        val pop = prefs.getString(KEY_POP_TOKEN, null)
        return when {
            !service.isNullOrBlank() && !pop.isNullOrBlank() -> "service:${service.length}chars • pop:${pop.length}chars"
            !service.isNullOrBlank() -> "service:${service.length}chars • pop:missing"
            !pop.isNullOrBlank() -> "service:missing • pop:${pop.length}chars"
            else -> "none"
        }
    }

    fun getSlotPreview(): String {
        val serviceReady = if (hasServiceToken()) "Ready" else "Missing"
        val popReady = if (hasPopToken()) "Ready" else "Missing"
        return "Slot 1 Firefox: $serviceReady\nSlot 2 Chrome: $popReady\nSlot 3 Firefox: $serviceReady\nSlot 4 Chrome: $popReady"
    }

    fun getServiceToken(): String? = prefs.getString(KEY_SERVICE_TOKEN, null)

    fun getPopToken(): String? = prefs.getString(KEY_POP_TOKEN, null)

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_LEGACY_SESSION = "session"
        private const val KEY_SERVICE_TOKEN = "service_token"
        private const val KEY_POP_TOKEN = "pop_token"
    }
}
