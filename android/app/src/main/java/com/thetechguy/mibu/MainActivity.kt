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

    private lateinit var accountCard: TextView
    private lateinit var sessionCard: TextView
    private lateinit var beijingCard: TextView
    private lateinit var localCard: TextView
    private lateinit var countdownCard: TextView
    private lateinit var mobileDataCard: TextView
    private lateinit var serviceCard: TextView
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
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(30), dp(20), dp(18))
            setBackgroundColor(Color.rgb(3, 7, 16))
        }
        setContentView(ScrollView(this).apply { addView(root) })

        root.addView(ImageView(this).apply {
            setImageResource(R.drawable.mibu_logo)
            adjustViewBounds = true
            scaleType = ImageView.ScaleType.FIT_CENTER
        }, fullWidth(dp(190), dp(4)))
        root.addView(label("MIBU", 34f, Color.WHITE, true, Gravity.CENTER))
        root.addView(label("THETECHGUY TOOL", 13f, muted(), false, Gravity.CENTER))

        accountCard = neonRow("✓", "Account Status", "Checking", green())
        sessionCard = neonRow("▣", "Session Imported", "Import from PC helper first", cyan())
        root.addView(accountCard)
        root.addView(sessionCard)

        val timeRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        beijingCard = miniPanel("Target Time (Beijing)", "--")
        localCard = miniPanel("Target Time (Local)", "--")
        timeRow.addView(beijingCard, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(0, 0, dp(6), 0) })
        timeRow.addView(localCard, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(dp(6), 0, 0, 0) })
        root.addView(timeRow)

        countdownCard = countdownPanel("-- : -- : --")
        root.addView(countdownCard)
        mobileDataCard = neonRow("▮", "Mobile Data Reminder", "Mobile data is ON", green())
        serviceCard = neonRow("◇", "Foreground Service", "Ready", cyan())
        root.addView(mobileDataCard)
        root.addView(serviceCard)

        startWaitingButton = neonButton("▷  Start Waiting", true) {
            startActivity(Intent(this, StartWaitingActivity::class.java))
        }
        root.addView(startWaitingButton)

        val bottomRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        bottomRow.addView(neonButton("Open Logs", false) {
            startActivity(Intent(this@MainActivity, LogsActivity::class.java))
        }, LinearLayout.LayoutParams(0, dp(72), 1f).apply { setMargins(0, 0, dp(6), 0) })
        bottomRow.addView(neonButton("Instructions", false) {
            startActivity(Intent(this@MainActivity, InstructionsActivity::class.java))
        }, LinearLayout.LayoutParams(0, dp(72), 1f).apply { setMargins(dp(6), 0, 0, 0) })
        root.addView(bottomRow)

        root.addView(neonButton("Import Firefox + Chrome Tokens", false) {
            startActivity(Intent(this, TokenImportActivity::class.java))
        })
        root.addView(neonButton("Community / Settings", false) {
            startActivity(Intent(this, CommunityCheckActivity::class.java))
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

        val tokenStatus = when {
            tokenStore.hasRequiredCaptures() -> "Eligible to send request"
            tokenStore.hasSession() -> "Partial setup"
            else -> "Waiting for session/token"
        }
        accountCard.text = rowText("✓", "Account Status", tokenStatus)
        sessionCard.text = rowText("▣", "Session Imported", if (tokenStore.hasRequiredCaptures()) "From MIBU PC Tool" else "Import from PC helper first")
        beijingCard.text = if (targetChina == null) "Target Time (Beijing)\nNo active target" else "Target Time (Beijing)\n${targetChina.format(fmtTime)}\n${targetChina.format(fmtDate)}"
        localCard.text = if (localTarget == null) "Target Time (Local)\nNo active target" else "Target Time (Local)\n${localTarget.format(fmtTime)}\n${localTarget.format(fmtDate)}"
        countdownCard.text = when {
            verification.isTimingComplete() -> "Time Remaining\nCOMPLETE"
            verification.isAuthoritativeResult() -> "Verification\n${friendlyVerification(verification)}"
            else -> "Time Remaining\n%02d : %02d : %02d\nHOURS   MINUTES   SECONDS".format(hours, minutes, seconds)
        }
        serviceCard.text = rowText("◇", "Foreground Service", if (verification == VerificationState.WAITING_ARMED) "Service is running" else friendlyVerification(verification))
        startWaitingButton.text = when {
            verification == VerificationState.WAITING_ARMED -> "▷  $RESUME_WAITING_LABEL"
            verification.blocksNewWaitingCycle() -> "Result Recorded"
            else -> "▷  Start Waiting"
        }
        startWaitingButton.contentDescription = startWaitingButton.text
        startWaitingButton.isEnabled = !verification.blocksNewWaitingCycle()
        serviceCard.contentDescription = verificationGuidance(verification)
    }

    private fun neonRow(icon: String, title: String, body: String, stroke: Int): TextView =
        TextView(this).apply {
            text = rowText(icon, title, body)
            textSize = 16f
            setTextColor(Color.WHITE)
            setPadding(dp(18), dp(14), dp(18), dp(14))
            background = rounded(Color.rgb(8, 14, 28), dp(18), stroke)
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                setMargins(0, dp(10), 0, 0)
            }
        }

    private fun rowText(icon: String, title: String, body: String) = "$icon   $title\n     $body"

    private fun miniPanel(title: String, value: String): TextView =
        TextView(this).apply {
            text = "$title\n$value"
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(dp(14), dp(14), dp(14), dp(14))
            background = rounded(Color.rgb(11, 14, 30), dp(16), purple())
        }

    private fun countdownPanel(value: String): TextView =
        TextView(this).apply {
            text = "Time Remaining\n$value"
            textSize = 25f
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            setPadding(dp(12), dp(18), dp(12), dp(18))
            background = rounded(Color.rgb(8, 10, 26), dp(20), purple())
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
                setMargins(0, dp(12), 0, dp(2))
            }
        }

    private fun neonButton(text: String, primary: Boolean, onClick: () -> Unit): Button =
        Button(this).apply {
            this.text = text
            textSize = if (primary) 20f else 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = rounded(if (primary) Color.rgb(22, 18, 44) else Color.rgb(9, 13, 26), dp(18), if (primary) orange() else purple())
            setOnClickListener { onClick() }
            layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, if (primary) dp(86) else dp(58)).apply {
                setMargins(0, dp(12), 0, 0)
            }
        }

    private fun label(textValue: String, size: Float, color: Int, bold: Boolean, gravityValue: Int): TextView =
        TextView(this).apply {
            text = textValue
            textSize = size
            setTextColor(color)
            gravity = gravityValue
            if (bold) typeface = Typeface.DEFAULT_BOLD
            includeFontPadding = false
        }

    private fun fullWidth(height: Int, bottom: Int): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, height).apply { setMargins(0, 0, 0, bottom) }

    private fun rounded(color: Int, radius: Int, stroke: Int): GradientDrawable =
        GradientDrawable().apply { setColor(color); cornerRadius = radius.toFloat(); setStroke(dp(1), stroke) }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
    private fun muted() = Color.rgb(160, 168, 190)
    private fun green() = Color.rgb(61, 255, 135)
    private fun cyan() = Color.rgb(36, 178, 255)
    private fun purple() = Color.rgb(168, 80, 255)
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
        private const val RESUME_WAITING_LABEL = "Resume Waiting"
    }
}
