package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.time.Duration
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class MainActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private lateinit var root: LinearLayout
    private lateinit var statusCard: TextView
    private lateinit var beijingCard: TextView
    private lateinit var localCard: TextView
    private lateinit var countdownCard: TextView
    private lateinit var sessionCard: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        if (::statusCard.isInitialized) refreshStatus()
    }

    private fun buildUi() {
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(22), dp(28), dp(22), dp(24))
            setBackgroundColor(Color.rgb(5, 9, 19))
        }

        val scroll = ScrollView(this)
        scroll.addView(root)
        setContentView(scroll)

        root.addView(headerBlock())
        root.addView(heroBlock())

        statusCard = statusTile("Account Status", "Checking...", "")
        root.addView(statusCard)

        sessionCard = statusTile("Session Imported", "Waiting for PC helper", "")
        root.addView(sessionCard)

        val timeRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        beijingCard = miniTile("Target Time (Beijing)", "-")
        localCard = miniTile("Target Time (Local)", "-")
        timeRow.addView(beijingCard, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(0, 0, dp(6), 0) })
        timeRow.addView(localCard, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(dp(6), 0, 0, 0) })
        root.addView(timeRow)

        countdownCard = statusTile("Time Remaining", "-- : -- : --", "HOURS   MINUTES   SECONDS")
        root.addView(countdownCard)

        root.addView(rowTile("Mobile Data Reminder", "Make sure Mobile Data is ON.", "Recommended"))
        root.addView(rowTile("Foreground Service", "Background helper is active when started.", "Ready"))

        root.addView(primaryButton("Start Waiting") {
            startService(Intent(this, MibuForegroundService::class.java))
            refreshStatus("Foreground service started.")
        })
        root.addView(secondaryButton("Import session/token from PC") {
            startActivity(Intent(this, TokenImportActivity::class.java))
        })
        root.addView(secondaryButton("Open Logs") {
            startActivity(Intent(this, LogsActivity::class.java))
        })
        root.addView(secondaryButton("Instructions") {
            startActivity(Intent(this, InstructionsActivity::class.java))
        })

        val footer = TextView(this).apply {
            text = "By the THETECHGUY TOOL team"
            textSize = 13f
            setTextColor(Color.rgb(145, 160, 190))
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, dp(8))
        }
        root.addView(footer)
    }

    private fun headerBlock(): View {
        val wrap = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(0, dp(8), 0, dp(12))
        }
        val logo = TextView(this).apply {
            text = "MIBU"
            textSize = 40f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(255, 255, 255))
            gravity = Gravity.CENTER
        }
        val sub = TextView(this).apply {
            text = "THETECHGUY TOOL"
            textSize = 13f
            setTextColor(Color.rgb(145, 160, 190))
            gravity = Gravity.CENTER
        }
        wrap.addView(logo)
        wrap.addView(sub)
        return wrap
    }

    private fun heroBlock(): View {
        val hero = TextView(this).apply {
            text = "MI  👻  BU\nMi Bootloader Unlock Helper\nPhone-side helper for Xiaomi bootloader unlock."
            textSize = 22f
            gravity = Gravity.CENTER
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            setPadding(dp(18), dp(26), dp(18), dp(26))
            background = rounded(Color.rgb(8, 15, 30), dp(24), Color.rgb(32, 55, 90))
        }
        rootParams(hero, bottom = dp(14))
        return hero
    }

    private fun statusTile(title: String, main: String, small: String): TextView {
        return TextView(this).apply {
            text = formatBlock(title, main, small)
            textSize = 15f
            setTextColor(Color.WHITE)
            setPadding(dp(18), dp(15), dp(18), dp(15))
            background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
            rootParams(this, bottom = dp(12))
        }
    }

    private fun miniTile(title: String, value: String): TextView {
        return TextView(this).apply {
            text = "$title\n$value"
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(dp(14), dp(14), dp(14), dp(14))
            background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
        }
    }

    private fun rowTile(title: String, desc: String, badge: String): TextView {
        return TextView(this).apply {
            text = "$title\n$desc\n[$badge]"
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(dp(18), dp(14), dp(18), dp(14))
            background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
            rootParams(this, bottom = dp(10))
        }
    }

    private fun primaryButton(text: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            textSize = 16f
            setTextColor(Color.WHITE)
            background = rounded(Color.rgb(30, 88, 255), dp(14), Color.rgb(75, 114, 255))
            setOnClickListener { onClick() }
            rootParams(this, bottom = dp(10))
        }
    }

    private fun secondaryButton(text: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            this.text = text
            textSize = 15f
            setTextColor(Color.WHITE)
            background = rounded(Color.rgb(14, 23, 40), dp(14), Color.rgb(40, 66, 106))
            setOnClickListener { onClick() }
            rootParams(this, bottom = dp(10))
        }
    }

    private fun refreshStatus(extra: String? = null) {
        val beijing = ZoneId.of("Asia/Shanghai")
        val local = ZoneId.systemDefault()
        val nowChina = ZonedDateTime.now(beijing)
        val targetChina = nowChina.toLocalDate().atTime(23, 59, 58, 600_000_000).atZone(beijing)
            .let { if (it.isBefore(nowChina)) it.plusDays(1) else it }
        val localTarget = targetChina.withZoneSameInstant(local)
        val fmtDate = DateTimeFormatter.ofPattern("MMM dd, yyyy")
        val fmtTime = DateTimeFormatter.ofPattern("HH:mm:ss.SSS")
        val duration = Duration.between(ZonedDateTime.now(beijing), targetChina).coerceAtLeast(Duration.ZERO)
        val hours = duration.toHours()
        val minutes = duration.toMinutesPart()
        val seconds = duration.toSecondsPart()
        val status = if (tokenStore.hasSession()) "Session/token ready" else "Waiting for session/token"
        val session = if (tokenStore.hasSession()) "Imported by user\n${tokenStore.getSessionPreview()}" else "Import from PC helper first"

        statusCard.text = formatBlock("Account Status", status, extra ?: "User logs in themselves; MIBU only stores the explicit token/session import.")
        sessionCard.text = formatBlock("Session Imported", session, "")
        beijingCard.text = "Target Time (Beijing)\n${targetChina.format(fmtDate)}\n${targetChina.format(fmtTime)}\nGMT+8 China Standard Time"
        localCard.text = "Target Time (Local)\n${localTarget.format(fmtDate)}\n${localTarget.format(fmtTime)}\n${local.id}"
        countdownCard.text = formatBlock("Time Remaining", "%02d : %02d : %02d".format(hours, minutes, seconds), "HOURS   MINUTES   SECONDS")
    }

    private fun formatBlock(title: String, main: String, small: String): String {
        return if (small.isBlank()) "$title\n$main" else "$title\n$main\n$small"
    }

    private fun rounded(color: Int, radius: Int, stroke: Int): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color)
            cornerRadius = radius.toFloat()
            setStroke(dp(1), stroke)
        }
    }

    private fun rootParams(view: View, bottom: Int = 0) {
        view.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            setMargins(0, 0, 0, bottom)
        }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
