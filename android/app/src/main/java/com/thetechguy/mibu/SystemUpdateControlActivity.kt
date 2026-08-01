package com.thetechguy.mibu

import android.app.Activity
import android.app.Dialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.ColorDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.Gravity
import android.view.ViewGroup
import android.view.Window
import android.widget.LinearLayout
import android.widget.TextView

class SystemUpdateControlActivity : Activity() {
    private val store by lazy { SystemUpdateControlStore(this) }
    private val logStore by lazy { LogStore(this) }
    private val handler = Handler(Looper.getMainLooper())
    private var dialog: Dialog? = null
    private var statusText: TextView? = null
    private val refresh = object : Runnable {
        override fun run() {
            renderState()
            handler.postDelayed(this, REFRESH_MS)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        mibuScreen {
            addView(mibuBrandHeader(onBack = { finish() }))
            addView(mibuHeading("System Update Control", "Reversibly disable or enable Xiaomi OTA updates through MIBU PC Helper."))
            addView(mibuAction(R.drawable.mibu_icon_shield, "Manage System Updates", "Open verified enable and disable controls", MibuColors.orange, true) {
                showControlPopup()
            }.root)
            addView(mibuCard("How it works", "The phone requests the change. MIBU PC Helper applies the shell-only command over USB, then this screen verifies the actual updater package and automatic-update setting."))
            addView(mibuCard("Safety", "Enable restores Xiaomi's updater package. Disable can prevent security and stability updates until you enable it again."))
            addView(footer())
        }
        showControlPopup()
    }

    override fun onResume() {
        super.onResume()
        handler.removeCallbacks(refresh)
        handler.post(refresh)
    }

    override fun onPause() {
        handler.removeCallbacks(refresh)
        super.onPause()
    }

    private fun showControlPopup() {
        if (dialog?.isShowing == true) return
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(16))
            background = rounded(MibuColors.panel, dp(16), MibuColors.orange, 2)
            addView(TextView(this@SystemUpdateControlActivity).apply {
                text = "System Update Control"
                textSize = 21f
                setTextColor(Color.WHITE)
                setTypeface(typeface, Typeface.BOLD)
            })
            addView(TextView(this@SystemUpdateControlActivity).apply {
                text = "Choose a reversible updater state. Keep USB connected and MIBU PC Helper open."
                textSize = 12f
                setTextColor(MibuColors.muted)
                setPadding(0, dp(5), 0, dp(12))
            })
            statusText = TextView(this@SystemUpdateControlActivity).apply {
                textSize = 13f
                setTextColor(Color.WHITE)
                setPadding(dp(12), dp(11), dp(12), dp(11))
                background = rounded(MibuColors.card, dp(11), MibuColors.line)
            }
            addView(statusText, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                setMargins(0, 0, 0, dp(12))
            })
            val actions = LinearLayout(this@SystemUpdateControlActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER
            }
            actions.addView(mibuButton("Disable", primary = true) { request(SystemUpdateAction.DISABLE) }, LinearLayout.LayoutParams(0, dp(54), 1f).apply {
                setMargins(0, 0, dp(4), 0)
            })
            actions.addView(mibuButton("Enable") { request(SystemUpdateAction.ENABLE) }, LinearLayout.LayoutParams(0, dp(54), 1f).apply {
                setMargins(dp(4), 0, 0, 0)
            })
            addView(actions)
            addView(mibuButton("Close") { dialog?.dismiss() }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50)).apply {
                setMargins(0, dp(8), 0, 0)
            })
        }
        dialog = Dialog(this).apply {
            requestWindowFeature(Window.FEATURE_NO_TITLE)
            setContentView(content)
            setCanceledOnTouchOutside(false)
            setOnDismissListener { dialog = null; statusText = null }
            window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
            show()
            window?.setLayout((resources.displayMetrics.widthPixels * 0.92f).toInt(), ViewGroup.LayoutParams.WRAP_CONTENT)
        }
        renderState()
    }

    private fun request(action: SystemUpdateAction) {
        val id = store.request(action)
        Log.i(SystemUpdateControlReceiver.LOG_TAG, "UPDATE_REQUEST id=$id action=${action.name}")
        logStore.add("System update request ${action.name.lowercase()} sent to PC Helper")
        renderState()
    }

    private fun renderState() {
        val state = store.readState()
        val actual = when {
            !state.updaterInstalled -> "Updater package not installed"
            state.fullyDisabled -> "DISABLED - package and automatic OTA verified off"
            state.fullyEnabled -> "ENABLED - Xiaomi updater is available"
            else -> "PARTIAL - updater=${if (state.updaterEnabled) "enabled" else "disabled"}, automatic OTA=${if (state.automaticUpdatesDisabled) "off" else "on"}"
        }
        val request = when {
            state.resultState == "PENDING" -> "\nRequest ${state.requestedAction}: waiting for PC Helper"
            state.resultMessage.isNotBlank() -> "\nLast PC result: ${state.resultMessage}"
            else -> ""
        }
        statusText?.text = "$actual$request"
        statusText?.setTextColor(
            when {
                state.fullyDisabled -> MibuColors.green
                state.resultState == "FAILED" -> MibuColors.red
                else -> Color.WHITE
            }
        )
    }

    companion object {
        private const val REFRESH_MS = 750L
    }
}
