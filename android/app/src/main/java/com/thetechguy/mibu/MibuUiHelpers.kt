package com.thetechguy.mibu

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.LayerDrawable
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import android.widget.TextView

data class MibuLiveRow(
    val root: LinearLayout,
    val title: TextView,
    val value: TextView,
    val badge: TextView,
)

data class MibuCountdown(
    val root: LinearLayout,
    val title: TextView,
    val value: TextView,
    val units: TextView,
)

fun Activity.mibuScreen(padding: Int = 14, build: LinearLayout.() -> Unit): LinearLayout {
    window.statusBarColor = MibuColors.background
    window.navigationBarColor = MibuColors.background
    val root = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(padding), dp(10), dp(padding), dp(18))
        setBackgroundColor(MibuColors.background)
        build()
    }
    root.setOnApplyWindowInsetsListener { view, insets ->
        val top: Int
        val bottom: Int
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
            val bars = insets.getInsets(WindowInsets.Type.systemBars())
            top = bars.top
            bottom = bars.bottom
        } else {
            @Suppress("DEPRECATION")
            top = insets.systemWindowInsetTop
            @Suppress("DEPRECATION")
            bottom = insets.systemWindowInsetBottom
        }
        view.setPadding(dp(padding), top + dp(8), dp(padding), bottom + dp(12))
        insets
    }
    val scroll = ScrollView(this).apply {
        isFillViewport = true
        overScrollMode = View.OVER_SCROLL_NEVER
        setBackgroundColor(MibuColors.background)
        addView(root)
    }
    setContentView(scroll)
    return root
}

fun Activity.mibuBrandHeader(
    onBack: (() -> Unit)? = null,
    onSettings: (() -> Unit)? = null,
    large: Boolean = false,
): FrameLayout {
    val compact = !large && onBack != null
    val height = when {
        large -> 294
        compact -> 118
        else -> 172
    }
    return FrameLayout(this).apply {
        background = rounded(MibuColors.panel, dp(18), MibuColors.line)
        clipToOutline = true
        layoutParams = fullWidth(dp(10)).apply { this.height = dp(height) }

        addView(ImageView(this@mibuBrandHeader).apply {
            setImageResource(R.drawable.mibu_hood_live)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            contentDescription = "MIBU assistant"
        }, FrameLayout.LayoutParams(
            dp(if (large) 300 else if (compact) 156 else 220),
            dp(if (large) 245 else if (compact) 116 else 170),
            Gravity.END or Gravity.BOTTOM,
        ))

        addView(ImageView(this@mibuBrandHeader).apply {
            setImageResource(R.drawable.mibu_logo_live)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            contentDescription = "MIBU logo"
        }, FrameLayout.LayoutParams(
            dp(if (large) 118 else if (compact) 58 else 82),
            dp(if (large) 118 else if (compact) 58 else 82),
        ).apply {
            leftMargin = dp(if (onBack == null) 8 else if (compact) 36 else 44)
            topMargin = dp(if (large) 12 else 8)
        })

        addView(ImageView(this@mibuBrandHeader).apply {
            setImageResource(R.drawable.mibu_wordmark_live)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            contentDescription = "MIBU"
        }, FrameLayout.LayoutParams(
            dp(if (large) 190 else if (compact) 126 else 142),
            dp(if (large) 62 else if (compact) 42 else 48),
        ).apply {
            leftMargin = dp(if (large) 128 else if (onBack == null) 86 else if (compact) 92 else 120)
            topMargin = dp(if (large) 26 else if (compact) 12 else 18)
        })

        addView(TextView(this@mibuBrandHeader).apply {
            text = "THETECHGUY TOOL"
            textSize = if (large) 12f else 10f
            setTextColor(MibuColors.muted)
        }, FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT).apply {
            leftMargin = dp(if (large) 132 else if (onBack == null) 88 else if (compact) 94 else 122)
            topMargin = dp(if (large) 82 else if (compact) 49 else 62)
        })

        if (large) {
            addView(TextView(this@mibuBrandHeader).apply {
                text = "Mi Bootloader Unlock Helper"
                textSize = 23f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
            }, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, dp(42), Gravity.BOTTOM).apply {
                bottomMargin = dp(14)
            })
        }

        onBack?.let { callback ->
            addView(mibuIconButton("\u2039", "Back", callback), FrameLayout.LayoutParams(dp(if (compact) 32 else 38), dp(if (compact) 32 else 38)).apply {
                leftMargin = dp(4)
                topMargin = dp(if (compact) 7 else 10)
            })
        }
        onSettings?.let { callback ->
            addView(mibuIconButton("\u2699", "Settings", callback), FrameLayout.LayoutParams(dp(38), dp(38), Gravity.END or Gravity.TOP).apply {
                rightMargin = dp(8)
                topMargin = dp(8)
            })
        }
    }
}

