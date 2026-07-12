package com.thetechguy.mibu

import java.time.ZoneId
import java.time.ZonedDateTime

enum class LaneStatus {
    PENDING,
    ARMED,
    WINDOW_REACHED,
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
    WAITING_ARMED,
    TIMING_WINDOW_REACHED,
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
        return targetTimeForMidnight(nextTargetMidnight(nowChina))
    }

    fun targetTimeForMidnight(targetMidnight: ZonedDateTime): ZonedDateTime {
        require(targetMidnight.zone == CHINA_ZONE) { "Target midnight must use Asia/Shanghai" }
        return targetMidnight.minusNanos(offsetMs * 1_000_000L)
    }

    fun summary(): String = "Lane $number • $sourceLabel • ${offsetMs}ms • $status"

    companion object {
        val CHINA_ZONE: ZoneId = ZoneId.of("Asia/Shanghai")
        private const val EARLIEST_OFFSET_MS = 1400L

        fun nextTargetMidnight(nowChina: ZonedDateTime = ZonedDateTime.now(CHINA_ZONE)): ZonedDateTime {
            val normalizedNow = nowChina.withZoneSameInstant(CHINA_ZONE)
            var upcomingMidnight = normalizedNow.toLocalDate().plusDays(1).atStartOfDay(CHINA_ZONE)
            val earliestWindow = upcomingMidnight.minusNanos(EARLIEST_OFFSET_MS * 1_000_000L)
            if (!normalizedNow.isBefore(earliestWindow)) {
                upcomingMidnight = upcomingMidnight.plusDays(1)
            }
            return upcomingMidnight
        }

        fun defaultLanes(): List<MibuLane> = listOf(
            MibuLane(1, "Firefox service token", 1400),
            MibuLane(2, "Chrome pop token", 900),
            MibuLane(3, "Firefox service token", 400),
            MibuLane(4, "Chrome pop token", 100)
        )
    }
}
