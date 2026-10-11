import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show TargetPlatform, defaultTargetPlatform;
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:wakelock_plus/wakelock_plus.dart';

import 'theme.dart';
import 'services/history_service.dart';
import 'services/settings_service.dart';
import 'services/session_controller.dart';
import 'services/foreground_monitor.dart';
import 'screens/timer_screen.dart';
import 'screens/history_screen.dart';
import 'screens/schedule_screen.dart';
import 'screens/settings_screen.dart';

/// Platform channel for foreground app detection (used by Android native code)
const _channel = MethodChannel('com.focuscapsule.android/foreground');

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Enable wake lock so screen doesn't dim during focus sessions
  WakelockPlus.enable();

  final historyService = HistoryService();
  await historyService.init();

  final settingsService = SettingsService();
  await settingsService.init();

  final controller = SessionController(historyService: historyService);

  // Request notification permission for Android 13+
  if (await _requestForegroundPermission()) {
    // Start foreground monitor on mobile platforms
    if (defaultTargetPlatform == TargetPlatform.android) {
      _initForegroundMonitor(controller);
    }
  }

  runApp(
    MultiProvider(
      providers: [
        Provider<HistoryService>.value(value: historyService),
        Provider<SettingsService>.value(value: settingsService),
        Provider<SessionController>.value(value: controller),
      ],
      child: const FocusCapsuleApp(),
    ),
  );
}

/// Request usage access permission on Android.
Future<bool> _requestForegroundPermission() async {
  if (defaultTargetPlatform != TargetPlatform.android) return true;
  
  try {
    // This will open the settings page for Usage Stats
    // The user needs to toggle it ON for Focus Capsule
    _channel.invokeMethod<void>('requestUsageAccess');
    return false; // Will be checked again later
  } catch (e) {
    return false;
  }
}

/// Set up foreground detection via platform channel.
void _initForegroundMonitor(SessionController controller) {
  _channel.setMethodCallHandler((call) async {
    switch (call.method) {
      case 'onForegroundChange':
        final args = call.arguments as Map<dynamic, dynamic>;
        final processName = args['process'] as String? ?? '';
        final windowTitle = args['title'] as String? ?? '';
        controller.onForegroundChange(processName, windowTitle);
        break;
      case 'onOverlayDismissed':
        final currentProcess = call.arguments as String? ?? '';
        controller.onOverlayDismissed(currentProcess);
        break;
    }
    return;
  });
}

/// Show the Android system overlay window
Future<void> showAndroidOverlay(
  String appName,
  int seconds,
  List<String> allowedApps,
) async {
  if (defaultTargetPlatform != TargetPlatform.android) return;
  try {
    await _channel.invokeMethod<void>('showOverlay', {
      'appName': appName,
      'returnSeconds': seconds,
      'allowedApps': allowedApps,
    });
  } catch (e) {
    // Overlay permission might be denied
  }
}

/// Hide the Android system overlay window
Future<void> hideAndroidOverlay() async {
  if (defaultTargetPlatform != TargetPlatform.android) return;
  try {
    await _channel.invokeMethod<void>('hideOverlay');
  } catch (e) {}
}

class FocusCapsuleApp extends StatelessWidget {
  const FocusCapsuleApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '专注神器',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const _HomeView(),
    );
  }
}

class _HomeView extends StatefulWidget {
  const _HomeView();

  @override
  State<_HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends State<_HomeView> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    TimerScreen(),
    HistoryScreen(),
    ScheduleScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.3),
              blurRadius: 8,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (i) => setState(() => _currentIndex = i),
          selectedItemColor: AppTheme.accent,
          unselectedItemColor: AppTheme.textSecondary,
          type: BottomNavigationBarType.fixed,
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.timer_outlined),
              activeIcon: Icon(Icons.timer),
              label: '专注',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.history_outlined),
              activeIcon: Icon(Icons.history),
              label: '历史',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.calendar_today_outlined),
              activeIcon: Icon(Icons.calendar_today),
              label: '日程',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.settings_outlined),
              activeIcon: Icon(Icons.settings),
              label: '设置',
            ),
          ],
        ),
      ),
    );
  }
}
