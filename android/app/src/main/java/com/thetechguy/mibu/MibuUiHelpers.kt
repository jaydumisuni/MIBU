package com.thetechguy.mibu

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

fun Activity.mibuPage(brand: String, title: String, build: LinearLayout.() -> Unit) {
    val root = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER_HORIZONTAL
        setPadding(dp(18), dp(52), dp(18), dp(22))
        setBackgroundColor(Color.rgb(5, 9, 19))
    }

    val brandText = TextView(this).apply {
        text = brand
        textSize = 24f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Color.WHITE)
        gravity = Gravity.CENTER
    }
    root.addView(brandText, fullWidth(bottom = dp(4)))

    val titleText = TextView(this).apply {
        text = title
        textSize = 12f
        setTextColor(Color.rgb(145, 160, 190))
        gravity = Gravity.CENTER
    }
    root.addView(titleText, fullWidth(bottom = dp(18)))

    root.build()

    val scroll = ScrollView(this)
    scroll.addView(root)
    setContentView(scroll)
}

fun Activity.mibuCard(title: String, body: String): TextView {
    return TextView(this).apply {
        text = if (body.isBlank()) title else "$title\n$body"
        textSize = 12f
        setTextColor(Color.WHITE)
        setPadding(dp(18), dp(15), dp(18), dp(15))
        background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
        layoutParams = fullWidth(bottom = dp(12))
    }
}

fun Activity.mibuExpectedImage(resId: Int): ImageView {
    return ImageView(this).apply {
        setImageResource(resId)
        adjustViewBounds = true
        scaleType = ImageView.ScaleType.CENTER_CROP
        background = rounded(Color.rgb(8, 15, 30), dp(18), Color.rgb(32, 55, 90))
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(250)).apply {
            setMargins(0, 0, 0, dp(12))
        }
    }
}

fun Activity.mibuButton(text: String, primary: Boolean = false, onClick: () -> Unit): Button {
    return Button(this).apply {
        this.text = text
        textSize = if (primary) 13f else 12f
        setTextColor(Color.WHITE)
        background = if (primary) {
            rounded(Color.rgb(30, 88, 255), dp(14), Color.rgb(75, 114, 255))
        } else {
            rounded(Color.rgb(14, 23, 40), dp(14), Color.rgb(40, 66, 106))
        }
        setOnClickListener { onClick() }
        layoutParams = fullWidth(bottom = dp(10))
    }
}

fun Activity.footer(): TextView {
    return TextView(this).apply {
        text = "By the THETECHGUY TOOL team"
        textSize = 11f
        setTextColor(Color.rgb(145, 160, 190))
        gravity = Gravity.CENTER
        setPadding(0, dp(18), 0, dp(8))
        layoutParams = fullWidth(bottom = dp(4))
    }
}

fun Activity.rounded(color: Int, radius: Int, stroke: Int): GradientDrawable {
    return GradientDrawable().apply {
        setColor(color)
        cornerRadius = radius.toFloat()
        setStroke(dp(1), stroke)
    }
}

fun Activity.dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

private fun Activity.fullWidth(bottom: Int = 0): LinearLayout.LayoutParams {
    return LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
        setMargins(0, 0, 0, bottom)
    }
}
