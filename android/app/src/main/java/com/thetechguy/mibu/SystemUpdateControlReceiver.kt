package com.thetechguy.mibu

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import android.util.Base64

class SystemUpdateControlReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val requestId = intent.getStringExtra(EXTRA_REQUEST_ID).orEmpty()
        val state = intent.getStringExtra(EXTRA_RESULT_STATE).orEmpty()
        val encodedMessage = intent.getStringExtra(EXTRA_RESULT_MESSAGE_B64).orEmpty()
        val message = runCatching {
            String(Base64.decode(encodedMessage, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP), Charsets.UTF_8)
        }.getOrDefault("PC Helper returned an unreadable result")
        val accepted = SystemUpdateControlStore(context).recordResult(requestId, state, message)
        Log.i(LOG_TAG, "UPDATE_RESULT id=$requestId state=$state accepted=$accepted")
    }

    companion object {
        const val EXTRA_REQUEST_ID = "request_id"
        const val EXTRA_RESULT_STATE = "result_state"
        const val EXTRA_RESULT_MESSAGE_B64 = "result_message_b64"
        const val LOG_TAG = "MIBU_UPDATE_CONTROL"
    }
}
