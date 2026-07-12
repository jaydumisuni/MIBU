package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle
import android.util.Log

class StatusActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val stateStore by lazy { MibuStateStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        stateStore.reconcileTimingState()
        val laneStates = stateStore.lanes().joinToString(",") { "${it.number}:${it.status.name}" }
        val message = buildString {
            append("STATUS ")
            append("captures=").append(if (tokenStore.hasRequiredCaptures()) "READY" else "NOT_READY")
            append(" verification=").append(stateStore.verificationState().name)
            append(" community=").append(stateStore.communityState().name)
            append(" lanes=").append(laneStates)
        }
        Log.i(LOG_TAG, message)
        setResult(RESULT_OK)
        finish()
    }

    companion object {
        private const val LOG_TAG = "MIBU_STATUS"
    }
}