fun Activity.mibuHeading(title: String, subtitle: String = ""): LinearLayout =
    LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(4), dp(2), dp(4), dp(8))
        addView(TextView(this@mibuHeading).apply {
            text = title
            textSize = 25f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            includeFontPadding = false
        })
        if (subtitle.isNotBlank()) {
            addView(TextView(this@mibuHeading).apply {
                text = subtitle
                textSize = 13f
                setTextColor(MibuColors.muted)
                setLineSpacing(0f, 1.08f)
            })
        }
    }

fun Activity.mibuLiveRow(
    iconRes: Int,
    titleText: String,
    valueText: String,
    accent: Int,
    badgeText: String = "",
    onClick: (() -> Unit)? = null,
): MibuLiveRow {
    val title = TextView(this).apply {
        text = titleText
        textSize = 14f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Color.WHITE)
        includeFontPadding = false
    }
    val value = TextView(this).apply {
        text = valueText
        textSize = 12f
        setTextColor(accent)
        includeFontPadding = false
        maxLines = 2
    }
    val badge = TextView(this).apply {
        text = badgeText
        textSize = 10f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(accent)
        gravity = Gravity.CENTER
        setPadding(dp(8), dp(4), dp(8), dp(4))
        background = rounded(Color.TRANSPARENT, dp(9), accent)
        visibility = if (badgeText.isBlank()) View.GONE else View.VISIBLE
    }
    val root = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setPadding(dp(12), dp(9), dp(11), dp(9))
        background = rounded(MibuColors.card, dp(13), MibuColors.line)
        layoutParams = fullWidth(dp(8)).apply { height = dp(64) }
        addView(ImageView(this@mibuLiveRow).apply {
            setImageResource(iconRes)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
        }, LinearLayout.LayoutParams(dp(42), dp(42)).apply { setMargins(0, 0, dp(10), 0) })
        addView(LinearLayout(this@mibuLiveRow).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_VERTICAL
            addView(title)
            addView(value)
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f))
        addView(badge)
        if (onClick != null) {
            isClickable = true
            isFocusable = true
            setOnClickListener { onClick() }
            addView(TextView(this@mibuLiveRow).apply {
                text = "\u203a"
                textSize = 28f
                setTextColor(MibuColors.muted)
                gravity = Gravity.CENTER
            }, LinearLayout.LayoutParams(dp(24), LinearLayout.LayoutParams.MATCH_PARENT))
        }
    }
    return MibuLiveRow(root, title, value, badge)
}

fun Activity.mibuAction(
    iconRes: Int,
    titleText: String,
    subtitleText: String,
    accent: Int,
    primary: Boolean = false,
    onClick: () -> Unit,
): MibuLiveRow {
    val row = mibuLiveRow(iconRes, titleText, subtitleText, accent, onClick = onClick)
    row.root.background = if (primary) neonBackground() else rounded(MibuColors.card, dp(14), MibuColors.line)
    row.root.layoutParams = fullWidth(dp(8)).apply { height = dp(if (primary) 68 else 62) }
    if (primary) row.title.textSize = 18f
    return row
}

