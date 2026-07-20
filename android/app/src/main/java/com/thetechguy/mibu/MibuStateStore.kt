package com.thetechguy.mibu

import android.content.Context
import java.time.Instant
import java.time.ZonedDateTime

class MibuStateStore(context: Context) {
    private val prefs = context.getSharedPreferences("mibu_state", Context.MODE_PRIVATE)

    fun setCommunityState(state: CommunityDeviceState) {
        prefs.edit().putString(KEY_COMMUNITY, state.name).apply()
    }

    fun communityState(): CommunityDeviceState {
        val raw = prefs.getString(KEY_COMMUNITY, CommunityDeviceState.COMMUNITY_ROUTE_UNKNOWN.name)
        return runCatching { CommunityDeviceState.valueOf(raw ?: CommunityDeviceState.COMMUNITY_ROUTE_UNKNOWN.name) }
            .getOrDefault(CommunityDeviceState.COMMUNITY_ROUTE_UNKNOWN)
    }

    fun setVerificationState(state: VerificationState) {
        prefs.edit().putString(KEY_VERIFY, state.name).apply()
    }

    fun verificationState(): VerificationState {
        val raw = prefs.getString(KEY_VERIFY, VerificationState.NOT_STARTED.name)
        val stored = runCatching { VerificationState.valueOf(raw ?: VerificationState.NOT_STARTED.name) }
            .getOrDefault(VerificationState.NOT_STARTED)
        if (stored == VerificationState.UNLOCKED && readBootloaderLocked() == true) {
            prefs.edit().putString(KEY_VERIFY, VerificationState.UNKNOWN.name).apply()
            return VerificationState.UNKNOWN
        }
        return stored
    }

    fun armWaiting(targetMidnight: ZonedDateTime) {
        require(targetMidnight.zone == MibuLane.CHINA_ZONE) { "Waiting target must use Asia/Shanghai" }
        val edit = prefs.edit()
        MibuLane.defaultLanes().forEach { lane ->
            edit.putString(laneKey(lane.number), LaneStatus.ARMED.name)
        }
        edit.putLong(KEY_TARGET_MIDNIGHT_EPOCH_MS, targetMidnight.toInstant().toEpochMilli())
        edit.putString(KEY_VERIFY, VerificationState.WAITING_ARMED.name)
        edit.putBoolean(KEY_SERVICE_RUNNING, false)
        edit.apply()
    }

    fun beginPreflight(targetMidnight: ZonedDateTime) {
        require(targetMidnight.zone == MibuLane.CHINA_ZONE) { "Waiting target must use Asia/Shanghai" }
        prefs.edit()
            .putLong(KEY_TARGET_MIDNIGHT_EPOCH_MS, targetMidnight.toInstant().toEpochMilli())
            .putString(KEY_VERIFY, VerificationState.PREFLIGHT_CHECKING.name)
            .apply()
    }

    fun waitingTargetMidnight(): ZonedDateTime? {
        val epochMs = prefs.getLong(KEY_TARGET_MIDNIGHT_EPOCH_MS, 0L)
        if (epochMs <= 0L) return null
        return Instant.ofEpochMilli(epochMs).atZone(MibuLane.CHINA_ZONE)
    }

    @Suppress("UNUSED_PARAMETER")
    fun reconcileTimingState(nowChina: ZonedDateTime = ZonedDateTime.now(MibuLane.CHINA_ZONE)): VerificationState =
        verificationState()

    fun clearWaitingTarget() {
        prefs.edit().remove(KEY_TARGET_MIDNIGHT_EPOCH_MS).apply()
    }

    fun completeVerification(state: VerificationState) {
        require(state.isAuthoritativeResult()) { "State $state is not an authoritative verification result" }
        prefs.edit()
            .putString(KEY_VERIFY, state.name)
            .remove(KEY_TARGET_MIDNIGHT_EPOCH_MS)
            .putBoolean(KEY_SERVICE_RUNNING, false)
            .apply()
    }

    fun resetWorkflow() {
        val edit = prefs.edit()
            .putString(KEY_VERIFY, VerificationState.NOT_STARTED.name)
            .remove(KEY_TARGET_MIDNIGHT_EPOCH_MS)
            .remove(KEY_SERVER_CLOCK_OFFSET_MS)
            .putBoolean(KEY_SERVICE_RUNNING, false)
            .remove(KEY_SERVICE_HEARTBEAT_MS)
        MibuLane.defaultLanes().forEach { lane ->
            edit.putString(laneKey(lane.number), LaneStatus.PENDING.name)
                .remove(laneMessageKey(lane.number))
                .remove(laneCodeKey(lane.number))
                .remove(laneApplyKey(lane.number))
                .remove(laneDeadlineKey(lane.number))
                .remove(laneRequestKey(lane.number))
                .remove(laneResponseKey(lane.number))
        }
        edit.apply()
    }

    fun setLaneStatus(laneNumber: Int, status: LaneStatus) {
        require(laneNumber in 1..MibuLane.defaultLanes().size) { "Unknown lane number: $laneNumber" }
        prefs.edit().putString(laneKey(laneNumber), status.name).apply()
    }

