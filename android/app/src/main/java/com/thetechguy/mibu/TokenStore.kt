package com.thetechguy.mibu

import android.content.Context

class TokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("mibu_session", Context.MODE_PRIVATE)

    fun saveSession(session: String) {
        // TODO: replace with Android Keystore backed storage before production.
        prefs.edit().putString("session", session).apply()
    }

    fun hasSession(): Boolean = !prefs.getString("session", null).isNullOrBlank()

    fun getSessionPreview(): String {
        val value = prefs.getString("session", null) ?: return "none"
        return "saved:${value.length}chars"
    }

    fun clear() {
        prefs.edit().clear().apply()
    }
}
