package com.thetechguy.mibu

import android.content.Context

class TokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("mibu_session", Context.MODE_PRIVATE)

    fun saveSession(session: String) {
        val clean = session.trim()
        prefs.edit().putString(KEY_LEGACY_SESSION, clean).putString(KEY_SERVICE_TOKEN, clean).putLong(KEY_CAPTURED_AT, System.currentTimeMillis()).apply()
    }

    fun saveServiceToken(token: String) {
        prefs.edit().putString(KEY_SERVICE_TOKEN, token.trim()).putLong(KEY_CAPTURED_AT, System.currentTimeMillis()).apply()
    }

    fun savePopToken(token: String) {
        prefs.edit().putString(KEY_POP_TOKEN, token.trim()).putLong(KEY_CAPTURED_AT, System.currentTimeMillis()).apply()
    }

    fun saveCaptures(serviceToken: String, popToken: String) {
        prefs.edit().putString(KEY_SERVICE_TOKEN, serviceToken.trim()).putString(KEY_POP_TOKEN, popToken.trim()).putLong(KEY_CAPTURED_AT, System.currentTimeMillis()).apply()
    }

    fun hasSession(): Boolean { expireIfStale(); return hasServiceTokenRaw() || !prefs.getString(KEY_LEGACY_SESSION, null).isNullOrBlank() }
    fun hasServiceToken(): Boolean { expireIfStale(); return hasServiceTokenRaw() }
    fun hasPopToken(): Boolean { expireIfStale(); return !prefs.getString(KEY_POP_TOKEN, null).isNullOrBlank() }
    fun hasRequiredCaptures(): Boolean = hasServiceToken() && hasPopToken()

    fun isFresh(): Boolean {
        val capturedAt = prefs.getLong(KEY_CAPTURED_AT, 0L)
        return capturedAt > 0L && System.currentTimeMillis() - capturedAt <= MAX_TOKEN_AGE_MS
    }

    fun minutesRemaining(): Long {
        val capturedAt = prefs.getLong(KEY_CAPTURED_AT, 0L)
        if (capturedAt <= 0L) return 0L
        return ((MAX_TOKEN_AGE_MS - (System.currentTimeMillis() - capturedAt)).coerceAtLeast(0L) + 59_999L) / 60_000L
    }

    fun getSessionPreview(): String {
        expireIfStale()
        val service = prefs.getString(KEY_SERVICE_TOKEN, null)
        val pop = prefs.getString(KEY_POP_TOKEN, null)
        val freshness = if (isFresh()) "${minutesRemaining()} min left" else "expired"
        return when {
            !service.isNullOrBlank() && !pop.isNullOrBlank() -> "service:${service.length}chars • pop:${pop.length}chars • $freshness"
            !service.isNullOrBlank() -> "service:${service.length}chars • pop:missing • $freshness"
            !pop.isNullOrBlank() -> "service:missing • pop:${pop.length}chars • $freshness"
            else -> "none"
        }
    }

    fun getSlotPreview(): String {
        val serviceReady = if (hasServiceToken()) "Ready" else "Missing"
        val popReady = if (hasPopToken()) "Ready" else "Missing"
        return "Slot 1 Firefox: $serviceReady\nSlot 2 Chrome: $popReady\nSlot 3 Firefox: $serviceReady\nSlot 4 Chrome: $popReady"
    }

    fun getServiceToken(): String? { expireIfStale(); return prefs.getString(KEY_SERVICE_TOKEN, null) }
    fun getPopToken(): String? { expireIfStale(); return prefs.getString(KEY_POP_TOKEN, null) }
    fun clear() { prefs.edit().clear().apply() }

    private fun hasServiceTokenRaw(): Boolean = !prefs.getString(KEY_SERVICE_TOKEN, null).isNullOrBlank()
    private fun expireIfStale() {
        val capturedAt = prefs.getLong(KEY_CAPTURED_AT, 0L)
        if (capturedAt > 0L && System.currentTimeMillis() - capturedAt > MAX_TOKEN_AGE_MS) clear()
    }

    companion object {
        private const val KEY_LEGACY_SESSION = "session"
        private const val KEY_SERVICE_TOKEN = "service_token"
        private const val KEY_POP_TOKEN = "pop_token"
        private const val KEY_CAPTURED_AT = "captured_at"
        private const val MAX_TOKEN_AGE_MS = 30L * 60L * 1000L
    }
}
