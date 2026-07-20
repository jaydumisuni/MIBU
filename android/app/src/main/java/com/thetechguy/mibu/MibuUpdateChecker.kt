package com.thetechguy.mibu

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

object MibuUpdateChecker {
    private const val LATEST_RELEASE_API = "https://api.github.com/repos/jaydumisuni/MIBU/releases/latest"
    private const val RELEASES_URL = "https://github.com/jaydumisuni/MIBU/releases/latest"
    private val executor = Executors.newSingleThreadExecutor()

    fun check(activity: Activity) {
        executor.execute {
            val latest = runCatching { latestVersion() }.getOrNull() ?: return@execute
            if (!isNewer(latest, BuildConfig.VERSION_NAME)) return@execute
            activity.runOnUiThread {
                if (activity.isFinishing || activity.isDestroyed) return@runOnUiThread
                AlertDialog.Builder(activity)
                    .setTitle("MIBU update available")
                    .setMessage("Version $latest is available. Update the PC helper and reinstall its bundled APK together.")
                    .setNegativeButton("Later", null)
                    .setPositiveButton("Open release") { _, _ ->
                        activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(RELEASES_URL)))
                    }
                    .show()
            }
        }
    }

    private fun latestVersion(): String? {
        val connection = (URL(LATEST_RELEASE_API).openConnection() as HttpURLConnection).apply {
            connectTimeout = 4_000
            readTimeout = 6_000
            setRequestProperty("Accept", "application/vnd.github+json")
            setRequestProperty("User-Agent", "MIBU-Android/${BuildConfig.VERSION_NAME}")
        }
        return try {
            if (connection.responseCode !in 200..299) return null
            val raw = connection.inputStream.bufferedReader().use { it.readText() }
            JSONObject(raw).optString("tag_name").trim().removePrefix("v").ifBlank { null }
        } finally {
            connection.disconnect()
        }
    }

    internal fun isNewer(latest: String, current: String): Boolean {
        fun parts(value: String): List<Int> = value.removePrefix("v").substringBefore('-')
            .split('.').map { it.toIntOrNull() ?: 0 }
        val left = parts(latest)
        val right = parts(current)
        val count = maxOf(left.size, right.size)
        return (0 until count).firstNotNullOfOrNull { index ->
            val difference = left.getOrElse(index) { 0 }.compareTo(right.getOrElse(index) { 0 })
            difference.takeIf { it != 0 }
        }?.let { it > 0 } ?: false
    }
}