fun Activity.mibuTimeCard(label: String, value: String, date: String, accent: Int): Pair<LinearLayout, TextView> {
    val valueView = TextView(this).apply {
        text = value
        textSize = 24f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(accent)
        gravity = Gravity.CENTER_HORIZONTAL
        includeFontPadding = false
    }
    val root = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER
        setPadding(dp(8), dp(8), dp(8), dp(8))
        background = rounded(MibuColors.card, dp(13), accent)
        addView(TextView(this@mibuTimeCard).apply {
            text = label
            textSize = 11f
            setTextColor(MibuColors.muted)
            gravity = Gravity.CENTER
        })
        addView(valueView)
        addView(TextView(this@mibuTimeCard).apply {
            text = date
            textSize = 10f
            setTextColor(MibuColors.muted)
            gravity = Gravity.CENTER
        })
    }
    return root to valueView
}

fun Activity.mibuCountdown(): MibuCountdown {
    val title = TextView(this).apply {
        text = "Time Remaining"
        textSize = 12f
        setTextColor(MibuColors.muted)
        gravity = Gravity.CENTER
    }
    val value = TextView(this).apply {
        text = "-- : -- : --"
        textSize = 31f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(MibuColors.purple)
        gravity = Gravity.CENTER
        includeFontPadding = false
    }
    val units = TextView(this).apply {
        text = "HOURS       MINUTES       SECONDS"
        textSize = 9f
        setTextColor(MibuColors.muted)
        gravity = Gravity.CENTER
    }
    val root = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER
        setPadding(dp(10), dp(8), dp(10), dp(8))
        background = rounded(Color.rgb(11, 8, 28), dp(14), MibuColors.purple)
        layoutParams = fullWidth(dp(8)).apply { height = dp(92) }
        addView(title)
        addView(value)
        addView(units)
    }
    return MibuCountdown(root, title, value, units)
}

fun Activity.mibuStep(number: Int, iconRes: Int, title: String, body: String, accent: Int): LinearLayout =
    LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setPadding(dp(10), dp(8), dp(10), dp(8))
        background = rounded(MibuColors.card, dp(12), MibuColors.line)
        layoutParams = fullWidth(dp(7)).apply { height = dp(76) }
        addView(TextView(this@mibuStep).apply {
            text = number.toString()
            textSize = 20f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(accent)
            gravity = Gravity.CENTER
            background = rounded(Color.TRANSPARENT, dp(21), accent)
        }, LinearLayout.LayoutParams(dp(42), dp(42)).apply { setMargins(0, 0, dp(8), 0) })
        addView(LinearLayout(this@mibuStep).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_VERTICAL
            addView(TextView(this@mibuStep).apply {
                text = title
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
            })
            addView(TextView(this@mibuStep).apply {
                text = body
                textSize = 11f
                setTextColor(MibuColors.muted)
                maxLines = 2
            })
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.MATCH_PARENT, 1f))
        addView(ImageView(this@mibuStep).apply {
            setImageResource(iconRes)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
        }, LinearLayout.LayoutParams(dp(48), dp(48)).apply { setMargins(dp(8), 0, 0, 0) })
    }

@Suppress("UseSwitchCompatOrMaterialCode")
fun Activity.mibuToggle(label: String, detail: String, checked: Boolean, accent: Int, onChanged: (Boolean) -> Unit): LinearLayout =
    LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        setPadding(dp(12), dp(8), dp(10), dp(8))
        background = rounded(MibuColors.card, dp(12), accent)
        layoutParams = fullWidth(dp(8)).apply { height = dp(62) }
        addView(LinearLayout(this@mibuToggle).apply {
            orientation = LinearLayout.VERTICAL
            addView(TextView(this@mibuToggle).apply {
                text = label
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
            })
            addView(TextView(this@mibuToggle).apply {
                text = detail
                textSize = 10f
                setTextColor(MibuColors.muted)
            })
        }, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        addView(Switch(this@mibuToggle).apply {
            isChecked = checked
            setOnCheckedChangeListener { _, value -> onChanged(value) }
        })
    }

