package com.thetechguy.mibu

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.text.InputFilter
import android.text.InputType
import android.util.Base64
import android.util.Log
import android.widget.EditText
import android.widget.LinearLayout

class TokenImportActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val proofNonce by lazy { ProofNonce.from(intent) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val serviceToken = decodeExtra("mibu_service_token_b64")
            .ifBlank { intent?.getStringExtra("mibu_service_token")?.trim().orEmpty() }
        val popToken = decodeExtra("mibu_pop_token_b64")
            .ifBlank { intent?.getStringExtra("mibu_pop_token")?.trim().orEmpty() }
        val pushedToken = decodeExtra("mibu_session_token_b64")
            .ifBlank { intent?.getStringExtra("mibu_session_token")?.trim().orEmpty() }

        if (TokenStore.isAcceptableToken(serviceToken) && TokenStore.isAcceptableToken(popToken)) {
            tokenStore.saveCaptures(serviceToken, popToken)
            Log.i(LOG_TAG, "TWO_CAPTURES_IMPORTED nonce=$proofNonce")
            showImported()
            return
        }

        if (TokenStore.isAcceptableToken(pushedToken)) {
            tokenStore.saveSession(pushedToken)
            Log.i(LOG_TAG, "SERVICE_CAPTURE_IMPORTED nonce=$proofNonce")
            showImported()
            return
        }

        if (hasAnyImportExtra()) {
            Log.w(LOG_TAG, "IMPORT_REJECTED_INVALID_CAPTURE nonce=$proofNonce")
        }
        showWelcomeImport()
    }

    private fun showWelcomeImport() {
        mibuImageHotspotScreen(
            R.drawable.android_welcome_import,
            listOf(
                MibuHotspot(0.10f, 0.710f, 0.80f, 0.075f, "Import Session Token From PC") {
                    showManualPasteDialog()
                },
                MibuHotspot(0.10f, 0.805f, 0.80f, 0.065f, "Open Logs") {
                    startActivity(Intent(this, LogsActivity::class.java))
                },
                MibuHotspot(0.10f, 0.880f, 0.80f, 0.065f, "Instructions") {
                    startActivity(Intent(this, InstructionsActivity::class.java))
                },
            ),
        )
    }

    private fun showImported() {
        mibuImageHotspotScreen(
            R.drawable.android_account_session,
            listOf(
                MibuHotspot(0.08f, 0.885f, 0.84f, 0.070f, "Open Dashboard") {
                    startActivity(Intent(this, MainActivity::class.java))
                    finish()
                },
            ),
        )
    }

    private fun showManualPasteDialog() {
        val serviceInput = tokenField("Firefox new_bbs_serviceToken")
        val popInput = tokenField("Chrome popRunToken")
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(8), dp(8), dp(8), dp(0))
            addView(serviceInput)
            addView(popInput)
        }
        AlertDialog.Builder(this)
            .setTitle("Paste / Push Token")
            .setMessage("Paste both approved captures. PC push over ADB is preferred when available.")
            .setView(box)
            .setPositiveButton("Save") { _, _ ->
                val service = serviceInput.text.toString().trim()
                val pop = popInput.text.toString().trim()
                if (TokenStore.isAcceptableToken(service) && TokenStore.isAcceptableToken(pop)) {
                    tokenStore.saveCaptures(service, pop)
                    Log.i(LOG_TAG, "TWO_CAPTURES_IMPORTED_MANUALLY nonce=$proofNonce")
                    startActivity(Intent(this, MainActivity::class.java))
                    finish()
                } else {
                    Log.w(LOG_TAG, "IMPORT_REJECTED_INVALID_MANUAL_CAPTURE nonce=$proofNonce")
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun tokenField(hintText: String): EditText =
        EditText(this).apply {
            hint = hintText
            setTextColor(Color.BLACK)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            filters = arrayOf(InputFilter.LengthFilter(TokenStore.MAX_TOKEN_LENGTH))
            minLines = 2
        }

    private fun hasAnyImportExtra(): Boolean = listOf(
        "mibu_service_token_b64",
        "mibu_pop_token_b64",
        "mibu_session_token_b64",
        "mibu_service_token",
        "mibu_pop_token",
        "mibu_session_token",
    ).any { intent?.hasExtra(it) == true }

    private fun decodeExtra(name: String): String {
        val encoded = intent?.getStringExtra(name)?.trim().orEmpty()
        if (encoded.isBlank()) return ""
        if (encoded.length > MAX_ENCODED_EXTRA_LENGTH) {
            Log.w(LOG_TAG, "IMPORT_REJECTED_OVERSIZE_BASE64 name=$name length=${encoded.length} nonce=$proofNonce")
            return ""
        }
        return runCatching {
            String(Base64.decode(encoded, Base64.URL_SAFE or Base64.NO_WRAP), Charsets.UTF_8).trim()
        }.onFailure {
            Log.w(LOG_TAG, "IMPORT_REJECTED_INVALID_BASE64 name=$name nonce=$proofNonce")
        }.getOrDefault("")
    }

    companion object {
        private const val MAX_ENCODED_EXTRA_LENGTH = 12_000
        private const val LOG_TAG = "MIBU_IMPORT"
    }
}
