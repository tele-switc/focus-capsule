import 'package:flutter/services.dart';
import 'dart:async';

/// Platform channel for Android foreground app detection.
/// Wraps UsageStatsManager polling to notify Flutter when the frontmost app changes.
class ForegroundMonitor {
  static const _channel = MethodChannel('com.focuscapsule.android/foreground');
  
  final VoidCallback onForegroundChange;
  Timer? _pollTimer;
  String _lastProcess = '';

  ForegroundMonitor({required this.onForegroundChange});

  void start() {
    if (_pollTimer != null) return;
    // Poll every 1 second on Android
    _pollTimer = Timer.periodic(const Duration(seconds: 1), (_) => _poll());
  }

  void stop() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  void _poll() {
    try {
      _channel.invokeMethod<String>('getForegroundApp').then((appName) {
        if (appName != null && appName.isNotEmpty && appName != _lastProcess) {
          _lastProcess = appName;
          onForegroundChange();
        }
      });
    } catch (e) {
      // Ignore polling errors
    }
  }
}
