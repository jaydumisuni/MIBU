package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.util.Base64
import android.widget.EditText

class TokenImportActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val serviceToken = decodeExtra("mibu_service_token_b64")
            .ifBlank { intent?.getStringExtra("mibu_service_token")?.trim().orEmpty() }
        val popToken = decodeExtra("mibu_pop_token_b64")
            .ifBlank { intent?.getStringExtra("mibu_pop_token")?.trim().orEmpty() }
        val pushedToken = decodeExtra("mibu_session_token_b64")
            .ifBlank { intent?.getStringExtra("mibu_session_token")?.trim().orEmpty() }

        if (serviceToken.length >= MIN_TOKEN_LENGTH && popToken.length >= MIN_TOKEN_LENGTH) {
            tokenStore.saveCaptures(serviceToken, popToken)
            showImported("Two captures imported", "Firefox service token and Chrome pop token were received. MIBU populated slots 1/3 and 2/4 automatically.")
            return
        }

        if (pushedToken.length >= MIN_TOKEN_LENGTH) {
            tokenStore.saveSession(pushedToken)
            showImported("Service token imported", "A single token/session was received and saved as the Firefox/service capture. Chrome pop token is still missing, so waiting cannot be armed yet.")
            return
        }

        showManualImport()
    }

    private fun decodeExtra(name: String): String {
        val encoded = intent?.getStringExtra(name)?.trim().orEmpty()
        if (encoded.isBlank()) return ""
        return runCatching {
            String(Base64.decode(encoded, Base64.URL_SAFE or Base64.NO_WRAP), Charsets.UTF_8).trim()
        }.getOrDefault("")
    }

    private fun showImported(title: String, message: String) {
        mibuPage("MIBU", "Session Imported / THETECHGUY TOOL") {
            addView(mibuCard(title, message))
            addView(mibuCard("Current slots", tokenStore.getSlotPreview()))
            addView(mibuButton("Open Dashboard", true) {
                startActivity(android.content.Intent(this@TokenImportActivity, MainActivity::class.java))
                finish()
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

    private fun showManualImport() {
        lateinit var serviceInput: EditText
        lateinit var popInput: EditText
        mibuPage("MIBU", "Import Tokens / THETECHGUY TOOL") {
            addView(mibuCard("Two captures, four slots", "Paste the Firefox new_bbs_serviceToken once and the Chrome popRunToken once. MIBU fills slots 1/3 and 2/4 automatically. Both captures expire locally after 30 minutes. MIBU does not need your Xiaomi password."))
            serviceInput = tokenField("Firefox service token → slots 1 and 3")
            popInput = tokenField("Chrome pop token → slots 2 and 4")
            addView(serviceInput)
            addView(popInput)
            addView(mibuButton("Save two captures", true) {
                val service = serviceInput.text.toString().trim()
                val pop = popInput.text.toString().trim()
                when {
                    service.length < MIN_TOKEN_LENGTH -> serviceInput.error = "Firefox/service token looks too short"
                    pop.length < MIN_TOKEN_LENGTH -> popInput.error = "Chrome/pop token looks too short"
                    else -> {
                        tokenStore.saveCaptures(service, pop)
                        finish()
                    }
                }
            })
            addView(mibuButton("Save service token only") {
                val service = serviceInput.text.toString().trim()
                if (service.length < MIN_TOKEN_LENGTH) {
                    serviceInput.error = "Firefox/service token looks too short"
                } else {
                    tokenStore.saveServiceToken(service)
                    finish()
                }
            })
            addView(mibuButton("Clear saved tokens") {
                tokenStore.clear()
                serviceInput.setText("")
                popInput.setText("")
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }

    private fun tokenField(hintText: String): EditText {
        return EditText(this).apply {
            hint = hintText
            setTextColor(android.graphics.Color.WHITE)
            setHintTextColor(android.graphics.Color.rgb(145, 160, 190))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            minLines = 3
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = rounded(android.graphics.Color.rgb(13, 20, 35), dp(16), android.graphics.Color.rgb(30, 40, 65))
        }
    }

    companion object {
        private const val MIN_TOKEN_LENGTH = 8
    }
}
