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
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.time.Duration
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class MainActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }
    private lateinit var root: LinearLayout
    private lateinit var statusCard: TextView
    private lateinit var beijingCard: TextView
    private lateinit var localCard: TextView
    private lateinit var countdownCard: TextView
    private lateinit var sessionCard: TextView
    private lateinit var laneCard: TextView
    private lateinit var verifyCard: TextView
    private lateinit var communityCard: TextView

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

        sessionCard = statusTile("Token Setup", "Waiting for import", "")
        root.addView(sessionCard)

        laneCard = statusTile("Hidden Request Lanes", "Not armed", "One visible countdown. Four lanes are tracked in the background.")
        root.addView(laneCard)

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

        verifyCard = statusTile("Verification", "Not started", "After request stage, verify with Mi Unlock Tool from PC Helper. Settings bind is fallback only.")
        root.addView(verifyCard)

        root.addView(rowTile("Mobile Data Reminder", "Make sure Mobile Data is ON and Wi-Fi/WLAN is OFF.", "Required"))
        communityCard = rowTile("Community Device Check", "For China-routed devices, confirm device/account status in Xiaomi Community if needed.", stateStore.communityState().name)
        root.addView(communityCard)

        root.addView(primaryButton("Start Waiting") {
            startActivity(Intent(this, StartWaitingActivity::class.java))
        })
        root.addView(secondaryButton("Import Firefox + Chrome tokens") {
            startActivity(Intent(this, TokenImportActivity::class.java))
        })
        root.addView(secondaryButton("Community Check") {
            startActivity(Intent(this, CommunityCheckActivity::class.java))
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
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(10), dp(10), dp(10), dp(16))
            background = rounded(Color.rgb(8, 15, 30), dp(24), Color.rgb(32, 55, 90))
        }
        val art = ImageView(this).apply {
            setImageResource(R.drawable.mibu_hero_art)
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.FIT_CENTER
        }
        card.addView(art, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(220)))
        val title = TextView(this).apply {
            text = "Mi Bootloader Unlock Helper\nOne countdown. Four hidden lanes. PC verification."
            textSize = 18f
            gravity = Gravity.CENTER
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            setPadding(dp(12), dp(6), dp(12), 0)
        }
        card.addView(title)
        rootParams(card, bottom = dp(14))
        return card
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
        val targetChina = MibuLane.defaultLanes().first().targetTime(nowChina)
        val localTarget = targetChina.withZoneSameInstant(local)
        val fmtDate = DateTimeFormatter.ofPattern("MMM dd, yyyy")
        val fmtTime = DateTimeFormatter.ofPattern("HH:mm:ss.SSS")
        val duration = Duration.between(ZonedDateTime.now(beijing), targetChina).let { if (it.isNegative) Duration.ZERO else it }
        val hours = duration.toHours()
        val minutes = duration.toMinutesPart()
        val seconds = duration.toSecondsPart()
        val status = if (tokenStore.hasRequiredCaptures()) "Full token setup ready" else if (tokenStore.hasSession()) "Partial token setup" else "Waiting for tokens"
        val session = if (tokenStore.hasSession()) "${tokenStore.getSessionPreview()}\n${tokenStore.getSlotPreview()}" else "Import Firefox service token and Chrome pop token first"

        statusCard.text = formatBlock("Account Status", status, extra ?: "User logs in themselves. MIBU stores only explicit token/session imports.")
        sessionCard.text = formatBlock("Token Setup", session, "Two captures populate four internal slots.")
        laneCard.text = formatBlock("Hidden Request Lanes", stateStore.laneSummary(), "Main UI shows one countdown; advanced lane detail is logged.")
        verifyCard.text = formatBlock("Verification", stateStore.verificationState().name, "PC Helper verifies with Mi Unlock Tool. Settings bind is fallback if account/device is not added.")
        communityCard.text = "Community Device Check\nFor China-routed devices, confirm device/account status in Xiaomi Community if needed.\n[${stateStore.communityState().name}]"
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
