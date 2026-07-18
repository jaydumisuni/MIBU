package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.text.InputFilter
import android.text.InputType
import android.util.Base64
import android.util.Log
import android.widget.EditText
import android.widget.ImageView

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
            showImported("Two captures imported", "Firefox service token and Chrome pop token were received. MIBU populated slots 1/3 and 2/4 automatically.")
            return
        }

        if (TokenStore.isAcceptableToken(pushedToken)) {
            tokenStore.saveSession(pushedToken)
            Log.i(LOG_TAG, "SERVICE_CAPTURE_IMPORTED nonce=$proofNonce")
            showImported("Service token imported", "A single token/session was received and saved as the Firefox/service capture. Chrome pop token is still missing, so waiting cannot be armed yet.")
            return
        }

        if (hasAnyImportExtra()) {
            Log.w(LOG_TAG, "IMPORT_REJECTED_INVALID_CAPTURE nonce=$proofNonce")
        }
        showManualImport()
    }

    private fun showImported(title: String, message: String) {
        mibuPage("MIBU", "Session Imported / THETECHGUY TOOL") {
            addView(ImageView(this@TokenImportActivity).apply {
                setImageResource(R.drawable.mibu_logo)
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.FIT_CENTER
            }, android.widget.LinearLayout.LayoutParams(android.widget.LinearLayout.LayoutParams.MATCH_PARENT, dp(150)))
            addView(mibuCard(title, message))
            addView(mibuCard("Current slots", tokenStore.getSlotPreview()))
            addView(mibuButton("Open Dashboard", true) {
                startActivity(Intent(this@TokenImportActivity, MainActivity::class.java))
                finish()
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

    private fun showManualImport() {
        lateinit var serviceInput: EditText
        lateinit var popInput: EditText
        mibuPage("MIBU", "Import Session / THETECHGUY TOOL") {
            addView(ImageView(this@TokenImportActivity).apply {
                setImageResource(R.drawable.mibu_logo)
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.FIT_CENTER
            }, android.widget.LinearLayout.LayoutParams(android.widget.LinearLayout.LayoutParams.MATCH_PARENT, dp(150)))
            addView(mibuCard("Import session from PC", "Paste the Firefox new_bbs_serviceToken once and the Chrome popRunToken once. MIBU fills slots 1/3 and 2/4 automatically. The PC helper can also push these directly over ADB."))
            serviceInput = tokenField("Firefox service token - slots 1 and 3")
            popInput = tokenField("Chrome pop token - slots 2 and 4")
            addView(serviceInput)
            addView(popInput)
            addView(mibuButton("Save two captures", true) {
                val service = serviceInput.text.toString().trim()
                val pop = popInput.text.toString().trim()
                when {
                    !TokenStore.isAcceptableToken(service) -> serviceInput.error = invalidTokenMessage("Firefox/service")
                    !TokenStore.isAcceptableToken(pop) -> popInput.error = invalidTokenMessage("Chrome/pop")
                    else -> {
                        tokenStore.saveCaptures(service, pop)
                        Log.i(LOG_TAG, "TWO_CAPTURES_IMPORTED_MANUALLY nonce=$proofNonce")
                        startActivity(Intent(this@TokenImportActivity, MainActivity::class.java))
                        finish()
                    }
                }
            })
            addView(mibuButton("Save service token only") {
                val service = serviceInput.text.toString().trim()
                if (!TokenStore.isAcceptableToken(service)) {
                    serviceInput.error = invalidTokenMessage("Firefox/service")
                } else {
                    tokenStore.saveServiceToken(service)
                    Log.i(LOG_TAG, "SERVICE_CAPTURE_IMPORTED_MANUALLY nonce=$proofNonce")
                    startActivity(Intent(this@TokenImportActivity, MainActivity::class.java))
                    finish()
                }
            })
            addView(mibuButton("Clear saved tokens") {
                tokenStore.clear()
                serviceInput.text?.clear()
                popInput.text?.clear()
                Log.i(LOG_TAG, "CAPTURES_CLEARED nonce=$proofNonce")
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

    private fun invalidTokenMessage(label: String): String =
        "$label token must be ${TokenStore.MIN_TOKEN_LENGTH}-${TokenStore.MAX_TOKEN_LENGTH} characters and contain no control characters"

    private fun tokenField(hintText: String): EditText =
        EditText(this).apply {
            hint = hintText
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(145, 160, 190))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            filters = arrayOf(InputFilter.LengthFilter(TokenStore.MAX_TOKEN_LENGTH))
            minLines = 3
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
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