    fun laneStatus(laneNumber: Int): LaneStatus {
        val raw = prefs.getString(laneKey(laneNumber), LaneStatus.PENDING.name)
        return runCatching { LaneStatus.valueOf(raw ?: LaneStatus.PENDING.name) }.getOrDefault(LaneStatus.PENDING)
    }

    fun lanes(): List<MibuLane> = MibuLane.defaultLanes().map { it.copy(status = laneStatus(it.number)) }

    fun laneSummary(): String = lanes().joinToString("\n") { it.summary() }

    fun saveLaneResult(laneNumber: Int, result: XiaomiApiResult, requestedAtMs: Long = 0L, respondedAtMs: Long = 0L) {
        require(laneNumber in 1..MibuLane.defaultLanes().size) { "Unknown lane number: $laneNumber" }
        prefs.edit()
            .putString(laneKey(laneNumber), result.laneStatus().name)
            .putString(laneMessageKey(laneNumber), result.message.take(MAX_RESULT_MESSAGE))
            .putInt(laneCodeKey(laneNumber), result.code ?: Int.MIN_VALUE)
            .putInt(laneApplyKey(laneNumber), result.applyResult ?: Int.MIN_VALUE)
            .putString(laneDeadlineKey(laneNumber), result.deadline)
            .putLong(laneRequestKey(laneNumber), requestedAtMs)
            .putLong(laneResponseKey(laneNumber), respondedAtMs)
            .apply()
    }

    fun laneResultSummary(laneNumber: Int): String {
        val status = laneStatus(laneNumber).name
        val code = prefs.getInt(laneCodeKey(laneNumber), Int.MIN_VALUE).takeIf { it != Int.MIN_VALUE }
        val apply = prefs.getInt(laneApplyKey(laneNumber), Int.MIN_VALUE).takeIf { it != Int.MIN_VALUE }
        val deadline = prefs.getString(laneDeadlineKey(laneNumber), "").orEmpty()
        val message = prefs.getString(laneMessageKey(laneNumber), "").orEmpty()
        return buildString {
            append(status)
            code?.let { append(" code=").append(it) }
            apply?.let { append(" apply=").append(it) }
            if (deadline.isNotBlank()) append(" deadline=").append(deadline)
            if (message.isNotBlank()) append(" ").append(message)
        }
    }

    fun setServerClockOffset(offsetMs: Long) {
        prefs.edit().putLong(KEY_SERVER_CLOCK_OFFSET_MS, offsetMs).apply()
    }

    fun serverClockOffset(): Long = prefs.getLong(KEY_SERVER_CLOCK_OFFSET_MS, 0L)

    fun setServiceRunning(running: Boolean) {
        prefs.edit()
            .putBoolean(KEY_SERVICE_RUNNING, running)
            .putLong(KEY_SERVICE_HEARTBEAT_MS, System.currentTimeMillis())
            .apply()
    }

    fun serviceRunning(): Boolean {
        if (!prefs.getBoolean(KEY_SERVICE_RUNNING, false)) return false
        val heartbeat = prefs.getLong(KEY_SERVICE_HEARTBEAT_MS, 0L)
        return heartbeat > 0L && System.currentTimeMillis() - heartbeat < SERVICE_HEARTBEAT_STALE_MS
    }

    fun heartbeat() {
        if (prefs.getBoolean(KEY_SERVICE_RUNNING, false)) {
            prefs.edit().putLong(KEY_SERVICE_HEARTBEAT_MS, System.currentTimeMillis()).apply()
        }
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_COMMUNITY = "community_state"
        private const val KEY_VERIFY = "verification_state"
        private const val KEY_TARGET_MIDNIGHT_EPOCH_MS = "target_midnight_epoch_ms"
        private const val KEY_SERVER_CLOCK_OFFSET_MS = "server_clock_offset_ms"
        private const val KEY_SERVICE_RUNNING = "service_running"
        private const val KEY_SERVICE_HEARTBEAT_MS = "service_heartbeat_ms"
        private const val SERVICE_HEARTBEAT_STALE_MS = 15_000L
        private const val MAX_RESULT_MESSAGE = 220
        private fun laneKey(number: Int): String = "lane_${number}_status"
        private fun laneMessageKey(number: Int): String = "lane_${number}_message"
        private fun laneCodeKey(number: Int): String = "lane_${number}_code"
        private fun laneApplyKey(number: Int): String = "lane_${number}_apply"
        private fun laneDeadlineKey(number: Int): String = "lane_${number}_deadline"
        private fun laneRequestKey(number: Int): String = "lane_${number}_request_ms"
        private fun laneResponseKey(number: Int): String = "lane_${number}_response_ms"

        fun parseBootloaderLocked(raw: String): Boolean? = when (raw.trim().lowercase()) {
            "1", "locked" -> true
            "0", "unlocked" -> false
            else -> null
        }

        private fun readBootloaderLocked(): Boolean? = runCatching {
            val process = ProcessBuilder("/system/bin/getprop", "ro.boot.flash.locked")
                .redirectErrorStream(true)
                .start()
            val raw = process.inputStream.bufferedReader().use { it.readText() }
            process.waitFor()
            parseBootloaderLocked(raw)
        }.getOrNull()
    }
}
