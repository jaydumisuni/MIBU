package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class MainActivity : Activity() {
    private lateinit var statusText: TextView
    private val tokenStore by lazy { TokenStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        refreshStatus()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(36, 48, 36, 36)
            setBackgroundColor(Color.rgb(7, 10, 18))
        }

        val title = TextView(this).apply {
            text = "MIBU"
            textSize = 36f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        root.addView(title)

        val subtitle = TextView(this).apply {
            text = "Mi Bootloader Unlock Helper"
            textSize = 15f
            setTextColor(Color.rgb(180, 190, 210))
            gravity = Gravity.CENTER
            setPadding(0, 4, 0, 28)
        }
        root.addView(subtitle)

        statusText = TextView(this).apply {
            textSize = 15f
            setTextColor(Color.WHITE)
            setPadding(0, 0, 0, 24)
        }
        root.addView(statusText)

        root.addView(actionButton("Import token pasted from PC") {
            tokenStore.saveSession("dev-placeholder-session")
            refreshStatus()
        })

        root.addView(actionButton("Start waiting service") {
            startService(Intent(this, MibuForegroundService::class.java))
            refreshStatus(extra = "Foreground service started.")
        })

        root.addView(actionButton("Clear saved session") {
            tokenStore.clear()
            refreshStatus(extra = "Saved session cleared.")
        })

        val note = TextView(this).apply {
            text = "Safety note: MIBU is a timing/helper tool for your own Xiaomi account. It must respect official account/device limits and should not bypass ownership checks or rate limits."
            textSize = 13f
            setTextColor(Color.rgb(150, 160, 180))
            setPadding(0, 30, 0, 0)
        }
        root.addView(note)

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)
    }

    private fun actionButton(text: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            setOnClickListener { onClick() }
        }
    }

    private fun refreshStatus(extra: String? = null) {
        val beijing = ZoneId.of("Asia/Shanghai")
        val local = ZoneId.systemDefault()
        val nowChina = ZonedDateTime.now(beijing)
        val targetChina = nowChina.toLocalDate().atTime(23, 59, 58, 600_000_000).atZone(beijing)
            .let { if (it.isBefore(nowChina)) it.plusDays(1) else it }
        val localTarget = targetChina.withZoneSameInstant(local)
        val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss z")
        val session = if (tokenStore.hasSession()) "Session present" else "No session saved"

        statusText.text = buildString {
            appendLine("Status: $session")
            appendLine("Beijing window: ${targetChina.format(fmt)}")
            appendLine("Your local time: ${localTarget.format(fmt)}")
            if (extra != null) appendLine("\n$extra")
        }
    }
}
