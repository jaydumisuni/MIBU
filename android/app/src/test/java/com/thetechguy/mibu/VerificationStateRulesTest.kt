package com.thetechguy.mibu

import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class VerificationStateRulesTest {
    @Test
    fun timingCompletionBlocksASecondWaitingCycle() {
        assertFalse(VerificationState.TIMING_WINDOW_REACHED.isTimingComplete())
        assertTrue(VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION.isTimingComplete())
        assertTrue(VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION.blocksNewWaitingCycle())
    }

    @Test
    fun everyOfficialResultIsAuthoritativeAndBlocksRearm() {
        val results = listOf(
            VerificationState.WAIT_TIME_SHOWN,
            VerificationState.ACCOUNT_DEVICE_NOT_ADDED,
            VerificationState.COMMUNITY_AUTH_REQUIRED,
            VerificationState.UNLOCKED,
        )
        assertTrue(results.all { it.isAuthoritativeResult() })
        assertTrue(results.all { it.blocksNewWaitingCycle() })
    }

    @Test
    fun notStartedUnknownAndArmedRemainNonAuthoritative() {
        val states = listOf(
            VerificationState.NOT_STARTED,
            VerificationState.UNKNOWN,
            VerificationState.WAITING_ARMED,
        )
        assertTrue(states.none { it.isAuthoritativeResult() })
        assertFalse(VerificationState.WAITING_ARMED.blocksNewWaitingCycle())
    }

    @Test
    fun bootloaderPropertyParserUsesDeviceTruth() {
        assertTrue(MibuStateStore.parseBootloaderLocked("1") == true)
        assertTrue(MibuStateStore.parseBootloaderLocked("unlocked") == false)
        assertNull(MibuStateStore.parseBootloaderLocked(""))
    }
}
