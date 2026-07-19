package com.thetechguy.mibu

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputFilter
import android.text.InputType
import android.util.Base64
import android.util.Log
import android.view.Gravity
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class TokenImportActivity : Activity() {
    private val tokenStore by lazy { TokenStore(this) }
    private val proofNonce by lazy { ProofNonce.from(intent) }
    private lateinit var serviceInput: EditText
    private lateinit var popInput: EditText
    private lateinit var statusText: TextView

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
            showImported("Two captures imported")
            return
        }

        if (TokenStore.isAcceptableToken(pushedToken)) {
            tokenStore.saveSession(pushedToken)
            Log.i(LOG_TAG, "SERVICE_CAPTURE_IMPORTED nonce=$proofNonce")
            showImported("Service token imported")
            return
        }

        if (hasAnyImportExtra()) {
            Log.w(LOG_TAG, "IMPORT_REJECTED_INVALID_CAPTURE nonce=$proofNonce")
        }
        showManualImport()
    }

    private fun showImported(message: String) {
        buildShell("Session Imported") { root ->
            root.addView(statusCard(message, tokenStore.getSlotPreview(), green()))
            root.addView(neonButton("Open Dashboard", true) {
                startActivity(Intent(this, MainActivity::class.java))
                finish()
            })
        }
    }

    private fun showManualImport() {
        buildShell("Import Session From PC") { root ->
            root.addView(statusCard("Waiting for approved token/session", "Paste both captures here or let the PC helper push them over ADB.", cyan()))
            serviceInput = tokenField("Firefox new_bbs_serviceToken")
            popInput = tokenField("Chrome popRunToken")
            root.addView(serviceInput)
            root.addView(popInput)
            statusText = TextView(this).apply {
                text = "Status appears here while this step runs."
                textSize = 13f
                setTextColor(Color.rgb(255, 190, 100))
                setPadding(dp(16), dp(12), dp(16), dp(12))
                background = rounded(Color.rgb(8, 13, 28), dp(14), Color.rgb(55, 78, 122))
            }
            root.addView(statusText, fullWidth(dp(10)))
            root.addView(neonButton("Save Two Captures", true) { saveTwoCaptures() })
            root.addView(neonButton("Clear Saved Tokens") {
                tokenStore.clear()
                serviceInput.text?.clear()
                popInput.text?.clear()
                statusText.text = "Saved tokens cleared."
                Log.i(LOG_TAG, "CAPTURES_CLEARED nonce=$proofNonce")
            })
            root.addView(neonButton("Back") { finish() })
        }
    }

    private fun buildShell(title: String, build: (LinearLayout) -> Unit) {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(18))
            setBackgroundColor(Color.rgb(4, 6, 17))
        }
        setContentView(ScrollView(this).apply { addView(root) })
        root.addView(ImageView(this).apply {
            setImageResource(R.drawable.mibu_welcome_hero)
            scaleType = ImageView.ScaleType.CENTER_CROP
            background = rounded(Color.rgb(8, 12, 30), dp(22), Color.rgb(40, 62, 102))
        }, fullWidth(dp(14)).apply { height = dp(340) })
        root.addView(TextView(this).apply {
            text = title
            textSize = 28f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }, fullWidth(dp(6)))
        root.addView(TextView(this).apply {
            text = "by the THETECHGUY TOOL team"
            textSize = 13f
            setTextColor(Color.rgb(166, 177, 205))
            gravity = Gravity.CENTER
        }, fullWidth(dp(12)))
        build(root)
    }

    private fun saveTwoCaptures() {
        val service = serviceInput.text.toString().trim()
        val pop = popInput.text.toString().trim()
        when {
            !TokenStore.isAcceptableToken(service) -> statusText.text = "Firefox/service token is missing or invalid."
            !TokenStore.isAcceptableToken(pop) -> statusText.text = "Chrome/pop token is missing or invalid."
            else -> {
                tokenStore.saveCaptures(service, pop)
                Log.i(LOG_TAG, "TWO_CAPTURES_IMPORTED_MANUALLY nonce=$proofNonce")
                startActivity(Intent(this, MainActivity::class.java))
                finish()
            }
        }
    }

    private fun statusCard(title: String, body: String, stroke: Int): TextView =
        TextView(this).apply {
            text = "$title\n$body"
            textSize = 15f
            setTextColor(Color.WHITE)
            setPadding(dp(18), dp(14), dp(18), dp(14))
            background = rounded(Color.rgb(10, 15, 32), dp(18), stroke)
            layoutParams = fullWidth(dp(12))
        }

    private fun tokenField(hintText: String): EditText =
        EditText(this).apply {
            hint = hintText
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(145, 160, 190))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            filters = arrayOf(InputFilter.LengthFilter(TokenStore.MAX_TOKEN_LENGTH))
            minLines = 2
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = rounded(Color.rgb(10, 15, 32), dp(16), Color.rgb(55, 78, 122))
            layoutParams = fullWidth(dp(10))
        }

    private fun neonButton(textValue: String, primary: Boolean = false, onClick: () -> Unit): Button =
        Button(this).apply {
            text = textValue
            textSize = if (primary) 16f else 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            background = rounded(if (primary) Color.rgb(23, 20, 48) else Color.rgb(10, 15, 32), dp(18), if (primary) orange() else Color.rgb(55, 78, 122))
            setOnClickListener { onClick() }
            layoutParams = fullWidth(dp(10)).apply { height = if (primary) dp(66) else dp(56) }
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

    private fun fullWidth(bottom: Int): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            setMargins(0, 0, 0, bottom)
        }

    private fun rounded(color: Int, radius: Int, stroke: Int): GradientDrawable =
        GradientDrawable().apply { setColor(color); cornerRadius = radius.toFloat(); setStroke(dp(1), stroke) }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
    private fun green() = Color.rgb(61, 255, 135)
    private fun cyan() = Color.rgb(36, 178, 255)
    private fun orange() = Color.rgb(255, 122, 43)

    companion object {
        private const val MAX_ENCODED_EXTRA_LENGTH = 12_000
        private const val LOG_TAG = "MIBU_IMPORT"
    }
}
