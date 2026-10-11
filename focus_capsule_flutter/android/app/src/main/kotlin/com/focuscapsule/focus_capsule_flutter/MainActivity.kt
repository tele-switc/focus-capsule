package com.focuscapsule.android

import android.content.Context
import android.os.Build
import android.app.usage.UsageStats
import android.app.usage.UsageStatsManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.util.*

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.focuscapsule.android/foreground"
    private lateinit var methodChannel: MethodChannel
    private lateinit var context: android.content.Context
    private var lastPackageName = ""
    private var overlayWindow: OverlayWindow? = null
    private var overlayShowing = false
    
    override fun attachBaseContext(base: android.content.Context?) {
        super.attachBaseContext(base)
        context = base!!
    }
    
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        methodChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
        methodChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "getForegroundApp" -> {
                    val pkg = getForegroundPackageName()
                    if (pkg != null && pkg != lastPackageName) {
                        lastPackageName = pkg
                        val info = mapOf(
                            "process" to pkg.lowercase(),
                            "title" to ""
                        )
                        methodChannel.invokeMethod("onForegroundChange", info)
                    }
                    result.success(pkg?.let { 
                        it.split("\\.".toRegex()).dropLast(1).joinToString(".")
                    })
                }
                "showOverlay" -> {
                    @Suppress("UNCHECKED_CAST")
                    val args = call.arguments as Map<String, Any?>
                    val appName = args["appName"] as String? ?: ""
                    val returnSeconds = (args["returnSeconds"] as Number?)?.toInt() ?: 3
                    @Suppress("UNCHECKED_CAST")
                    val allowedApps = args["allowedApps"] as List<String>? ?: emptyList()
                    
                    if (!overlayShowing) {
                        overlayWindow = OverlayWindow(context)
                        overlayWindow?.setOnDismiss {
                            overlayShowing = false
                            methodChannel.invokeMethod("onOverlayDismissed", "")
                        }
                        overlayWindow?.show(appName, returnSeconds, allowedApps)
                        overlayShowing = true
                    }
                    result.success(null)
                }
                "hideOverlay" -> {
                    overlayWindow?.dismiss()
                    overlayShowing = false
                    result.success(null)
                }
                "requestUsageAccess" -> {
                    try {
                        val intent = android.content.Intent(android.provider.Settings.ACTION_USAGE_ACCESS_SETTINGS)
                        intent.flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK
                        context.startActivity(intent)
                    } catch (e: Exception) {}
                    result.success(null)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }
    
    /**
     * Get the currently foregrounded application package name using UsageStatsManager.
     * Returns the top app name (last 64 chars to avoid truncation).
     */
    private fun getForegroundPackageName(): String? {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            val usageStatsManager = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val time = System.currentTimeMillis()
            
            // Get stats for the last 1 second to find most recent top app
            val stats = usageStatsManager.queryUsageStats(
                UsageStatsManager.INTERVAL_BEST,
                time - 1000,
                time
            )
            
            if (stats != null && stats.isNotEmpty()) {
                var topApp: UsageStats? = null
                for (app in stats.sortedBy { it.lastTimeUsed }) {
                    if (topApp == null || app.lastTimeUsed > topApp!!.lastTimeUsed) {
                        topApp = app
                    }
                }
                
                if (topApp != null) {
                    val packageName = topApp!!.packageName
                    // Filter out system UI and our own process
                    if (packageName != "com.android.systemui" && 
                        !packageName.startsWith("io.flutter")) {
                        return packageName.takeLast(64)
                    }
                }
            }
            
            // Fallback: query last 1 minute by minute intervals
            try {
                val minuteStats = usageStatsManager.queryAndAggregateUsageStats(time - 60000, time)
                return minuteStats.values.maxByOrNull { it.lastTimeUsed }?.packageName
            } catch (e: Exception) {
                // Ignore
            }
        }
        return null
    }
}
