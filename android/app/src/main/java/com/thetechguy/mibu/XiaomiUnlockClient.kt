package com.thetechguy.mibu

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

enum class XiaomiResultKind {
    ELIGIBLE,
    ALREADY_APPROVED,
    APPROVED,
    MAYBE_APPROVED,
    LIMIT_REACHED,
    BLOCKED,
    ACCOUNT_TOO_NEW,
    COOKIE_EXPIRED,
    REJECTED,
    UNKNOWN,
    NETWORK_ERROR,
}

data class XiaomiApiResult(
    val kind: XiaomiResultKind,
    val code: Int? = null,
    val isPass: Int? = null,
    val buttonState: Int? = null,
    val applyResult: Int? = null,
    val deadline: String = "",
    val message: String,
    val serverEpochMs: Long? = null,
    val clockOffsetMs: Long? = null,
) {
    fun laneStatus(): LaneStatus = when (kind) {
        XiaomiResultKind.ELIGIBLE -> LaneStatus.PREFLIGHT_OK
        XiaomiResultKind.ALREADY_APPROVED,
        XiaomiResultKind.APPROVED -> LaneStatus.APPROVED
        XiaomiResultKind.MAYBE_APPROVED -> LaneStatus.MAYBE_APPROVED_RECHECK
        XiaomiResultKind.LIMIT_REACHED -> LaneStatus.LIMIT_REACHED
        XiaomiResultKind.BLOCKED,
        XiaomiResultKind.ACCOUNT_TOO_NEW -> LaneStatus.BLOCKED_UNTIL_DEADLINE
        XiaomiResultKind.COOKIE_EXPIRED -> LaneStatus.COOKIE_EXPIRED
        XiaomiResultKind.REJECTED -> LaneStatus.REJECTED
        XiaomiResultKind.NETWORK_ERROR -> LaneStatus.NETWORK_ERROR
        XiaomiResultKind.UNKNOWN -> LaneStatus.UNKNOWN
    }
}

