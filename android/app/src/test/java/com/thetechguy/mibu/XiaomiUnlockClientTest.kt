package com.thetechguy.mibu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class XiaomiUnlockClientTest {
    @Test
    fun bothCaptureSourcesUseTheOriginalWorkerCookieContract() {
        val firefox = XiaomiUnlockClient.cookieHeader("firefox-capture", "DEVICE1")
        val chrome = XiaomiUnlockClient.cookieHeader("chrome-capture", "DEVICE2")

        assertEquals("new_bbs_serviceToken=firefox-capture;versionCode=500411;versionName=5.4.11;deviceId=DEVICE1;", firefox)
        assertEquals("new_bbs_serviceToken=chrome-capture;versionCode=500411;versionName=5.4.11;deviceId=DEVICE2;", chrome)
    }

    @Test
    fun eligibleStatusRequiresExactServerState() {
        val result = XiaomiUnlockClient.parseStatusResponse(
            """{"code":0,"data":{"is_pass":4,"button_state":1}}""",
        )
        assertEquals(XiaomiResultKind.ELIGIBLE, result.kind)
        assertEquals(LaneStatus.PREFLIGHT_OK, result.laneStatus())
    }

    @Test
    fun approvedStatusIsAuthoritative() {
        val result = XiaomiUnlockClient.parseStatusResponse(
            """{"code":0,"data":{"is_pass":1,"button_state":0,"deadline_format":"2026-07-22"}}""",
        )
        assertEquals(XiaomiResultKind.ALREADY_APPROVED, result.kind)
        assertEquals(LaneStatus.APPROVED, result.laneStatus())
    }

    @Test
    fun quotaResponseNeverLooksApproved() {
        val result = XiaomiUnlockClient.parseApplyResponse(
            """{"code":0,"data":{"apply_result":3}}""",
        )
        assertEquals(XiaomiResultKind.LIMIT_REACHED, result.kind)
        assertEquals(LaneStatus.LIMIT_REACHED, result.laneStatus())
    }

    @Test
    fun invalidJsonRemainsUnknown() {
        val result = XiaomiUnlockClient.parseApplyResponse("not-json")
        assertEquals(XiaomiResultKind.UNKNOWN, result.kind)
        assertTrue(result.message.contains("not valid JSON"))
    }
}
