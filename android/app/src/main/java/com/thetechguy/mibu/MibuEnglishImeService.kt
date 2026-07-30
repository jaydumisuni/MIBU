package com.thetechguy.mibu

import android.content.res.ColorStateList
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.inputmethodservice.InputMethodService
import android.provider.Settings
import android.view.Gravity
import android.view.HapticFeedbackConstants
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

class MibuEnglishImeService : InputMethodService() {
    private var shifted = false
    private var symbols = false
    private lateinit var keyboard: LinearLayout

    override fun onEvaluateFullscreenMode(): Boolean = false

    override fun onCreateInputView(): View {
        keyboard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(5), dp(3), dp(5), dp(7))
            setBackgroundColor(BACKGROUND)
        }
        renderKeys()
        return keyboard
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        super.onStartInput(attribute, restarting)
        shifted = false
        symbols = false
        if (::keyboard.isInitialized) renderKeys()
    }

    private fun renderKeys() {
        keyboard.removeAllViews()
        addToolbar()
        val rows = if (symbols) {
            listOf(
                listOf("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"),
                listOf("@", "#", "$", "%", "&", "-", "+", "(", ")", "/"),
                listOf("ABC", "*", "\"", "'", ":", ";", "!", "?", "_", "DEL")
            )
        } else {
            listOf(
                listOf("q", "w", "e", "r", "t", "y", "u", "i", "o", "p"),
                listOf("a", "s", "d", "f", "g", "h", "j", "k", "l"),
                listOf("SHIFT", "z", "x", "c", "v", "b", "n", "m", "DEL")
            )
        }
        rows.forEachIndexed { index, keys -> addRow(keys, index == 1 && !symbols) }
        addBottomRow()
    }

    private fun addToolbar() {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(9), 0, dp(4), 0)
        }
        val language = TextView(this).apply {
            text = "MIBU  |  English (US)"
            setTextColor(SECONDARY_TEXT)
            textSize = 12f
            typeface = Typeface.create("sans", Typeface.BOLD)
            gravity = Gravity.CENTER_VERTICAL
        }
        val settings = toolbarButton("\u2699") {
            val intent = Intent(Settings.ACTION_INPUT_METHOD_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            runCatching { startActivity(intent) }
        }
        val hide = toolbarButton("\u2304") { requestHideSelf(0) }
        row.addView(language, LinearLayout.LayoutParams(0, dp(36), 1f))
        row.addView(settings, LinearLayout.LayoutParams(dp(42), dp(34)))
        row.addView(hide, LinearLayout.LayoutParams(dp(42), dp(34)))
        keyboard.addView(
            row,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )
    }

    private fun toolbarButton(label: String, action: () -> Unit): TextView =
        TextView(this).apply {
            text = label
            gravity = Gravity.CENTER
            setTextColor(SECONDARY_TEXT)
            textSize = 20f
            typeface = Typeface.DEFAULT_BOLD
            isClickable = true
            isFocusable = false
            background = rippleBackground(TOOLBAR_KEY, false)
            setOnClickListener {
                performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                action()
            }
        }

    private fun addRow(keys: List<String>, inset: Boolean) {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            if (inset) setPadding(dp(14), 0, dp(14), 0)
        }
        keys.forEach { key ->
            val weight = when (key) {
                "SHIFT", "DEL", "ABC" -> 1.35f
                else -> 1f
            }
            row.addView(
                keyView(key),
                LinearLayout.LayoutParams(0, dp(45), weight).apply {
                    setMargins(dp(2), dp(2), dp(2), dp(2))
                }
            )
        }
        keyboard.addView(
            row,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )
    }

    private fun addBottomRow() {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        val keys = listOf(
            KeySpec(if (symbols) "ABC" else "?123", 1.35f),
            KeySpec(",", 0.85f),
            KeySpec("SPACE", 3.8f),
            KeySpec(".", 0.85f),
            KeySpec("Enter", 1.35f)
        )
        keys.forEach { spec ->
            row.addView(
                keyView(spec.label),
                LinearLayout.LayoutParams(0, dp(47), spec.weight).apply {
                    setMargins(dp(2), dp(2), dp(2), dp(2))
                }
            )
        }
        keyboard.addView(
            row,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )
    }

    private fun keyView(label: String): View {
        val container = FrameLayout(this).apply {
            background = rippleBackground(
                if (isAccentKey(label)) ACCENT_KEY else KEY,
                isAccentKey(label)
            )
            isClickable = true
            isFocusable = false
            setOnClickListener {
                performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                handleKey(label)
            }
        }
        val main = TextView(this).apply {
            text = displayLabel(label)
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            textSize = when (label) {
                "SHIFT", "DEL" -> 24f
                "SPACE" -> 12f
                "?123", "ABC" -> 13f
                "Enter" -> if (editorActionLabel().length > 2) 13f else 23f
                else -> 20f
            }
            typeface = Typeface.create("sans", Typeface.NORMAL)
        }
        container.addView(
            main,
            FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
        )
        numberHint(label)?.let { hint ->
            val hintView = TextView(this).apply {
                text = hint
                gravity = Gravity.TOP or Gravity.END
                setPadding(0, dp(2), dp(5), 0)
                setTextColor(HINT_TEXT)
                textSize = 8f
            }
            container.addView(
                hintView,
                FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT
                )
            )
            container.setOnLongClickListener {
                container.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                commit(hint)
                true
            }
        }
        return container
    }

    private fun displayLabel(label: String): String = when (label) {
        "SHIFT" -> if (shifted) "\u21e7" else "\u21e7"
        "DEL" -> "\u232b"
        "SPACE" -> "English (US)"
        "Enter" -> editorActionLabel()
        else -> {
            if (label.length != 1 || !label[0].isLetter()) {
                label
            } else if (shifted) {
                label.uppercase(Locale.US)
            } else {
                label
            }
        }
    }

    private fun editorActionLabel(): String {
        return when (currentInputEditorInfo?.imeOptions?.and(EditorInfo.IME_MASK_ACTION)) {
            EditorInfo.IME_ACTION_GO -> "Go"
            EditorInfo.IME_ACTION_NEXT -> "Next"
            EditorInfo.IME_ACTION_SEARCH -> "Search"
            EditorInfo.IME_ACTION_SEND -> "Send"
            EditorInfo.IME_ACTION_DONE -> "Done"
            else -> "\u21b5"
        }
    }

    private fun numberHint(label: String): String? {
        if (symbols || label.length != 1) return null
        val index = "qwertyuiop".indexOf(label)
        if (index < 0) return null
        return "1234567890"[index].toString()
    }

    private fun handleKey(label: String) {
        when (label) {
            "SHIFT" -> {
                shifted = !shifted
                renderKeys()
            }
            "DEL" -> deleteOne()
            "?123", "ABC" -> {
                symbols = !symbols
                shifted = false
                renderKeys()
            }
            "SPACE" -> commit(" ")
            "Enter" -> {
                if (!sendDefaultEditorAction(true)) {
                    sendDownUpKeyEvents(KeyEvent.KEYCODE_ENTER)
                }
            }
            else -> {
                val value = if (shifted && label.length == 1 && label[0].isLetter()) {
                    label.uppercase(Locale.US)
                } else {
                    label
                }
                commit(value)
                if (shifted) {
                    shifted = false
                    renderKeys()
                }
            }
        }
    }

    private fun deleteOne() {
        val connection = currentInputConnection ?: return
        val selected = connection.getSelectedText(0)
        if (!selected.isNullOrEmpty()) {
            connection.commitText("", 1)
        } else if (!connection.deleteSurroundingText(1, 0)) {
            sendDownUpKeyEvents(KeyEvent.KEYCODE_DEL)
        }
    }

    private fun commit(value: String) {
        currentInputConnection?.commitText(value, 1)
    }

    private fun rippleBackground(color: Int, accent: Boolean): RippleDrawable {
        val shape = GradientDrawable().apply {
            cornerRadius = dp(6).toFloat()
            setColor(color)
            if (accent) setStroke(dp(1), CYAN)
        }
        return RippleDrawable(
            ColorStateList.valueOf(if (accent) MAGENTA else RIPPLE),
            shape,
            null
        )
    }

    private fun isAccentKey(label: String): Boolean =
        label == "SHIFT" || label == "DEL" || label == "Enter"

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()

    private data class KeySpec(val label: String, val weight: Float)

    companion object {
        private const val BACKGROUND = 0xFF121318.toInt()
        private const val KEY = 0xFF252831.toInt()
        private const val ACCENT_KEY = 0xFF202D45.toInt()
        private const val TOOLBAR_KEY = 0xFF1B1D24.toInt()
        private const val SECONDARY_TEXT = 0xFFB8C2D8.toInt()
        private const val HINT_TEXT = 0xFF8D94A6.toInt()
        private const val CYAN = 0xFF25C8FF.toInt()
        private const val MAGENTA = 0xFFB33CFF.toInt()
        private const val RIPPLE = 0xFF5A6070.toInt()
    }
}
