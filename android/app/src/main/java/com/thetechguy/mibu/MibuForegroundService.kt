package com.thetechguy.mibu

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log

class MibuForegroundService : Service() {
    private val tokenStore by lazy { TokenStore(this) }

    override fun onCreate() {
        super.onCreate()
        ensureChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return try {
            if (!tokenStore.hasSession()) {
                Log.w("MIBU", "No session token imported; waiting service stopping cleanly")
                stopSelf(startId)
                START_NOT_STICKY
            } else {
                startForeground(49, buildNotification())
                Log.i("MIBU", "Waiting service running")
                START_STICKY
            }
        } catch (exc: Exception) {
            Log.e("MIBU", "Waiting service failed", exc)
            stopSelf(startId)
            START_NOT_STICKY
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                "mibu_wait",
                "MIBU waiting service",
                NotificationManager.IMPORTANCE_LOW
            )
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, "mibu_wait")
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("MIBU is active")
            .setContentText("Keeping the request-window helper alive.")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()
    }
}
