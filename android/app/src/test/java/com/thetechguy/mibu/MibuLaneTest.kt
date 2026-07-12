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
        assertEquals(12, target.dayOfMonth)
        assertEquals(23, target.hour)
        assertEquals(59, target.minute)
        assertEquals(58, target.second)
        assertEquals(600_000_000, target.nano)
        assertTrue(target.isAfter(now))
    }

    @Test
    fun allLanesRollTogetherAfterEarliestWindowPassed() {
        val now = ZonedDateTime.of(2026, 7, 12, 23, 59, 58, 800_000_000, china)
        val targets = MibuLane.defaultLanes().map { it.targetTime(now) }
        assertEquals(setOf(13), targets.map { it.dayOfMonth }.toSet())
        assertTrue(targets.all { it.isAfter(now) })
        assertTrue(targets.zipWithNext().all { (a, b) -> a.isBefore(b) })
    }

    @Test
    fun eachLaneProducesExpectedSubSecondTarget() {
        val now = ZonedDateTime.of(2026, 7, 12, 12, 0, 0, 0, china)
        val targets = MibuLane.defaultLanes().map { it.targetTime(now) }
        assertEquals(listOf(58, 59, 59, 59), targets.map { it.second })
        assertEquals(listOf(600_000_000, 100_000_000, 600_000_000, 900_000_000), targets.map { it.nano })
        assertEquals(1, targets.map { it.toLocalDate() }.toSet().size)
    }

    @Test
    fun targetMidnightUsesChinaZoneEvenWhenInputZoneDiffers() {
        val utcNow = ZonedDateTime.of(2026, 7, 12, 15, 50, 0, 0, ZoneId.of("UTC"))
        val midnight = MibuLane.nextTargetMidnight(utcNow)
        assertEquals(china, midnight.zone)
        assertEquals(0, midnight.hour)
        assertEquals(0, midnight.minute)
    }
}
