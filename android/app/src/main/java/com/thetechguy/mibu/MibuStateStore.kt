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
        return runCatching { VerificationState.valueOf(raw ?: VerificationState.NOT_STARTED.name) }
            .getOrDefault(VerificationState.NOT_STARTED)
    }

    fun armWaiting(targetMidnight: ZonedDateTime) {
        require(targetMidnight.zone == MibuLane.CHINA_ZONE) { "Waiting target must use Asia/Shanghai" }
        val edit = prefs.edit()
        MibuLane.defaultLanes().forEach { lane ->
            edit.putString(laneKey(lane.number), LaneStatus.ARMED.name)
        }
        edit.putLong(KEY_TARGET_MIDNIGHT_EPOCH_MS, targetMidnight.toInstant().toEpochMilli())
        edit.putString(KEY_VERIFY, VerificationState.WAITING_ARMED.name)
        edit.apply()
    }

    fun waitingTargetMidnight(): ZonedDateTime? {
        val epochMs = prefs.getLong(KEY_TARGET_MIDNIGHT_EPOCH_MS, 0L)
        if (epochMs <= 0L) return null
        return Instant.ofEpochMilli(epochMs).atZone(MibuLane.CHINA_ZONE)
    }

    fun reconcileTimingState(nowChina: ZonedDateTime = ZonedDateTime.now(MibuLane.CHINA_ZONE)): VerificationState {
        val targetMidnight = waitingTargetMidnight() ?: return verificationState()
        val normalizedNow = nowChina.withZoneSameInstant(MibuLane.CHINA_ZONE)
        val edit = prefs.edit()
        var reached = 0
        MibuLane.defaultLanes().forEach { lane ->
            val current = laneStatus(lane.number)
            val target = lane.targetTimeForMidnight(targetMidnight)
            val next = if (current == LaneStatus.ARMED && !normalizedNow.isBefore(target)) LaneStatus.WINDOW_REACHED else current
            if (next == LaneStatus.WINDOW_REACHED) reached += 1
            if (next != current) edit.putString(laneKey(lane.number), next.name)
        }
        val verification = if (reached == MibuLane.defaultLanes().size) {
            VerificationState.TIMING_WINDOW_REACHED
        } else {
            VerificationState.WAITING_ARMED
        }
        edit.putString(KEY_VERIFY, verification.name).apply()
        return verification
    }

    fun clearWaitingTarget() {
        prefs.edit().remove(KEY_TARGET_MIDNIGHT_EPOCH_MS).apply()
    }

    fun setLaneStatus(laneNumber: Int, status: LaneStatus) {
        prefs.edit().putString(laneKey(laneNumber), status.name).apply()
    }

    fun laneStatus(laneNumber: Int): LaneStatus {
        val raw = prefs.getString(laneKey(laneNumber), LaneStatus.PENDING.name)
        return runCatching { LaneStatus.valueOf(raw ?: LaneStatus.PENDING.name) }.getOrDefault(LaneStatus.PENDING)
    }

    fun lanes(): List<MibuLane> = MibuLane.defaultLanes().map { it.copy(status = laneStatus(it.number)) }

    fun laneSummary(): String = lanes().joinToString("\n") { it.summary() }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_COMMUNITY = "community_state"
        private const val KEY_VERIFY = "verification_state"
        private const val KEY_TARGET_MIDNIGHT_EPOCH_MS = "target_midnight_epoch_ms"
        private fun laneKey(number: Int): String = "lane_${number}_status"
    }
}
