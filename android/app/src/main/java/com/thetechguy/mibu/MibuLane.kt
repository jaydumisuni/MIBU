package com.thetechguy.mibu

import java.time.ZoneId
import java.time.ZonedDateTime

enum class LaneStatus {
    PENDING,
    ARMED,
    FIRED,
    APPROVED,
    MAYBE_APPROVED_RECHECK,
    LIMIT_REACHED,
    BLOCKED_UNTIL_DEADLINE,
    COOKIE_EXPIRED,
    COMMUNITY_GATE,
    NETWORK_ERROR,
    UNKNOWN
}

enum class CommunityDeviceState {
    COMMUNITY_DEVICE_CONFIRMED,
    COMMUNITY_DEVICE_NOT_FOUND,
    COMMUNITY_ROUTE_NOT_REQUIRED,
    COMMUNITY_ROUTE_UNKNOWN
}

enum class VerificationState {
    NOT_STARTED,
    REQUEST_STAGE_COMPLETE,
    READY_FOR_MI_UNLOCK_VERIFICATION,
    WAIT_TIME_SHOWN,
    ACCOUNT_DEVICE_NOT_ADDED,
    COMMUNITY_AUTH_REQUIRED,
    UNLOCKED,
    UNKNOWN
}

data class MibuLane(
    val number: Int,
    val sourceLabel: String,
    val offsetMs: Long,
    val status: LaneStatus = LaneStatus.PENDING
) {
    fun targetTime(nowChina: ZonedDateTime = ZonedDateTime.now(CHINA_ZONE)): ZonedDateTime {
        val midnightToday = nowChina.toLocalDate().atStartOfDay(CHINA_ZONE)
        val targetToday = midnightToday.minusNanos(offsetMs * 1_000_000L)
        return if (targetToday.isAfter(nowChina)) {
            targetToday
        } else {
            midnightToday.plusDays(1).minusNanos(offsetMs * 1_000_000L)
        }
    }

    fun summary(): String = "Lane $number • $sourceLabel • ${offsetMs}ms • $status"

    companion object {
        val CHINA_ZONE: ZoneId = ZoneId.of("Asia/Shanghai")
        fun defaultLanes(): List<MibuLane> = listOf(
            MibuLane(1, "Firefox service token", 1400),
            MibuLane(2, "Chrome pop token", 900),
            MibuLane(3, "Firefox service token", 400),
            MibuLane(4, "Chrome pop token", 100)
        )
    }
}