fun Activity.mibuSection(title: String): TextView = TextView(this).apply {
    text = title.uppercase()
    textSize = 10f
    typeface = Typeface.DEFAULT_BOLD
    setTextColor(MibuColors.muted)
    setPadding(dp(4), dp(8), dp(4), dp(7))
}

fun Activity.footer(): TextView = TextView(this).apply {
    text = "By the THETECHGUY TOOL team"
    textSize = 10f
    setTextColor(MibuColors.muted)
    gravity = Gravity.CENTER
    setPadding(0, dp(12), 0, dp(6))
    layoutParams = fullWidth()
}

// Compact compatibility helpers used by proof and secondary screens.
fun Activity.mibuPage(brand: String, title: String, build: LinearLayout.() -> Unit) {
    mibuScreen {
        addView(mibuBrandHeader(onBack = { finish() }))
        addView(mibuHeading(brand, title))
        build()
    }
}

fun Activity.mibuCard(title: String, body: String): TextView = TextView(this).apply {
    text = if (body.isBlank()) title else "$title\n$body"
    textSize = 12f
    setTextColor(Color.WHITE)
    setPadding(dp(14), dp(12), dp(14), dp(12))
    background = rounded(MibuColors.card, dp(12), MibuColors.line)
    layoutParams = fullWidth(dp(8))
}

fun Activity.mibuButton(text: String, primary: Boolean = false, onClick: () -> Unit): Button = Button(this).apply {
    this.text = text
    textSize = 12f
    typeface = Typeface.DEFAULT_BOLD
    setTextColor(Color.WHITE)
    background = if (primary) neonBackground() else rounded(MibuColors.card, dp(12), MibuColors.line)
    setOnClickListener { onClick() }
    layoutParams = fullWidth(dp(8)).apply { height = dp(54) }
}

fun Activity.rounded(color: Int, radius: Int, stroke: Int, strokeWidth: Int = 1): GradientDrawable =
    GradientDrawable().apply {
        setColor(color)
        cornerRadius = radius.toFloat()
        setStroke(dp(strokeWidth), stroke)
    }

fun Activity.neonBackground(): LayerDrawable {
    val glow = GradientDrawable(
        GradientDrawable.Orientation.LEFT_RIGHT,
        intArrayOf(Color.argb(210, 255, 105, 30), Color.argb(220, 210, 51, 255), Color.argb(210, 39, 139, 255)),
    ).apply { cornerRadius = dp(15).toFloat() }
    val inner = GradientDrawable(
        GradientDrawable.Orientation.LEFT_RIGHT,
        intArrayOf(Color.rgb(32, 12, 28), Color.rgb(22, 12, 44), Color.rgb(8, 20, 52)),
    ).apply { cornerRadius = dp(13).toFloat() }
    return LayerDrawable(arrayOf(glow, inner)).apply {
        setLayerInset(1, dp(2), dp(2), dp(2), dp(2))
    }
}

fun Activity.dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

private fun Activity.mibuIconButton(symbol: String, description: String, callback: () -> Unit): TextView =
    TextView(this).apply {
        text = symbol
        textSize = 26f
        setTextColor(Color.WHITE)
        gravity = Gravity.CENTER
        contentDescription = description
        background = rounded(Color.rgb(8, 12, 25), dp(19), MibuColors.purple)
        isClickable = true
        isFocusable = true
        setOnClickListener { callback() }
    }

private fun Activity.fullWidth(bottom: Int = 0): LinearLayout.LayoutParams =
    LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
        setMargins(0, 0, 0, bottom)
    }

object MibuColors {
    val background = Color.rgb(3, 5, 13)
    val panel = Color.rgb(6, 9, 20)
    val card = Color.rgb(9, 14, 28)
    val line = Color.rgb(43, 56, 83)
    val muted = Color.rgb(165, 175, 198)
    val orange = Color.rgb(255, 112, 38)
    val purple = Color.rgb(180, 74, 255)
    val blue = Color.rgb(45, 151, 255)
    val cyan = Color.rgb(34, 218, 255)
    val green = Color.rgb(70, 242, 124)
    val red = Color.rgb(255, 91, 102)
}
