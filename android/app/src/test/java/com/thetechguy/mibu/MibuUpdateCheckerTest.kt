package com.thetechguy.mibu

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MibuUpdateCheckerTest {
    @Test
    fun newerSemanticVersionIsDetected() {
        assertTrue(MibuUpdateChecker.isNewer("0.4.0", "0.3.0-dev"))
        assertTrue(MibuUpdateChecker.isNewer("v1.0.0", "0.3.0"))
    }

    @Test
    fun sameOrOlderVersionIsNotUpdate() {
        assertFalse(MibuUpdateChecker.isNewer("0.3.0", "0.3.0-dev"))
        assertFalse(MibuUpdateChecker.isNewer("0.2.9", "0.3.0"))
    }
}
