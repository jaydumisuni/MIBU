package com.thetechguy.mibu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TokenStoreContractTest {
    @Test
    fun freshCaptureReceivesExactlyThirtyMinutes() {
        val now = 10_000L
        assertEquals(TokenStore.MAX_TOKEN_AGE_MS, TokenStore.remainingMillis(now, now))
    }

    @Test
    fun captureExpiresAtExactBoundary() {
        val captured = 10_000L
        assertEquals(0L, TokenStore.remainingMillis(captured, captured + TokenStore.MAX_TOKEN_AGE_MS))
    }

    @Test
    fun wallClockRollbackFailsClosedInsteadOfExtendingLifetime() {
        assertEquals(0L, TokenStore.remainingMillis(capturedAtMs = 20_000L, nowMs = 19_999L))
    }

    @Test
    fun tokenValidationRejectsControlsAndOversizeValues() {
        assertTrue(TokenStore.isAcceptableToken("abcdefgh"))
        assertTrue(TokenStore.isAcceptableToken("valid-but\nwrapped"))
        assertFalse(TokenStore.isAcceptableToken("short"))
        assertFalse(TokenStore.isAcceptableToken("valid-but\u0000unsafe"))
        assertFalse(TokenStore.isAcceptableToken("x".repeat(TokenStore.MAX_TOKEN_LENGTH + 1)))
    }
}
