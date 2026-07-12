package com.thetechguy.mibu

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
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
    private val uiHandler = Handler(Looper.getMainLooper())
    private val ticker = object : Runnable {
        override fun run() {
            if (::countdownCard.isInitialized) refreshStatus()
            uiHandler.postDelayed(this, 1000L)
        }
    }

    private lateinit var root: LinearLayout
    private lateinit var statusCard: TextView
    private lateinit var beijingCard: TextView
    private lateinit var localCard: TextView
    private lateinit var countdownCard: TextView
    private lateinit var sessionCard: TextView
    private lateinit var laneCard: TextView
    private lateinit var verifyCard: TextView
    private lateinit var communityCard: TextView
    private lateinit var startWaitingButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        requestNotificationPermissionIfNeeded()
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        uiHandler.removeCallbacks(ticker)
        uiHandler.post(ticker)
    }

    override fun onPause() {
        uiHandler.removeCallbacks(ticker)
        super.onPause()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
        }
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
        sessionCard = statusTile("Token Setup", "Waiting for import", "")
        laneCard = statusTile("Waiting Engine", "Not armed", "Four timing-window lanes run silently in the background.")
        root.addView(statusCard)
        root.addView(sessionCard)
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
        verifyCard = statusTile("Verification", "Not started", "After the timing window is reached, verify with Mi Unlock Tool from PC Helper. Settings bind is fallback only.")
        root.addView(countdownCard)
        root.addView(verifyCard)
        root.addView(rowTile("Mobile Data Reminder", "Make sure Mobile Data is ON and Wi-Fi/WLAN is OFF.", "Required"))
        communityCard = rowTile("Community Device Check", "For China-routed devices, confirm device/account status in Xiaomi Community if needed.", stateStore.communityState().name)
        root.addView(communityCard)

        startWaitingButton = primaryButton("Start Waiting") { startActivity(Intent(this, StartWaitingActivity::class.java)) }
        root.addView(startWaitingButton)
        root.addView(secondaryButton("Import Firefox + Chrome tokens") { startActivity(Intent(this, TokenImportActivity::class.java)) })
        root.addView(secondaryButton("Community Check") { startActivity(Intent(this, CommunityCheckActivity::class.java)) })
        root.addView(secondaryButton("Open Logs") { startActivity(Intent(this, LogsActivity::class.java)) })
        root.addView(secondaryButton("Instructions") { startActivity(Intent(this, InstructionsActivity::class.java)) })
        root.addView(TextView(this).apply {
            text = "By the THETECHGUY TOOL team"
            textSize = 13f
            setTextColor(Color.rgb(145, 160, 190))
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, dp(8))
        })
    }

    private fun headerBlock(): View = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER
        setPadding(0, dp(8), 0, dp(12))
        addView(TextView(this@MainActivity).apply {
            text = "MIBU"
            textSize = 40f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        })
        addView(TextView(this@MainActivity).apply {
            text = "THETECHGUY TOOL"
            textSize = 13f
            setTextColor(Color.rgb(145, 160, 190))
            gravity = Gravity.CENTER
        })
    }

    private fun heroBlock(): View {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(10), dp(10), dp(10), dp(16))
            background = rounded(Color.rgb(8, 15, 30), dp(24), Color.rgb(32, 55, 90))
        }
        card.addView(ImageView(this).apply {
            setImageResource(R.drawable.mibu_hero_art)
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.FIT_CENTER
        }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(220)))
        card.addView(TextView(this).apply {
            text = "Mi Bootloader Unlock Helper\nOne live countdown. Four hidden timing windows. PC verification."
            textSize = 18f
            gravity = Gravity.CENTER
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            setPadding(dp(12), dp(6), dp(12), 0)
        })
        rootParams(card, dp(14))
        return card
    }

    private fun statusTile(title: String, main: String, small: String) = TextView(this).apply {
        text = formatBlock(title, main, small)
        textSize = 15f
        setTextColor(Color.WHITE)
        setPadding(dp(18), dp(15), dp(18), dp(15))
        background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
        rootParams(this, dp(12))
    }

    private fun miniTile(title: String, value: String) = TextView(this).apply {
        text = "$title\n$value"
        textSize = 14f
        setTextColor(Color.WHITE)
        setPadding(dp(14), dp(14), dp(14), dp(14))
        background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
    }

    private fun rowTile(title: String, desc: String, badge: String) = TextView(this).apply {
        text = "$title\n$desc\n[$badge]"
        textSize = 14f
        setTextColor(Color.WHITE)
        setPadding(dp(18), dp(14), dp(18), dp(14))
        background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
        rootParams(this, dp(10))
    }

    private fun primaryButton(text: String, onClick: () -> Unit) = Button(this).apply {
        this.text = text
        textSize = 16f
        setTextColor(Color.WHITE)
        background = rounded(Color.rgb(30, 88, 255), dp(14), Color.rgb(75, 114, 255))
        setOnClickListener { onClick() }
        rootParams(this, dp(10))
    }

    private fun secondaryButton(text: String, onClick: () -> Unit) = Button(this).apply {
        this.text = text
        textSize = 15f
        setTextColor(Color.WHITE)
        background = rounded(Color.rgb(14, 23, 40), dp(14), Color.rgb(40, 66, 106))
        setOnClickListener { onClick() }
        rootParams(this, dp(10))
    }

    private fun refreshStatus() {
        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val verification = stateStore.reconcileTimingState(nowChina)
        val persistedTarget = stateStore.waitingTargetMidnight()?.let {
            MibuLane.defaultLanes().first().targetTimeForMidnight(it)
        }
        val targetChina = when {
            persistedTarget != null -> persistedTarget
            verification.isAuthoritativeResult() -> null
            else -> MibuLane.defaultLanes().first().targetTime(nowChina)
        }
        val localTarget = targetChina?.withZoneSameInstant(ZoneId.systemDefault())
        val duration = targetChina?.let { Duration.between(nowChina, it) }
            ?.let { if (it.isNegative) Duration.ZERO else it }
            ?: Duration.ZERO
        val totalSeconds = duration.seconds.coerceAtLeast(0L)
        val hours = totalSeconds / 3600L
        val minutes = (totalSeconds % 3600L) / 60L
        val seconds = totalSeconds % 60L
        val fmtDate = DateTimeFormatter.ofPattern("MMM dd, yyyy")
        val fmtTime = DateTimeFormatter.ofPattern("HH:mm:ss.SSS")
        val tokenStatus = when {
            tokenStore.hasRequiredCaptures() -> "Ready"
            tokenStore.hasSession() -> "Partial setup"
            else -> "Waiting for tokens"
        }
        val reached = stateStore.lanes().count { it.status == LaneStatus.WINDOW_REACHED }
        val engineStatus = when (verification) {
            VerificationState.TIMING_WINDOW_REACHED,
            VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Timing window reached"
            VerificationState.WAITING_ARMED -> "Armed • $reached/4 windows reached"
            else -> if (verification.isAuthoritativeResult()) "Result recorded" else "Not armed"
        }

        statusCard.text = formatBlock("Account Status", tokenStatus, "User logs in themselves. MIBU stores only explicit token/session imports.")
        sessionCard.text = formatBlock("Token Setup", tokenStore.getSessionPreview(), "Firefox fills 1/3. Chrome fills 2/4.")
        laneCard.text = formatBlock("Waiting Engine", engineStatus, "Details stay in Logs. The main screen remains one clean countdown.")
        verifyCard.text = formatBlock("Verification", friendlyVerification(verification), verificationGuidance(verification))
        communityCard.text = "Community Device Check\nFor China-routed devices, confirm device/account status in Xiaomi Community if needed.\n[${stateStore.communityState().name}]"

        if (targetChina != null && localTarget != null) {
            beijingCard.text = "Target Time (Beijing)\n${targetChina.format(fmtDate)}\n${targetChina.format(fmtTime)}\nGMT+8"
            localCard.text = "Target Time (Local)\n${localTarget.format(fmtDate)}\n${localTarget.format(fmtTime)}\n${localTarget.zone.id}"
        } else {
            beijingCard.text = "Target Time (Beijing)\n$NO_ACTIVE_TARGET\nResult recorded"
            localCard.text = "Target Time (Local)\n$NO_ACTIVE_TARGET\n${ZoneId.systemDefault().id}"
        }

        countdownCard.text = when {
            verification.isTimingComplete() ->
                formatBlock("Timing Stage", "COMPLETE", "Continue with PC verification")
            verification.isAuthoritativeResult() ->
                formatBlock("Verification Result", friendlyVerification(verification), "No new countdown is active")
            else ->
                formatBlock("Time Remaining", "%02d : %02d : %02d".format(hours, minutes, seconds), "HOURS   MINUTES   SECONDS")
        }

        when {
            verification == VerificationState.WAITING_ARMED -> {
                startWaitingButton.isEnabled = true
                startWaitingButton.text = "Resume Waiting"
            }
            verification.blocksNewWaitingCycle() -> {
                startWaitingButton.isEnabled = false
                startWaitingButton.text = if (verification == VerificationState.UNLOCKED) "Device Unlocked" else "Result Recorded"
            }
            else -> {
                startWaitingButton.isEnabled = true
                startWaitingButton.text = "Start Waiting"
            }
        }
    }

    private fun friendlyVerification(state: VerificationState): String = when (state) {
        VerificationState.NOT_STARTED -> "Not started"
        VerificationState.WAITING_ARMED -> "Waiting armed"
        VerificationState.TIMING_WINDOW_REACHED -> "Timing window reached"
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Ready for Mi Unlock verification"
        VerificationState.WAIT_TIME_SHOWN -> "Official wait time shown"
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED -> "Account/device not added"
        VerificationState.COMMUNITY_AUTH_REQUIRED -> "Community authorisation required"
        VerificationState.UNLOCKED -> "Unlocked"
        VerificationState.UNKNOWN -> "Unknown — review Logs"
    }

    private fun verificationGuidance(state: VerificationState): String = when (state) {
        VerificationState.TIMING_WINDOW_REACHED,
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Continue with PC Helper and the official Mi Unlock Tool."
        VerificationState.WAIT_TIME_SHOWN -> "Keep the official waiting period; do not restart the timing cycle."
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED -> "Resolve the phone-side account/device association before retrying."
        VerificationState.COMMUNITY_AUTH_REQUIRED -> "Complete the Xiaomi Community authorisation route first."
        VerificationState.UNLOCKED -> "The authoritative result is already complete."
        else -> "MIBU confirms timing state only. PC Helper and the official Mi Unlock Tool provide device verification."
    }

    private fun formatBlock(title: String, main: String, small: String) = if (small.isBlank()) "$title\n$main" else "$title\n$main\n$small"
    private fun rounded(color: Int, radius: Int, stroke: Int) = GradientDrawable().apply { setColor(color); cornerRadius = radius.toFloat(); setStroke(dp(1), stroke) }
    private fun rootParams(view: View, bottom: Int = 0) {
        view.layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { setMargins(0, 0, 0, bottom) }
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST = 49
        private const val NO_ACTIVE_TARGET = "No active target"
    }
}
