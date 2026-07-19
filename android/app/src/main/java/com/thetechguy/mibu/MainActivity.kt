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
            if (::accountValue.isInitialized) refreshStatus()
            uiHandler.postDelayed(this, 1000L)
        }
    }

    private lateinit var accountValue: TextView
    private lateinit var sessionValue: TextView
    private lateinit var beijingValue: TextView
    private lateinit var localValue: TextView
    private lateinit var countdownValue: TextView
    private lateinit var serviceValue: TextView
    private lateinit var startWaitingButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermissionIfNeeded()
        buildUi()
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
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(18))
            setBackgroundColor(Color.rgb(4, 6, 17))
        }
        setContentView(ScrollView(this).apply { addView(root) })

        root.addView(heroImage())
        root.addView(title("MIBU PC Helper", "THETECHGUY TOOL"))

        val statusRow = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val account = liveCard("Account Status", green())
        accountValue = account.second
        val session = liveCard("Session Imported", cyan())
        sessionValue = session.second
        statusRow.addView(account.first)
        statusRow.addView(session.first)
        root.addView(statusRow)

        val timeRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val beijing = liveCard("Target Time (Beijing)", orange())
        val local = liveCard("Target Time (Local)", purple())
        beijingValue = beijing.second
        localValue = local.second
        timeRow.addView(beijing.first, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(0, 0, dp(6), 0) })
        timeRow.addView(local.first, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(dp(6), 0, 0, 0) })
        root.addView(timeRow)

        val countdown = liveCard("Time Remaining", purple(), large = true)
        countdownValue = countdown.second
        root.addView(countdown.first)

        val service = liveCard("Foreground Service", cyan())
        serviceValue = service.second
        root.addView(service.first)

        startWaitingButton = neonButton("Start Waiting", true) {
            startActivity(Intent(this, StartWaitingActivity::class.java))
        }
        root.addView(startWaitingButton)

        val buttons = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        buttons.addView(neonButton("Open Logs") {
            startActivity(Intent(this@MainActivity, LogsActivity::class.java))
        }, LinearLayout.LayoutParams(0, dp(58), 1f).apply { setMargins(0, 0, dp(6), 0) })
        buttons.addView(neonButton("Instructions") {
            startActivity(Intent(this@MainActivity, InstructionsActivity::class.java))
        }, LinearLayout.LayoutParams(0, dp(58), 1f).apply { setMargins(dp(6), 0, 0, 0) })
        root.addView(buttons)

        root.addView(neonButton("Import Session From PC") {
            startActivity(Intent(this, TokenImportActivity::class.java))
        })
    }

    private fun refreshStatus() {
        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val verification = stateStore.reconcileTimingState(nowChina)
        val targetChina = stateStore.waitingTargetMidnight()?.let {
            MibuLane.defaultLanes().first().targetTimeForMidnight(it)
        } ?: if (verification.isAuthoritativeResult()) null else MibuLane.defaultLanes().first().targetTime(nowChina)
        val localTarget = targetChina?.withZoneSameInstant(ZoneId.systemDefault())
        val remaining = targetChina?.let { Duration.between(nowChina, it) }?.let { if (it.isNegative) Duration.ZERO else it } ?: Duration.ZERO
        val totalSeconds = remaining.seconds.coerceAtLeast(0L)
        val hours = totalSeconds / 3600L
        val minutes = (totalSeconds % 3600L) / 60L
        val seconds = totalSeconds % 60L
        val fmtDate = DateTimeFormatter.ofPattern("MMM dd, yyyy")
        val fmtTime = DateTimeFormatter.ofPattern("HH:mm:ss.SSS")

        accountValue.text = when {
            tokenStore.hasRequiredCaptures() -> "Eligible to send request"
            tokenStore.hasSession() -> "Partial setup"
            else -> "Waiting for session/token"
        }
        sessionValue.text = if (tokenStore.hasRequiredCaptures()) "From MIBU PC Tool" else "Import from PC helper first"
        beijingValue.text = if (targetChina == null) "No active target" else "${targetChina.format(fmtTime)}\n${targetChina.format(fmtDate)}"
        localValue.text = if (localTarget == null) "No active target" else "${localTarget.format(fmtTime)}\n${localTarget.format(fmtDate)}"
        countdownValue.text = when {
            verification.isTimingComplete() -> "COMPLETE"
            verification.isAuthoritativeResult() -> friendlyVerification(verification)
            else -> "%02d : %02d : %02d\nHOURS  MINUTES  SECONDS".format(hours, minutes, seconds)
        }
        serviceValue.text = if (verification == VerificationState.WAITING_ARMED) "Service is running" else friendlyVerification(verification)
        startWaitingButton.text = when {
            verification == VerificationState.WAITING_ARMED -> "Resume Waiting"
            verification.blocksNewWaitingCycle() -> "Result Recorded"
            else -> "Start Waiting"
        }
        startWaitingButton.isEnabled = !verification.blocksNewWaitingCycle()
        serviceValue.contentDescription = verificationGuidance(verification)
    }

    private fun heroImage(): ImageView =
        ImageView(this).apply {
            setImageResource(R.drawable.mibu_hood_hero)
            scaleType = ImageView.ScaleType.CENTER_CROP
            background = rounded(Color.rgb(8, 12, 30), dp(22), Color.rgb(40, 62, 102))
            clipToOutline = true
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(270)).apply { setMargins(0, 0, 0, dp(14)) }
        }

    private fun title(primary: String, secondary: String): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            addView(TextView(this@MainActivity).apply {
                text = primary
                textSize = 30f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
                includeFontPadding = false
            })
            addView(TextView(this@MainActivity).apply {
                text = secondary
                textSize = 13f
                setTextColor(Color.rgb(166, 177, 205))
                gravity = Gravity.CENTER
                letterSpacing = 0.08f
            })
        }

    private fun liveCard(label: String, stroke: Int, large: Boolean = false): Pair<LinearLayout, TextView> {
        val value = TextView(this).apply {
            text = "--"
            textSize = if (large) 29f else 17f
            typeface = if (large) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
            setTextColor(Color.WHITE)
            gravity = if (large) Gravity.CENTER else Gravity.START
        }
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(14), dp(18), dp(14))
            background = rounded(Color.rgb(10, 15, 32), dp(18), stroke)
            addView(TextView(this@MainActivity).apply {
                text = label
                textSize = 13f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.rgb(180, 190, 215))
            })
            addView(value)
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                setMargins(0, dp(10), 0, 0)
            }
        }
        return card to value
    }

    private fun neonButton(textValue: String, primary: Boolean = false, onClick: () -> Unit): Button =
        Button(this).apply {
            text = textValue
            textSize = if (primary) 18f else 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = rounded(if (primary) Color.rgb(23, 20, 48) else Color.rgb(10, 15, 32), dp(18), if (primary) orange() else Color.rgb(55, 78, 122))
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, if (primary) dp(70) else dp(58)).apply {
                setMargins(0, dp(12), 0, 0)
            }
        }

    private fun rounded(color: Int, radius: Int, stroke: Int): GradientDrawable =
        GradientDrawable().apply { setColor(color); cornerRadius = radius.toFloat(); setStroke(dp(1), stroke) }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
    private fun green() = Color.rgb(61, 255, 135)
    private fun cyan() = Color.rgb(36, 178, 255)
    private fun purple() = Color.rgb(176, 83, 255)
    private fun orange() = Color.rgb(255, 122, 43)

    private fun friendlyVerification(state: VerificationState): String = when (state) {
        VerificationState.NOT_STARTED -> "Not started"
        VerificationState.WAITING_ARMED -> "Waiting armed"
        VerificationState.TIMING_WINDOW_REACHED -> "Timing window reached"
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Ready for Mi Unlock"
        VerificationState.WAIT_TIME_SHOWN -> "Official wait time shown"
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED -> "Account/device not added"
        VerificationState.COMMUNITY_AUTH_REQUIRED -> "Community authorisation required"
        VerificationState.UNLOCKED -> "Unlocked"
        VerificationState.UNKNOWN -> "Unknown - review Logs"
    }

    private fun verificationGuidance(state: VerificationState): String = when (state) {
        VerificationState.TIMING_WINDOW_REACHED,
        VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> "Continue with PC Helper and the official Mi Unlock Tool."
        VerificationState.WAIT_TIME_SHOWN -> "Keep the official waiting period; do not restart the timing cycle."
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED -> "Resolve the phone-side account/device association before retrying."
        VerificationState.COMMUNITY_AUTH_REQUIRED -> "Complete the Xiaomi Community authorisation route first."
        VerificationState.UNLOCKED -> "The authoritative result is already complete."
        else -> "No active target"
    }

    companion object {
        private const val NOTIFICATION_PERMISSION_REQUEST = 49
    }
}