class XiaomiUnlockClient(
    private val statusUrl: String = STATUS_URL,
    private val applyUrl: String = APPLY_URL,
) {
    fun checkStatus(token: String, deviceId: String): XiaomiApiResult = request(
        method = "GET",
        endpoint = statusUrl,
        token = token,
        deviceId = deviceId,
        body = null,
        parser = ::parseStatusResponse,
    )

    fun submit(token: String, deviceId: String): XiaomiApiResult = request(
        method = "POST",
        endpoint = applyUrl,
        token = token,
        deviceId = deviceId,
        body = "{\"is_retry\":true}".toByteArray(Charsets.UTF_8),
        parser = ::parseApplyResponse,
    )

    private fun request(
        method: String,
        endpoint: String,
        token: String,
        deviceId: String,
        body: ByteArray?,
        parser: (String) -> XiaomiApiResult,
    ): XiaomiApiResult {
        if (!TokenStore.isAcceptableToken(token)) {
            return XiaomiApiResult(XiaomiResultKind.COOKIE_EXPIRED, message = "Capture is missing or malformed")
        }
        val startedAt = System.currentTimeMillis()
        var connection: HttpURLConnection? = null
        return try {
            connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = method
                connectTimeout = 5_000
                readTimeout = 15_000
                useCaches = false
                instanceFollowRedirects = false
                setRequestProperty("Cookie", cookieHeader(token, deviceId))
                setRequestProperty("User-Agent", "okhttp/4.12.0")
                setRequestProperty("Accept", "application/json")
                setRequestProperty("Accept-Encoding", "identity")
                if (body != null) {
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    setFixedLengthStreamingMode(body.size)
                    outputStream.use { it.write(body) }
                }
            }
            val httpCode = connection.responseCode
            val finishedAt = System.currentTimeMillis()
            val raw = (if (httpCode in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            val parsed = parser(raw)
            val serverTime = connection.date.takeIf { it > 0L }
            val midpoint = startedAt + ((finishedAt - startedAt) / 2L)
            parsed.copy(
                serverEpochMs = serverTime,
                clockOffsetMs = serverTime?.minus(midpoint),
                message = if (httpCode in 200..299) parsed.message else "HTTP $httpCode: ${parsed.message}",
            )
        } catch (exc: Exception) {
            XiaomiApiResult(
                XiaomiResultKind.NETWORK_ERROR,
                message = "${exc.javaClass.simpleName}: ${exc.message ?: "request failed"}",
            )
        } finally {
            connection?.disconnect()
        }
    }

    companion object {
        const val STATUS_URL = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
        const val APPLY_URL = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"

        internal fun cookieHeader(token: String, deviceId: String): String =
            "new_bbs_serviceToken=$token;versionCode=500411;versionName=5.4.11;deviceId=$deviceId;"

        fun parseStatusResponse(raw: String): XiaomiApiResult {
            val json = runCatching { JSONObject(raw) }.getOrElse {
                return XiaomiApiResult(XiaomiResultKind.UNKNOWN, message = "Status response was not valid JSON")
            }
            val code = json.optIntOrNull("code")
            if (code == 100004) {
                return XiaomiApiResult(XiaomiResultKind.COOKIE_EXPIRED, code = code, message = "Browser capture expired")
            }
            val data = json.optJSONObject("data") ?: JSONObject()
            val isPass = data.optIntOrNull("is_pass")
            val buttonState = data.optIntOrNull("button_state")
            val deadline = data.optString("deadline_format", "")
            val kind = when {
                code != 0 -> XiaomiResultKind.UNKNOWN
                isPass == 1 -> XiaomiResultKind.ALREADY_APPROVED
                isPass == 4 && buttonState == 1 -> XiaomiResultKind.ELIGIBLE
                isPass == 4 && buttonState == 2 -> XiaomiResultKind.BLOCKED
                isPass == 4 && buttonState == 3 -> XiaomiResultKind.ACCOUNT_TOO_NEW
                else -> XiaomiResultKind.UNKNOWN
            }
            val message = when (kind) {
                XiaomiResultKind.ALREADY_APPROVED -> "Request is already approved${deadlineSuffix(deadline)}"
                XiaomiResultKind.ELIGIBLE -> "Account is eligible to submit"
                XiaomiResultKind.BLOCKED -> "Requests are blocked${deadlineSuffix(deadline)}"
                XiaomiResultKind.ACCOUNT_TOO_NEW -> "Account is not old enough to submit"
                else -> "Unknown account status (code=${code ?: "missing"}, is_pass=${isPass ?: "missing"}, button_state=${buttonState ?: "missing"})"
            }
            return XiaomiApiResult(kind, code, isPass, buttonState, deadline = deadline, message = message)
        }

        fun parseApplyResponse(raw: String): XiaomiApiResult {
            val json = runCatching { JSONObject(raw) }.getOrElse {
                return XiaomiApiResult(XiaomiResultKind.UNKNOWN, message = "Apply response was not valid JSON")
            }
            val code = json.optIntOrNull("code")
            val data = json.optJSONObject("data") ?: JSONObject()
            val applyResult = data.optIntOrNull("apply_result")
            val deadline = data.optString("deadline_format", "")
            val kind = when {
                code == 100004 -> XiaomiResultKind.COOKIE_EXPIRED
                code == 100003 -> XiaomiResultKind.MAYBE_APPROVED
                code == 100001 -> XiaomiResultKind.REJECTED
                code == 0 && applyResult == 1 -> XiaomiResultKind.APPROVED
                code == 0 && applyResult == 3 -> XiaomiResultKind.LIMIT_REACHED
                code == 0 && applyResult == 4 -> XiaomiResultKind.BLOCKED
                else -> XiaomiResultKind.UNKNOWN
            }
            val message = when (kind) {
                XiaomiResultKind.APPROVED -> "Request approved; status verification required"
                XiaomiResultKind.MAYBE_APPROVED -> "Request may be approved; checking status"
                XiaomiResultKind.LIMIT_REACHED -> "Application quota limit reached${deadlineSuffix(deadline)}"
                XiaomiResultKind.BLOCKED -> "Request blocked${deadlineSuffix(deadline)}"
                XiaomiResultKind.COOKIE_EXPIRED -> "Browser capture expired"
                XiaomiResultKind.REJECTED -> "Request rejected by Xiaomi"
                else -> "Unknown apply result (code=${code ?: "missing"}, apply_result=${applyResult ?: "missing"})"
            }
            return XiaomiApiResult(kind, code = code, applyResult = applyResult, deadline = deadline, message = message)
        }

        private fun JSONObject.optIntOrNull(name: String): Int? =
            if (has(name) && !isNull(name)) optInt(name) else null

        private fun deadlineSuffix(deadline: String): String =
            if (deadline.isBlank()) "" else " until $deadline"
    }
}
