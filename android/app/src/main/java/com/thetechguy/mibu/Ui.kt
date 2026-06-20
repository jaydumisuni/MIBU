package com.thetechguy.mibu

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

fun Activity.mibuPage(title: String, subtitle: String, body: LinearLayout.() -> Unit) {
    val root = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER_HORIZONTAL
        setPadding(dp(22), dp(28), dp(22), dp(24))
        setBackgroundColor(Color.rgb(5, 9, 19))
    }
    val header = TextView(this).apply {
        text = title
        textSize = 34f
        typeface = Typeface.DEFAULT_BOLD
        setTextColor(Color.WHITE)
        gravity = Gravity.CENTER
    }
    val sub = TextView(this).apply {
        text = subtitle
        textSize = 13f
        setTextColor(Color.rgb(145, 160, 190))
        gravity = Gravity.CENTER
        setPadding(0, 0, 0, dp(18))
    }
    root.addView(header)
    root.addView(sub)
    root.body()
    val scroll = ScrollView(this)
    scroll.addView(root)
    setContentView(scroll)
}

fun Activity.mibuCard(title: String, content: String): TextView {
    return TextView(this).apply {
        text = "$title\n$content"
        textSize = 15f
        setTextColor(Color.WHITE)
        setPadding(dp(18), dp(15), dp(18), dp(15))
        background = rounded(Color.rgb(13, 20, 35), dp(16), Color.rgb(30, 40, 65))
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            setMargins(0, 0, 0, dp(12))
        }
    }
}

fun Activity.mibuButton(textValue: String, primary: Boolean = false, action: () -> Unit): Button {
    return Button(this).apply {
        text = textValue
        textSize = if (primary) 16f else 15f
        setTextColor(Color.WHITE)
        background = if (primary) {
            rounded(Color.rgb(30, 88, 255), dp(14), Color.rgb(75, 114, 255))
        } else {
            rounded(Color.rgb(14, 23, 40), dp(14), Color.rgb(40, 66, 106))
        }
        setOnClickListener { action() }
        layoutParams = LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            setMargins(0, 0, 0, dp(10))
        }
    }
}

fun Activity.footer(): TextView {
    return TextView(this).apply {
        text = "By the THETECHGUY TOOL team"
        textSize = 13f
        setTextColor(Color.rgb(145, 160, 190))
        gravity = Gravity.CENTER
        setPadding(0, dp(18), 0, dp(8))
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
