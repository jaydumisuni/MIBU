package com.thetechguy.mibu

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.util.Log
import java.time.Duration
import java.time.ZonedDateTime

class MibuForegroundService : Service() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }
    private val handler = Handler(Looper.getMainLooper())
    private val callbacks = mutableListOf<Runnable>()
    private var wakeLock: PowerManager.WakeLock? = null
    private var reachedCount = 0
    private var proofNonce = "none"

    override fun onCreate() {
        super.onCreate()
        ensureChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        proofNonce = ProofNonce.from(intent)
        return try {
            callbacks.forEach(handler::removeCallbacks)
            callbacks.clear()

            val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
            val reconciled = stateStore.reconcileTimingState(nowChina)
            reachedCount = stateStore.lanes().count { it.status == LaneStatus.WINDOW_REACHED }

            when {
                reconciled == VerificationState.TIMING_WINDOW_REACHED ||
                    reconciled == VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION -> {
                    startForeground(NOTIFICATION_ID, buildNotification("Timing window reached • continue with PC verification"))
                    Log.i(LOG_TAG, "WAITING_SERVICE_RECOVERED_COMPLETE state=${reconciled.name} reached=$reachedCount nonce=$proofNonce")
                    handler.postDelayed({ stopSelf() }, 15_000L)
                    START_NOT_STICKY
                }

                isAuthoritativeResult(reconciled) -> {
                    Log.i(LOG_TAG, "WAITING_SERVICE_NOT_NEEDED state=${reconciled.name} nonce=$proofNonce")
                    stopSelf(startId)
                    START_NOT_STICKY
                }

                !tokenStore.hasRequiredCaptures() -> {
                    Log.w(LOG_TAG, "WAITING_SERVICE_REJECTED_MISSING_CAPTURES nonce=$proofNonce")
                    stateStore.setVerificationState(VerificationState.UNKNOWN)
                    stopSelf(startId)
                    START_NOT_STICKY
                }

                else -> {
                    val targetMidnight = stateStore.waitingTargetMidnight()
                        ?: throw IllegalStateException("Waiting target midnight was not persisted")
                    val armedLanes = stateStore.lanes().filter { it.status == LaneStatus.ARMED }
                    if (armedLanes.isEmpty()) {
                        throw IllegalStateException("No armed timing lanes remain for an incomplete waiting state")
                    }

                    val delays = armedLanes.associateWith { lane ->
                        Duration.between(nowChina, lane.targetTimeForMidnight(targetMidnight)).toMillis().coerceAtLeast(0L)
                    }
                    val latestDelay = delays.values.maxOrNull() ?: 0L
                    if (latestDelay > tokenStore.millisRemaining()) {
                        Log.w(LOG_TAG, "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY latestDelayMs=$latestDelay nonce=$proofNonce")
                        stateStore.setVerificationState(VerificationState.UNKNOWN)
                        stopSelf(startId)
                        START_NOT_STICKY
                    } else {
                        startForeground(NOTIFICATION_ID, buildNotification("Waiting armed • $reachedCount/4 timing windows reached"))
                        acquireWakeLock(latestDelay + 60_000L)
                        armedLanes.forEach { lane ->
                            val callback = Runnable { markWindowReached(lane.number) }
                            callbacks += callback
                            handler.postDelayed(callback, delays.getValue(lane))
                        }
                        Log.i(
                            LOG_TAG,
                            "WAITING_SERVICE_ARMED targetMidnight=${targetMidnight.toInstant().toEpochMilli()} lanes=${armedLanes.joinToString(",") { it.number.toString() }} latestDelayMs=$latestDelay nonce=$proofNonce"
                        )
                        START_NOT_STICKY
                    }
                }
            }
        } catch (exc: Exception) {
            Log.e(LOG_TAG, "WAITING_SERVICE_FAILED nonce=$proofNonce", exc)
            val current = stateStore.verificationState()
            if (current != VerificationState.TIMING_WINDOW_REACHED &&
                current != VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION &&
                !isAuthoritativeResult(current)
            ) {
                stateStore.setVerificationState(VerificationState.UNKNOWN)
            }
            stopSelf(startId)
            START_NOT_STICKY
        }
    }

    private fun isAuthoritativeResult(state: VerificationState): Boolean = when (state) {
        VerificationState.WAIT_TIME_SHOWN,
        VerificationState.ACCOUNT_DEVICE_NOT_ADDED,
        VerificationState.COMMUNITY_AUTH_REQUIRED,
        VerificationState.UNLOCKED -> true
        else -> false
    }

    private fun markWindowReached(laneNumber: Int) {
        stateStore.setLaneStatus(laneNumber, LaneStatus.WINDOW_REACHED)
        reachedCount = stateStore.lanes().count { it.status == LaneStatus.WINDOW_REACHED }
        val manager = getSystemService(NotificationManager::class.java)
        if (reachedCount >= MibuLane.defaultLanes().size) {
            stateStore.setVerificationState(VerificationState.TIMING_WINDOW_REACHED)
            manager.notify(NOTIFICATION_ID, buildNotification("Timing window reached • continue with PC verification"))
            Log.i(LOG_TAG, "WAITING_SERVICE_COMPLETE reached=$reachedCount nonce=$proofNonce")
            handler.postDelayed({ stopSelf() }, 15_000L)
        } else {
            manager.notify(NOTIFICATION_ID, buildNotification("Waiting armed • $reachedCount/4 timing windows reached"))
            Log.i(LOG_TAG, "WAITING_LANE_REACHED lane=$laneNumber reached=$reachedCount nonce=$proofNonce")
        }
    }

    override fun onDestroy() {
        callbacks.forEach(handler::removeCallbacks)
        callbacks.clear()
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun acquireWakeLock(timeoutMs: Long) {
        wakeLock?.let { if (it.isHeld) it.release() }
        val power = getSystemService(PowerManager::class.java)
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MIBU:TimingWindow").apply {
            setReferenceCounted(false)
            acquire(timeoutMs.coerceAtMost(TokenStore.MAX_TOKEN_AGE_MS + 60_000L))
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "MIBU waiting service", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

    private fun buildNotification(message: String): Notification {
        val pending = PendingIntent.getActivity(
            this,
            49,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("MIBU timing assistant")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pending)
            .setOngoing(reachedCount < 4)
            .build()
    }

    companion object {
        private const val CHANNEL_ID = "mibu_wait"
        private const val NOTIFICATION_ID = 49
        private const val LOG_TAG = "MIBU_SERVICE"
    }
}
