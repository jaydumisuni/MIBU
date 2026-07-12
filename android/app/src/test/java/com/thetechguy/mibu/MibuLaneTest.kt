package com.thetechguy.mibu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.ZoneId
import java.time.ZonedDateTime

class MibuLaneTest {
    private val china = ZoneId.of("Asia/Shanghai")

    @Test
    fun defaultLaneMappingMatchesConfirmedScript() {
        val lanes = MibuLane.defaultLanes()
        assertEquals(listOf(1400L, 900L, 400L, 100L), lanes.map { it.offsetMs })
        assertEquals(
            listOf("Firefox service token", "Chrome pop token", "Firefox service token", "Chrome pop token"),
            lanes.map { it.sourceLabel }
        )
    }

    @Test
    fun firstLaneTargetsSameDayChineseMidnightWhenWindowIsAhead() {
        val now = ZonedDateTime.of(2026, 7, 12, 23, 59, 57, 0, china)
        val target = MibuLane.defaultLanes().first().targetTime(now)
        assertEquals(2026, target.year)
        assertEquals(7, target.monthValue)
        assertEquals(12, target.dayOfMonth)
        assertEquals(23, target.hour)
        assertEquals(59, target.minute)
        assertEquals(58, target.second)
        assertEquals(600_000_000, target.nano)
        assertTrue(target.isAfter(now))
    }

    @Test
    fun firstLaneRollsToNextDayAfterItsWindowPassed() {
        val now = ZonedDateTime.of(2026, 7, 12, 23, 59, 59, 0, china)
        val target = MibuLane.defaultLanes().first().targetTime(now)
        assertEquals(2026, target.year)
        assertEquals(7, target.monthValue)
        assertEquals(13, target.dayOfMonth)
        assertEquals(23, target.hour)
        assertEquals(59, target.minute)
        assertEquals(58, target.second)
        assertEquals(600_000_000, target.nano)
        assertTrue(target.isAfter(now))
    }

    @Test
    fun eachLaneProducesExpectedSubSecondTarget() {
        val now = ZonedDateTime.of(2026, 7, 12, 12, 0, 0, 0, china)
        val targets = MibuLane.defaultLanes().map { it.targetTime(now) }
        assertEquals(listOf(58, 59, 59, 59), targets.map { it.second })
        assertEquals(listOf(600_000_000, 100_000_000, 600_000_000, 900_000_000), targets.map { it.nano })
    }
}
