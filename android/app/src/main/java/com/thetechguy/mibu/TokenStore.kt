package com.thetechguy.mibu

import android.content.Context

class TokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("mibu_session", Context.MODE_PRIVATE)

    fun saveSession(session: String) {
        val clean = normalizeToken(session)
        val now = System.currentTimeMillis()
        prefs.edit()
            .putString(KEY_LEGACY_SESSION, clean)
            .putString(KEY_SERVICE_TOKEN, clean)
            .putLong(KEY_SERVICE_CAPTURED_AT, now)
            .apply()
    }

    fun saveServiceToken(token: String) {
        val clean = normalizeToken(token)
        prefs.edit()
            .putString(KEY_SERVICE_TOKEN, clean)
            .putLong(KEY_SERVICE_CAPTURED_AT, System.currentTimeMillis())
            .apply()
    }

    fun savePopToken(token: String) {
        val clean = normalizeToken(token)
        prefs.edit()
            .putString(KEY_POP_TOKEN, clean)
            .putLong(KEY_POP_CAPTURED_AT, System.currentTimeMillis())
            .apply()
    }

    fun saveCaptures(serviceToken: String, popToken: String) {
        val cleanService = normalizeToken(serviceToken)
        val cleanPop = normalizeToken(popToken)
        val now = System.currentTimeMillis()
        prefs.edit()
            .putString(KEY_SERVICE_TOKEN, cleanService)
            .putString(KEY_POP_TOKEN, cleanPop)
            .putLong(KEY_SERVICE_CAPTURED_AT, now)
            .putLong(KEY_POP_CAPTURED_AT, now)
            .apply()
    }

    fun hasSession(): Boolean {
        expireStaleCaptures()
        return hasServiceTokenRaw() || !prefs.getString(KEY_LEGACY_SESSION, null).isNullOrBlank()
    }

    fun hasServiceToken(): Boolean {
        expireStaleCaptures()
        return hasServiceTokenRaw()
    }

    fun hasPopToken(): Boolean {
        expireStaleCaptures()
        return hasPopTokenRaw()
    }

    fun hasRequiredCaptures(): Boolean = hasServiceToken() && hasPopToken()

    fun serviceMillisRemaining(nowMs: Long = System.currentTimeMillis()): Long =
        remainingFor(KEY_SERVICE_CAPTURED_AT, nowMs)

    fun popMillisRemaining(nowMs: Long = System.currentTimeMillis()): Long =
        remainingFor(KEY_POP_CAPTURED_AT, nowMs)

    fun millisRemaining(nowMs: Long = System.currentTimeMillis()): Long {
        expireStaleCaptures(nowMs)
        if (!hasServiceTokenRaw() || !hasPopTokenRaw()) return 0L
        return minOf(serviceMillisRemaining(nowMs), popMillisRemaining(nowMs))
    }

    fun isFresh(): Boolean = millisRemaining() > 0L

    fun minutesRemaining(): Long = (millisRemaining() + 59_999L) / 60_000L

    fun getSessionPreview(): String {
        expireStaleCaptures()
        val service = prefs.getString(KEY_SERVICE_TOKEN, null)
        val pop = prefs.getString(KEY_POP_TOKEN, null)
        val freshness = if (hasRequiredCaptures()) "${minutesRemaining()} min minimum freshness" else "incomplete"
        return when {
            !service.isNullOrBlank() && !pop.isNullOrBlank() -> "service:${service.length}chars • pop:${pop.length}chars • $freshness"
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

    fun getServiceToken(): String? {
        expireStaleCaptures()
        return normalizedStoredToken(KEY_SERVICE_TOKEN, KEY_SERVICE_CAPTURED_AT, KEY_LEGACY_SESSION)
    }

    fun getPopToken(): String? {
        expireStaleCaptures()
        return normalizedStoredToken(KEY_POP_TOKEN, KEY_POP_CAPTURED_AT)
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    private fun hasServiceTokenRaw(): Boolean = !prefs.getString(KEY_SERVICE_TOKEN, null).isNullOrBlank()
    private fun hasPopTokenRaw(): Boolean = !prefs.getString(KEY_POP_TOKEN, null).isNullOrBlank()

    private fun remainingFor(timestampKey: String, nowMs: Long): Long =
        remainingMillis(prefs.getLong(timestampKey, 0L), nowMs)

    private fun expireStaleCaptures(nowMs: Long = System.currentTimeMillis()) {
        val edit = prefs.edit()
        var changed = false
        if (hasServiceTokenRaw() && serviceMillisRemaining(nowMs) <= 0L) {
            edit.remove(KEY_SERVICE_TOKEN).remove(KEY_SERVICE_CAPTURED_AT).remove(KEY_LEGACY_SESSION)
            changed = true
        }
        if (hasPopTokenRaw() && popMillisRemaining(nowMs) <= 0L) {
            edit.remove(KEY_POP_TOKEN).remove(KEY_POP_CAPTURED_AT)
            changed = true
        }
        if (changed) edit.apply()
    }

    private fun normalizedStoredToken(tokenKey: String, timestampKey: String, legacyKey: String? = null): String? {
        val stored = prefs.getString(tokenKey, null) ?: return null
        val compact = compactToken(stored)
        if (!isAcceptableToken(compact)) {
            val edit = prefs.edit().remove(tokenKey).remove(timestampKey)
            if (legacyKey != null) edit.remove(legacyKey)
            edit.apply()
            return null
        }
        if (compact != stored) {
            val edit = prefs.edit().putString(tokenKey, compact)
            if (legacyKey != null) edit.putString(legacyKey, compact)
            edit.apply()
        }
        return compact
    }

    private fun normalizeToken(value: String): String {
        val clean = compactToken(value)
        require(isAcceptableToken(clean)) { "Token capture is malformed or outside the accepted size range" }
        return clean
    }

    companion object {
        private const val KEY_LEGACY_SESSION = "session"
        private const val KEY_SERVICE_TOKEN = "service_token"
        private const val KEY_POP_TOKEN = "pop_token"
        private const val KEY_SERVICE_CAPTURED_AT = "service_captured_at"
        private const val KEY_POP_CAPTURED_AT = "pop_captured_at"
        const val MIN_TOKEN_LENGTH = 8
        const val MAX_TOKEN_LENGTH = 8_192
        const val MAX_TOKEN_AGE_MS = 30L * 60L * 1000L

        fun compactToken(value: String): String =
            value.trim().filterNot { it.isWhitespace() }

        fun isAcceptableToken(value: String): Boolean {
            val clean = compactToken(value)
            return clean.length in MIN_TOKEN_LENGTH..MAX_TOKEN_LENGTH && clean.none { it.isISOControl() }
        }

        fun remainingMillis(capturedAtMs: Long, nowMs: Long): Long {
            if (capturedAtMs <= 0L) return 0L
            val ageMs = nowMs - capturedAtMs
            // A wall-clock rollback must never extend a sensitive capture's lifetime.
            if (ageMs < 0L) return 0L
            return (MAX_TOKEN_AGE_MS - ageMs).coerceIn(0L, MAX_TOKEN_AGE_MS)
        }
    }
}
