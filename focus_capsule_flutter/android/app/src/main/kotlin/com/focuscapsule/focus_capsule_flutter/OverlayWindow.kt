package com.focuscapsule.android

import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.ImageView
import android.widget.ProgressBar
import android.widget.TextView

/**
 * OverlayWindow — 显示在应用顶层的遮罩窗口。
 * 当用户切换到白名单外应用时自动弹出，要求用户切回专注应用。
 */
class OverlayWindow(private val context: Context) {
    private var windowManager: WindowManager? = null
    private var overlayView: View? = null
    private var isShowing = false
    
    private val params = WindowManager.LayoutParams().apply {
        width = WindowManager.LayoutParams.MATCH_PARENT
        height = WindowManager.LayoutParams.MATCH_PARENT
        type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }
        flags = (WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
                or WindowManager.LayoutParams.FLAG_FULLSCREEN)
        format = PixelFormat.TRANSLUCENT
        gravity = Gravity.CENTER
        packageName = context.packageName
    }
    
    private var onDismissCallback: (() -> Unit)? = null

    fun show(blockedAppName: String, returnSeconds: Int = 3, allowedApps: List<String> = emptyList()) {
        try {
            if (isShowing) hide()
            
            windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
            
            overlayView = LayoutInflater.from(context).inflate(
                R.layout.overlay_overlay, null
            ).apply {
                // Find elements
                val ivMarker = findViewById<ImageView>(R.id.iv_marker)
                val tvTitle = findViewById<TextView>(R.id.tv_title)
                val tvSubtitle = findViewById<TextView>(R.id.tv_subtitle)
                val tvCountdown = findViewById<TextView>(R.id.tv_countdown)
                val btnDismiss = findViewById<Button>(R.id.btn_dismiss)
                
                ivMarker.visibility = View.GONE
                tvTitle.text = "这不在本轮专注计划中"
                tvSubtitle.text = "请切回 $blockedAppName 继续刚才的目标"
                tvCountdown.text = "提醒将在 $returnSeconds 秒后关闭"
                
                btnDismiss.setOnClickListener {
                    dismiss()
                }
            }
            
            params.flags = (params.flags or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS)
            windowManager?.addView(overlayView, params)
            isShowing = true
            
            // Auto-dismiss after returnSeconds
            var remaining = returnSeconds
            val timer = java.util.Timer(true)
            val task = object : java.util.TimerTask() {
                override fun run() {
                    remaining--
                    if (remaining <= 0) {
                        cancel()
                        timer.cancel()
                        overlayView?.post { dismiss() }
                    } else {
                        overlayView?.post {
                            overlayView?.findViewById<TextView>(R.id.tv_countdown)
                                ?.text = "提醒将在 $remaining 秒后关闭"
                        }
                    }
                }
            }
            timer.scheduleAtFixedRate(task, 1000, 1000)
        } catch (e: Exception) {
            // Overlay permission denied — fall back to notification
            e.printStackTrace()
        }
    }
    
    fun hide() {
        dismiss()
    }
    
    fun dismiss() {
        try {
            if (isShowing && overlayView != null && windowManager != null) {
                windowManager?.removeView(overlayView)
                isShowing = false
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
    
    fun setOnDismiss(callback: () -> Unit) {
        onDismissCallback = callback
    }
    
    private fun isVisible(): Boolean {
        return isShowing
    }
    
}
