package com.thetechguy.mibu

import android.content.Context
import java.time.ZonedDateTime

class LogStore(context: Context) {
    private val prefs = context.getSharedPreferences("mibu_logs", Context.MODE_PRIVATE)

    fun add(message: String) {
        val current = prefs.getString("events", "") ?: ""
        val line = "${ZonedDateTime.now()}  $message"
        val next = (current + "\n" + line).trim().lines().takeLast(80).joinToString("\n")
        prefs.edit().putString("events", next).apply()
    }

    fun all(): String = prefs.getString("events", "")?.ifBlank { "No logs yet." } ?: "No logs yet."

    fun clear() {
        prefs.edit().clear().apply()
    }
}
