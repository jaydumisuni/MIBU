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

    override fun onCreate() {
        super.onCreate()
        ensureChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return try {
            callbacks.forEach(handler::removeCallbacks)
            callbacks.clear()
            reachedCount = 0

            if (!tokenStore.hasRequiredCaptures()) {
                Log.w("MIBU", "Fresh Firefox + Chrome captures are not available; waiting service stopping")
                stateStore.setVerificationState(VerificationState.UNKNOWN)
                stateStore.clearWaitingTarget()
                stopSelf(startId)
                START_NOT_STICKY
            } else {
                val nowChina = ZonedDateTime.now(MibuLane.CHINA_ZONE)
                val targetMidnight = stateStore.waitingTargetMidnight()
                    ?: throw IllegalStateException("Waiting target midnight was not persisted")
                val lanes = MibuLane.defaultLanes()
                val delays = lanes.associateWith {
                    Duration.between(nowChina, it.targetTimeForMidnight(targetMidnight)).toMillis()
                }
                val earliestDelay = delays.values.minOrNull() ?: -1L
                val latestDelay = delays.values.maxOrNull() ?: -1L
                if (earliestDelay < 0L || latestDelay < 0L) {
                    Log.w("MIBU", "Persisted timing session is already past; stopping")
                    stateStore.setVerificationState(VerificationState.UNKNOWN)
                    stateStore.clearWaitingTarget()
                    stopSelf(startId)
                    START_NOT_STICKY
                } else if (latestDelay > tokenStore.millisRemaining()) {
                    Log.w("MIBU", "Tokens expire before latest timing window; stopping")
                    stateStore.setVerificationState(VerificationState.UNKNOWN)
                    stateStore.clearWaitingTarget()
                    stopSelf(startId)
                    START_NOT_STICKY
                } else {
                    startForeground(NOTIFICATION_ID, buildNotification("Waiting armed • 0/4 timing windows reached"))
                    acquireWakeLock(latestDelay + 60_000L)

                    lanes.forEach { lane ->
                        val callback = Runnable { markWindowReached(lane.number) }
                        callbacks += callback
                        handler.postDelayed(callback, delays.getValue(lane))
                    }
                    Log.i("MIBU", "Waiting service scheduled four timing windows for ${targetMidnight.toInstant().toEpochMilli()}")
                    START_NOT_STICKY
                }
            }
        } catch (exc: Exception) {
            Log.e("MIBU", "Waiting service failed", exc)
            stateStore.setVerificationState(VerificationState.UNKNOWN)
            stateStore.clearWaitingTarget()
            stopSelf(startId)
            START_NOT_STICKY
        }
    }

    private fun markWindowReached(laneNumber: Int) {
        stateStore.setLaneStatus(laneNumber, LaneStatus.WINDOW_REACHED)
        reachedCount += 1
        val manager = getSystemService(NotificationManager::class.java)
        if (reachedCount >= MibuLane.defaultLanes().size) {
            stateStore.setVerificationState(VerificationState.TIMING_WINDOW_REACHED)
            manager.notify(NOTIFICATION_ID, buildNotification("Timing window reached • continue with PC verification"))
            Log.i("MIBU", "All four timing windows reached")
            handler.postDelayed({ stopSelf() }, 15_000L)
        } else {
            manager.notify(NOTIFICATION_ID, buildNotification("Waiting armed • $reachedCount/4 timing windows reached"))
            Log.i("MIBU", "Timing window reached for lane $laneNumber")
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
    }
}
