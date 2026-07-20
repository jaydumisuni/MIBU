package com.thetechguy.mibu

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import java.security.MessageDigest
import java.time.Duration
import java.time.Instant
import java.time.ZonedDateTime
import java.util.UUID
import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

class MibuForegroundService : Service() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }
    private val logStore by lazy { LogStore(this) }
    private val client by lazy { XiaomiUnlockClient() }
    private val preparation = Executors.newSingleThreadExecutor()
    private val scheduler = ScheduledThreadPoolExecutor(4)
    private val scheduled = CopyOnWriteArrayList<ScheduledFuture<*>>()
    private val generation = AtomicInteger(0)
    private val resultLock = Any()
    private var wakeLock: PowerManager.WakeLock? = null
    private var proofNonce = "none"

    override fun onCreate() {
        super.onCreate()
        ensureChannel()
        scheduler.removeOnCancelPolicy = true
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        proofNonce = ProofNonce.from(intent)
        startForeground(NOTIFICATION_ID, buildNotification("Checking account, network and server time…"))
        stateStore.setServiceRunning(true)
        cancelScheduled()
        val run = generation.incrementAndGet()
        preparation.execute { prepareAndSchedule(run, startId) }
        return START_REDELIVER_INTENT
    }

    private fun prepareAndSchedule(run: Int, startId: Int) {
        try {
            val current = stateStore.verificationState()
            if (current == VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION) {
                finishReady("Xiaomi approval was already recorded", "WAITING_SERVICE_RECOVERED_COMPLETE")
                return
            }
            if (current.isAuthoritativeResult()) {
                failAndStop(current, "The saved authoritative result does not allow a new request cycle", "WAITING_SERVICE_NOT_NEEDED", startId)
                return
            }
            if (!tokenStore.hasRequiredCaptures()) {
                failAndStop(VerificationState.COOKIE_EXPIRED, "Fresh Firefox and Chrome captures are missing", "WAITING_SERVICE_REJECTED_MISSING_CAPTURES", startId)
                return
            }
            if (!isCellularReady()) {
                failAndStop(VerificationState.NETWORK_ERROR, "Mobile data is not the active validated network", "WAITING_SERVICE_REJECTED_CELLULAR", startId)
                return
            }

            val targetMidnight = stateStore.waitingTargetMidnight() ?: MibuLane.nextTargetMidnight()
            stateStore.beginPreflight(targetMidnight)
            updateNotification("Validating four browser-token lanes with Xiaomi…")
            val deviceIds = mutableMapOf<Int, String>()
            val clockOffsets = mutableListOf<Long>()

            for (lane in MibuLane.defaultLanes()) {
                if (run != generation.get()) return
                val token = tokenStore.tokenForLane(lane.number)
                if (token == null) {
                    failAndStop(VerificationState.COOKIE_EXPIRED, "Lane ${lane.number} capture expired during preflight", "WAITING_SERVICE_REJECTED_MISSING_CAPTURES", startId)
                    return
                }
                val deviceId = generateDeviceId(lane.number)
                deviceIds[lane.number] = deviceId
                val result = client.checkStatus(token, deviceId)
                stateStore.saveLaneResult(lane.number, result)
                result.clockOffsetMs?.let(clockOffsets::add)
                logStore.add("Lane ${lane.number} preflight: ${result.message}")
                Log.i(LOG_TAG, "PREFLIGHT lane=${lane.number} kind=${result.kind} code=${result.code} nonce=$proofNonce")

                if (result.kind == XiaomiResultKind.ALREADY_APPROVED) {
                    stateStore.setLaneStatus(lane.number, LaneStatus.APPROVED)
                    finishReady(result.message, "WAITING_SERVICE_PREFLIGHT_APPROVED")
                    return
                }
                if (result.kind != XiaomiResultKind.ELIGIBLE) {
                    failAndStop(result.toVerificationState(), result.message, "WAITING_SERVICE_PREFLIGHT_REJECTED", startId)
                    return
                }
            }

            if (clockOffsets.isEmpty()) {
                failAndStop(VerificationState.NETWORK_ERROR, "Xiaomi did not provide a server clock for safe scheduling", "WAITING_SERVICE_REJECTED_CLOCK", startId)
                return
            }
            val serverOffset = clockOffsets.sorted()[clockOffsets.size / 2]
            stateStore.setServerClockOffset(serverOffset)
            val correctedNowMs = System.currentTimeMillis() + serverOffset
            val latestTargetMs = MibuLane.defaultLanes().last().targetTimeForMidnight(targetMidnight).toInstant().toEpochMilli()
            val waitMs = latestTargetMs - correctedNowMs
            if (waitMs < -LATE_TOLERANCE_MS) {
                failAndStop(VerificationState.REQUEST_REJECTED, "The Beijing request window has already passed", "WAITING_SERVICE_REJECTED_LATE", startId)
                return
            }
            if (waitMs > tokenStore.millisRemaining()) {
                val waitMinutes = (waitMs.coerceAtLeast(0L) + 59_999L) / 60_000L
                failAndStop(
                    VerificationState.COOKIE_EXPIRED,
                    "Capture closer to Beijing midnight; the window is about $waitMinutes minutes away",
                    "WAITING_SERVICE_REJECTED_TOKEN_EXPIRY",
                    startId,
                )
                return
            }

            stateStore.armWaiting(targetMidnight)
            acquireWakeLock(waitMs.coerceAtLeast(0L) + 120_000L)
            scheduleHeartbeat(run)
            MibuLane.defaultLanes().forEach { lane ->
                val targetMs = lane.targetTimeForMidnight(targetMidnight).toInstant().toEpochMilli()
                val delayMs = (targetMs - correctedNowMs).coerceAtLeast(0L)
                scheduled += scheduler.schedule(
                    { submitLane(run, lane, deviceIds.getValue(lane.number)) },
                    delayMs,
                    TimeUnit.MILLISECONDS,
                )
            }
            updateNotification("Waiting armed • 0/4 verified server results")
            logStore.add("Four Xiaomi request lanes armed using verified server time")
            Log.i(
                LOG_TAG,
                "WAITING_SERVICE_ARMED targetMidnight=${targetMidnight.toInstant().toEpochMilli()} clockOffsetMs=$serverOffset lanes=1,2,3,4 nonce=$proofNonce",
            )
        } catch (exc: Exception) {
            Log.e(LOG_TAG, "WAITING_SERVICE_FAILED nonce=$proofNonce", exc)
            failAndStop(VerificationState.NETWORK_ERROR, "${exc.javaClass.simpleName}: ${exc.message ?: "service failed"}", "WAITING_SERVICE_FAILED", startId)
        }
    }

    private fun submitLane(run: Int, lane: MibuLane, deviceId: String) {
        if (run != generation.get()) return
        val requestedAt = System.currentTimeMillis() + stateStore.serverClockOffset()
        stateStore.setVerificationState(VerificationState.REQUESTS_RUNNING)
        stateStore.setLaneStatus(lane.number, LaneStatus.REQUESTING)
        updateNotification("Sending lane ${lane.number} • ${completedLaneCount()}/4 results")

        val token = tokenStore.tokenForLane(lane.number)
        val result = when {
            token == null -> XiaomiApiResult(XiaomiResultKind.COOKIE_EXPIRED, message = "Capture expired before lane ${lane.number}")
            !isCellularReady() -> XiaomiApiResult(XiaomiResultKind.NETWORK_ERROR, message = "Mobile data was not active for lane ${lane.number}")
            else -> client.submit(token, deviceId).let { submitted ->
                if (submitted.kind == XiaomiResultKind.APPROVED || submitted.kind == XiaomiResultKind.MAYBE_APPROVED) {
                    val verified = client.checkStatus(token, deviceId)
                    if (verified.kind == XiaomiResultKind.ALREADY_APPROVED) verified else submitted
                } else {
                    submitted
                }
            }
        }
        val respondedAt = System.currentTimeMillis() + stateStore.serverClockOffset()
        stateStore.saveLaneResult(lane.number, result, requestedAt, respondedAt)
        logStore.add("Lane ${lane.number} result: ${result.message}")
        Log.i(
            LOG_TAG,
            "LANE_RESULT lane=${lane.number} kind=${result.kind} code=${result.code} apply=${result.applyResult} nonce=$proofNonce",
        )
        evaluateResults()
    }

    private fun evaluateResults() = synchronized(resultLock) {
        val statuses = stateStore.lanes().map { it.status }
        val complete = statuses.count { it.isTerminalLaneResult() }
        updateNotification("Requests running • $complete/4 verified server results")
        if (statuses.any { it == LaneStatus.APPROVED }) {
            finishReady("Xiaomi accepted the request; continue with Mi Unlock Status", "WAITING_SERVICE_COMPLETE")
            return@synchronized
        }
        if (complete < MibuLane.defaultLanes().size) return@synchronized

        val state = when {
            statuses.any { it == LaneStatus.LIMIT_REACHED } -> VerificationState.QUOTA_LIMIT_REACHED
            statuses.any { it == LaneStatus.BLOCKED_UNTIL_DEADLINE } -> VerificationState.BLOCKED_UNTIL_DEADLINE
            statuses.any { it == LaneStatus.COOKIE_EXPIRED } -> VerificationState.COOKIE_EXPIRED
            statuses.any { it == LaneStatus.REJECTED } -> VerificationState.REQUEST_REJECTED
            statuses.any { it == LaneStatus.NETWORK_ERROR } -> VerificationState.NETWORK_ERROR
            else -> VerificationState.UNKNOWN
        }
        stateStore.setVerificationState(state)
        stateStore.setServiceRunning(false)
        updateNotification("Finished • ${state.friendlyServerState()}")
        Log.i(LOG_TAG, "WAITING_SERVICE_FINISHED state=${state.name} nonce=$proofNonce")
        logStore.add("Request cycle finished: ${state.friendlyServerState()}")
        scheduleStop()
    }

    private fun finishReady(message: String, marker: String) {
        stateStore.completeVerification(VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION)
        stateStore.setServiceRunning(false)
        updateNotification("Request accepted • continue with Mi Unlock Status")
        logStore.add(message)
        Log.i(LOG_TAG, "$marker state=READY_FOR_MI_UNLOCK_VERIFICATION nonce=$proofNonce")
        scheduleStop()
    }

    private fun failAndStop(state: VerificationState, message: String, marker: String, startId: Int) {
        if (state.isAuthoritativeResult()) stateStore.completeVerification(state) else stateStore.setVerificationState(state)
        stateStore.setServiceRunning(false)
        updateNotification(message.take(100))
        logStore.add(message)
        Log.w(LOG_TAG, "$marker state=${state.name} nonce=$proofNonce")
        scheduler.schedule({ stopSelf(startId) }, 2L, TimeUnit.SECONDS)
    }

    private fun scheduleHeartbeat(run: Int) {
        scheduled += scheduler.scheduleAtFixedRate({
            if (run == generation.get()) stateStore.heartbeat()
        }, 0L, 5L, TimeUnit.SECONDS)
    }

    private fun scheduleStop() {
        scheduled += scheduler.schedule({ stopSelf() }, 15L, TimeUnit.SECONDS)
    }

    private fun completedLaneCount(): Int = stateStore.lanes().count { it.status.isTerminalLaneResult() }

    private fun isCellularReady(): Boolean {
        val manager = getSystemService(ConnectivityManager::class.java)
        val active = manager.activeNetwork ?: return false
        val caps = manager.getNetworkCapabilities(active) ?: return false
        return caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) &&
            caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
            caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }

    private fun generateDeviceId(laneNumber: Int): String {
        val seed = "${UUID.randomUUID()}-$laneNumber-${System.nanoTime()}".toByteArray(Charsets.UTF_8)
        return MessageDigest.getInstance("SHA-1").digest(seed).joinToString("") { "%02X".format(it) }
    }

    private fun cancelScheduled() {
        scheduled.forEach { it.cancel(false) }
        scheduled.clear()
    }

    private fun acquireWakeLock(timeoutMs: Long) {
        wakeLock?.let { if (it.isHeld) it.release() }
        val power = getSystemService(PowerManager::class.java)
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "MIBU:XiaomiRequestWindow").apply {
            setReferenceCounted(false)
            acquire(timeoutMs.coerceAtMost(TokenStore.MAX_TOKEN_AGE_MS + 120_000L))
        }
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getSystemService(NotificationManager::class.java).createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "MIBU Xiaomi request service", NotificationManager.IMPORTANCE_LOW),
            )
        }
    }

    private fun updateNotification(message: String) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification(message))
    }

    private fun buildNotification(message: String): Notification {
        val pending = PendingIntent.getActivity(
            this,
            49,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("MIBU Xiaomi request assistant")
            .setContentText(message)
            .setSmallIcon(R.drawable.ic_mibu)
            .setContentIntent(pending)
            .setOngoing(stateStore.serviceRunning())
            .build()
    }

    override fun onDestroy() {
        generation.incrementAndGet()
        cancelScheduled()
        stateStore.setServiceRunning(false)
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        preparation.shutdownNow()
        scheduler.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun LaneStatus.isTerminalLaneResult(): Boolean = when (this) {
        LaneStatus.APPROVED,
        LaneStatus.MAYBE_APPROVED_RECHECK,
        LaneStatus.LIMIT_REACHED,
        LaneStatus.BLOCKED_UNTIL_DEADLINE,
        LaneStatus.COOKIE_EXPIRED,
        LaneStatus.COMMUNITY_GATE,
        LaneStatus.NETWORK_ERROR,
        LaneStatus.REJECTED,
        LaneStatus.UNKNOWN -> true
        else -> false
    }

    private fun XiaomiApiResult.toVerificationState(): VerificationState = when (kind) {
        XiaomiResultKind.ALREADY_APPROVED,
        XiaomiResultKind.APPROVED -> VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION
        XiaomiResultKind.LIMIT_REACHED -> VerificationState.QUOTA_LIMIT_REACHED
        XiaomiResultKind.BLOCKED,
        XiaomiResultKind.ACCOUNT_TOO_NEW -> VerificationState.BLOCKED_UNTIL_DEADLINE
        XiaomiResultKind.COOKIE_EXPIRED -> VerificationState.COOKIE_EXPIRED
        XiaomiResultKind.REJECTED -> VerificationState.REQUEST_REJECTED
        XiaomiResultKind.NETWORK_ERROR -> VerificationState.NETWORK_ERROR
        else -> VerificationState.UNKNOWN
    }

    private fun VerificationState.friendlyServerState(): String = name.lowercase().replace('_', ' ')

    companion object {
        private const val CHANNEL_ID = "mibu_xiaomi_request"
        private const val NOTIFICATION_ID = 49
        private const val LOG_TAG = "MIBU_SERVICE"
        private const val LATE_TOLERANCE_MS = 2_000L
    }
}
