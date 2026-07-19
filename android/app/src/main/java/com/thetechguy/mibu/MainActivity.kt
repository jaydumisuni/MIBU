package com.thetechguy.mibu

import android.Manifest
import android.app.Activity
import android.app.ActivityManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.time.Duration
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

class MainActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }
    private val logStore by lazy { LogStore(this) }
    private val uiHandler = Handler(Looper.getMainLooper())
    private val ticker = object : Runnable {
        override fun run() {
            if (::countdownValue.isInitialized) refreshStatus()
            uiHandler.postDelayed(this, 1000L)
        }
    }

    private lateinit var accountValue: TextView
    private lateinit var accountBadge: TextView
    private lateinit var sessionValue: TextView
    private lateinit var beijingValue: TextView
    private lateinit var localValue: TextView
    private lateinit var countdownValue: TextView
    private lateinit var mobileValue: TextView
    private lateinit var serviceValue: TextView
    private lateinit var serviceBadge: TextView
    private lateinit var startWaitingRoot: LinearLayout
    private lateinit var startWaitingTitle: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
    }

    override fun onResume() {
        super.onResume()
        uiHandler.removeCallbacks(ticker)
        if (::countdownValue.isInitialized) refreshStatus()
        uiHandler.post(ticker)
    }

    override fun onPause() {
        uiHandler.removeCallbacks(ticker)
        super.onPause()
    }

    private fun buildUi() {
        val verification = stateStore.reconcileTimingState()
        if (!tokenStore.hasRequiredCaptures() && verification == VerificationState.NOT_STARTED) {
            buildWelcome()
        } else {
            buildDashboard()
            refreshStatus()
        }
    }

    private fun buildWelcome() {
        mibuScreen {
            addView(mibuBrandHeader(onSettings = { openSettings() }, large = true))
            addView(mibuHeading("Welcome to MIBU", "The phone app receives the approved session from the PC helper, then owns the countdown."))
            addView(mibuAction(R.drawable.mibu_icon_session, "Import session from PC", "Open the secure two-capture handoff", MibuColors.blue, true) {
                logStore.add("Session import opened")
                startActivity(Intent(this@MainActivity, TokenImportActivity::class.java))
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_check, "Check device status", "Review account, network and waiting state", MibuColors.cyan) {
                openSettings()
            }.root)
            addView(mibuAction(R.drawable.mibu_icon_guide, "View guide", "Follow the complete PC and phone workflow", MibuColors.purple) {
                startActivity(Intent(this@MainActivity, GuideActivity::class.java))
            }.root)
            addView(footer())
        }
    }

    private fun buildDashboard() {
        mibuScreen {
            addView(mibuBrandHeader(onSettings = { openSettings() }))

            val account = mibuLiveRow(R.drawable.mibu_icon_check, "Account Status", "Checking...", MibuColors.green, onClick = {
                startActivity(Intent(this@MainActivity, TokenImportActivity::class.java))
            })
            accountValue = account.value
            accountBadge = account.badge
            addView(account.root)

            val session = mibuLiveRow(R.drawable.mibu_icon_session, "Session Imported", "Checking...", MibuColors.blue, onClick = {
                startActivity(Intent(this@MainActivity, TokenImportActivity::class.java))
            })
            sessionValue = session.value
            addView(session.root)

            val times = LinearLayout(this@MainActivity).apply { orientation = LinearLayout.HORIZONTAL }
            val beijing = mibuTimeCard("Target Time (Beijing)", "--:--:--", "CST", MibuColors.orange)
            val local = mibuTimeCard("Target Time (Local)", "--:--:--", ZoneId.systemDefault().id, MibuColors.purple)
            beijingValue = beijing.second
            localValue = local.second
            times.addView(beijing.first, LinearLayout.LayoutParams(0, dp(100), 1f).apply { setMargins(0, 0, dp(4), dp(8)) })
            times.addView(local.first, LinearLayout.LayoutParams(0, dp(100), 1f).apply { setMargins(dp(4), 0, 0, dp(8)) })
            addView(times)

            val countdown = mibuCountdown()
            countdownValue = countdown.second
            addView(countdown.first)

            val mobile = mibuLiveRow(R.drawable.mibu_icon_signal, "Mobile Data Reminder", "Checking network...", MibuColors.green, onClick = {
                openSettings()
            })
            mobileValue = mobile.value
            addView(mobile.root)

            val service = mibuLiveRow(R.drawable.mibu_icon_shield, "Foreground Service", "Checking...", MibuColors.blue)
            serviceValue = service.value
            serviceBadge = service.badge
            addView(service.root)

            val start = mibuAction(R.drawable.mibu_icon_play_clean, "Start Waiting", "Arm or resume the phone-side countdown", MibuColors.orange, true) {
                beginWaiting()
            }
            startWaitingRoot = start.root
            startWaitingTitle = start.title
            addView(start.root)

            val bottom = LinearLayout(this@MainActivity).apply { orientation = LinearLayout.HORIZONTAL }
            val logs = mibuAction(R.drawable.mibu_icon_logs, "Open Logs", "Activity", MibuColors.purple) {
                startActivity(Intent(this@MainActivity, LogsActivity::class.java))
            }.root
            val instructions = mibuAction(R.drawable.mibu_icon_info, "Instructions", "Guide", MibuColors.blue) {
                startActivity(Intent(this@MainActivity, InstructionsActivity::class.java))
            }.root
            bottom.addView(logs, LinearLayout.LayoutParams(0, dp(62), 1f).apply { setMargins(0, 0, dp(4), 0) })
            bottom.addView(instructions, LinearLayout.LayoutParams(0, dp(62), 1f).apply { setMargins(dp(4), 0, 0, 0) })
            addView(bottom)
            addView(footer())
        }
    }

    private fun beginWaiting() {
        if (!requestNotificationPermissionIfNeeded()) return
        logStore.add("Start Waiting tapped")
        startActivity(Intent(this, StartWaitingActivity::class.java))
    }

    private fun requestNotificationPermissionIfNeeded(): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), NOTIFICATION_PERMISSION_REQUEST)
            return false
        }
        return true
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == NOTIFICATION_PERMISSION_REQUEST) {
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
                beginWaiting()
            } else {
                Toast.makeText(this, "Notification access is needed to keep waiting visible in the background.", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun openSettings() {
        startActivity(Intent(this, CommunityCheckActivity::class.java))
    }

    private fun refreshStatus() {
        val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
        val verification = stateStore.reconcileTimingState(nowChina)
        val targetChina = stateStore.waitingTargetMidnight()?.let {
            MibuLane.defaultLanes().first().targetTimeForMidnight(it)
        } ?: if (verification.isAuthoritativeResult()) null else MibuLane.defaultLanes().first().targetTime(nowChina)
        val localTarget = targetChina?.withZoneSameInstant(ZoneId.systemDefault())
        val remaining = targetChina?.let { Duration.between(nowChina, it) }
            ?.let { if (it.isNegative) Duration.ZERO else it } ?: Duration.ZERO
        val totalSeconds = remaining.seconds.coerceAtLeast(0L)
        val hours = totalSeconds / 3600L
        val minutes = (totalSeconds % 3600L) / 60L
        val seconds = totalSeconds % 60L
        val time = DateTimeFormatter.ofPattern("HH:mm:ss")

        accountValue.text = when {
            tokenStore.hasRequiredCaptures() -> "Eligible to send request"
            tokenStore.hasSession() -> "Partial setup - second capture needed"
            verification.isAuthoritativeResult() -> friendlyVerification(verification)
            else -> "Waiting for approved session"
        }
        accountBadge.text = when {
            tokenStore.hasRequiredCaptures() -> "READY"
            verification.isAuthoritativeResult() -> "RESULT"
            else -> "WAITING"
        }
        accountBadge.visibility = View.VISIBLE
        sessionValue.text = if (tokenStore.hasRequiredCaptures()) "From MIBU PC Tool" else "Import from PC helper"
        beijingValue.text = targetChina?.format(time) ?: "--:--:--"
        localValue.text = localTarget?.format(time) ?: "--:--:--"
        countdownValue.text = when {
            verification.isTimingComplete() -> "COMPLETE"
            verification.isAuthoritativeResult() -> friendlyVerification(verification).uppercase()
            else -> "%02d : %02d : %02d".format(hours, minutes, seconds)
        }
        mobileValue.text = if (isCellularActive()) "Mobile data is active" else "Open network settings to confirm mobile data"
        val running = isWaitingServiceRunning()
        serviceValue.text = if (running) "Service is running" else friendlyVerification(verification)
        serviceBadge.text = if (running) "RUNNING" else "IDLE"
        serviceBadge.visibility = View.VISIBLE
        startWaitingTitle.text = when {
            verification == VerificationState.WAITING_ARMED -> "Resume Waiting"
            verification.blocksNewWaitingCycle() -> "Result Recorded"
            else -> "Start Waiting"
        }
        startWaitingRoot.isEnabled = !verification.blocksNewWaitingCycle()
        startWaitingRoot.alpha = if (startWaitingRoot.isEnabled) 1f else 0.55f
        serviceValue.contentDescription = verificationGuidance(verification)
    }

    private fun isCellularActive(): Boolean {
        val connectivity = getSystemService(ConnectivityManager::class.java)
        val network = connectivity.activeNetwork ?: return false
        return connectivity.getNetworkCapabilities(network)?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true
    }

    @Suppress("DEPRECATION")
    private fun isWaitingServiceRunning(): Boolean {
        val manager = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        return manager.getRunningServices(Int.MAX_VALUE).any { it.service.className == MibuForegroundService::class.java.name }
    }

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
