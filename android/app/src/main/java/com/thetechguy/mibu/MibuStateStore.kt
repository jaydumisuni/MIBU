package com.thetechguy.mibu

import android.content.Context

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

    fun armWaiting() {
        val edit = prefs.edit()
        MibuLane.defaultLanes().forEach { lane ->
            edit.putString(laneKey(lane.number), LaneStatus.ARMED.name)
        }
        edit.putString(KEY_VERIFY, VerificationState.NOT_STARTED.name)
        edit.apply()
    }

    fun setLaneStatus(laneNumber: Int, status: LaneStatus) {
        prefs.edit().putString(laneKey(laneNumber), status.name).apply()
    }

    fun laneStatus(laneNumber: Int): LaneStatus {
        val raw = prefs.getString(laneKey(laneNumber), LaneStatus.PENDING.name)
        return runCatching { LaneStatus.valueOf(raw ?: LaneStatus.PENDING.name) }.getOrDefault(LaneStatus.PENDING)
    }

    fun lanes(): List<MibuLane> {
        return MibuLane.defaultLanes().map { it.copy(status = laneStatus(it.number)) }
    }

    fun laneSummary(): String = lanes().joinToString("\n") { it.summary() }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_COMMUNITY = "community_state"
        private const val KEY_VERIFY = "verification_state"
        private fun laneKey(number: Int): String = "lane_${number}_status"
    }
}
