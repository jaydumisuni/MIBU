package com.thetechguy.mibu

import android.app.Activity
import android.os.Bundle
import android.text.InputType
import android.widget.EditText

class TokenImportActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val pushedToken = intent?.getStringExtra("mibu_session_token")?.trim().orEmpty()
        if (pushedToken.length >= 8) {
            tokenStore.saveSession(pushedToken)
            mibuPage("MIBU", "Session Imported / THETECHGUY TOOL") {
                addView(mibuCard("Session imported", "The session/token was securely received from MIBU PC Helper and saved on this phone."))
                addView(mibuButton("Open Dashboard", true) {
                    startActivity(android.content.Intent(this@TokenImportActivity, MainActivity::class.java))
                    finish()
                })
                addView(mibuButton("Back") { finish() })
                addView(footer())
            }
            return
        }

        lateinit var input: EditText
        mibuPage("MIBU", "Import Session / THETECHGUY TOOL") {
            addView(mibuCard("Sensitive token", "Only paste a token/session value you obtained yourself through the visible browser login flow. MIBU does not need your Xiaomi password."))
            input = EditText(this@TokenImportActivity).apply {
                hint = "Paste token/session here"
                setTextColor(android.graphics.Color.WHITE)
                setHintTextColor(android.graphics.Color.rgb(145, 160, 190))
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD or InputType.TYPE_TEXT_FLAG_MULTI_LINE
                minLines = 4
                setPadding(dp(16), dp(14), dp(16), dp(14))
                background = rounded(android.graphics.Color.rgb(13, 20, 35), dp(16), android.graphics.Color.rgb(30, 40, 65))
            }
            addView(input)
            addView(mibuButton("Save session", true) {
                val value = input.text.toString().trim()
                if (value.length < 8) {
                    input.error = "Token/session looks too short"
                } else {
                    tokenStore.saveSession(value)
                    finish()
                }
            })
            addView(mibuButton("Clear saved session") {
                tokenStore.clear()
                input.setText("")
            })
            addView(mibuButton("Back") { finish() })
            addView(footer())
        }
    }
}
