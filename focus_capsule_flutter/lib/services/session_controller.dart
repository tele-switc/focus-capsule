import 'dart:async';
import 'package:flutter/foundation.dart';

import '../models.dart';
import 'history_service.dart';

class SessionUpdate {
  final SessionStatus status;
  final int elapsed;
  final int total;
  final int escRemaining;
  final int escUsed;
  final int distractionCount;
  final String mode;
  final String currentApp;
  final int breakRemaining;

  const SessionUpdate({
    required this.status,
    required this.elapsed,
    required this.total,
    required this.escRemaining,
    required this.escUsed,
    required this.distractionCount,
    required this.mode,
    this.currentApp = '',
    this.breakRemaining = 0,
  });
}

typedef UpdateCallback = void Function(SessionUpdate update);
typedef CompleteCallback = void Function(SessionRecord record);

class SessionController extends ChangeNotifier {
  final HistoryService historyService;

  FocusConfig? _config;
  int _totalSeconds = 0;
  int _elapsed = 0;
  int _escRemaining = 0;
  int _escUsed = 0;
  int _distractions = 0;
  final Map<String, int> _distractionApps = {};
  final List<DistractionEntry> _distractionEvents = [];
  SessionStatus _status = SessionStatus.idle;
  int _breakRemaining = 0;
  DateTime? _startedAt;
  bool _terminated = false;

  Timer? _timer;
  Timer? _breakTimer;

  final List<UpdateCallback> _updateCallbacks = [];
  final List<CompleteCallback> _completeCallbacks = [];

  SessionController({required this.historyService});

  SessionStatus get status => _status;
  int get elapsed => _elapsed;
  int get total => _totalSeconds;
  int get escRemaining => _escRemaining;
  int get escUsed => _escUsed;
  int get distractionCount => _distractions;
  int get breakRemaining => _breakRemaining;
  bool get isRunning => isActive;
  bool get isActive =>
      _status == SessionStatus.running ||
      _status == SessionStatus.break_ ||
      _status == SessionStatus.overlay;
  FocusConfig? get config => _config;
  List<DistractionEntry> get distractionEvents => List.unmodifiable(_distractionEvents);

  void onUpdate(UpdateCallback callback) => _updateCallbacks.add(callback);
  void onComplete(CompleteCallback callback) => _completeCallbacks.add(callback);

  void startSession(FocusConfig config) {
    final duration = config.durationMinutes.clamp(1, 2147483647);
    _config = FocusConfig(
      whitelist: config.whitelist,
      durationMinutes: duration,
      mode: config.mode,
      maxEsc: config.maxEsc,
      escBreakMinutes: config.escBreakMinutes,
      goal: config.goal,
      customApps: config.customApps,
    );
    _totalSeconds = _config!.durationMinutes * 60;
    _elapsed = 0;
    _escRemaining = _config!.maxEsc;
    _escUsed = 0;
    _distractions = 0;
    _distractionApps.clear();
    _distractionEvents.clear();
    _status = SessionStatus.running;
    _breakRemaining = 0;
    _startedAt = DateTime.now();
    _terminated = false;

    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), _onTimerTick);

    _emitUpdate();
  }

  void _onTimerTick(Timer timer) {
    if (_status == SessionStatus.running || _status == SessionStatus.overlay) {
      _elapsed++;
      if (_elapsed >= _totalSeconds) {
        completeSession();
      } else {
        _emitUpdate();
      }
    }
  }

  void _emitUpdate() {
    notifyListeners();
    final update = SessionUpdate(
      status: _status,
      elapsed: _elapsed,
      total: _totalSeconds,
      escRemaining: _escRemaining,
      escUsed: _escUsed,
      distractionCount: _distractions,
      mode: _config?.mode ?? 'Standard',
      currentApp: _config?.whitelist.firstOrNull ?? '',
      breakRemaining: _breakRemaining,
    );
    for (final cb in _updateCallbacks) {
      try {
        cb(update);
      } catch (e) {
        debugPrint('更新回调错误: $e');
      }
    }
  }

  void handleEscape() {
    if (_terminated ||
        _status != SessionStatus.running ||
        _escRemaining <= 0) {
      return;
    }

    _escRemaining--;
    _escUsed++;
    _status = SessionStatus.break_;
    _breakRemaining = (_config?.escBreakMinutes ?? 3) * 60;

    _breakTimer?.cancel();
    _breakTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_terminated || _status != SessionStatus.break_) {
        timer.cancel();
        return;
      }
      _breakRemaining--;
      if (_breakRemaining <= 0) {
        timer.cancel();
        _onBreakEnd();
      } else {
        _emitUpdate();
      }
    });

    _emitUpdate();
  }

  void _onBreakEnd() {
    if (_terminated || _status != SessionStatus.break_ || _breakRemaining > 0) return;
    _status = SessionStatus.running;
    _breakRemaining = 0;
    _emitUpdate();
  }

  void onForegroundChange(String processName, String windowTitle) {
    if (_terminated || _status != SessionStatus.running) return;
    if (_config == null) return;

    final process = processName.trim().toLowerCase();
    if (process.isEmpty) return;

    final allowed = _config!.whitelist.any(
      (pa) => pa.trim().toLowerCase() == process,
    );
    if (allowed) return;

    _distractions++;
    _distractionApps[process] = (_distractionApps[process] ?? 0) + 1;
    _distractionEvents.add(
      DistractionEntry(
        processName: process,
        windowTitle: windowTitle.trim().isEmpty ? null : windowTitle.trim(),
        occurredAt: DateTime.now().toIso8601String(),
      ),
    );

    final mode = _config!.mode;
    if ((mode == 'Deep' || mode == 'Standard') && _config!.whitelist.isNotEmpty) {
      _status = SessionStatus.overlay;
    }
    _emitUpdate();
  }

  void completeSession() {
    if (_terminated || _status != SessionStatus.running) return;
    _status = SessionStatus.completed;
    _timer?.cancel();
    _breakTimer?.cancel();
    _saveAndNotify();
  }

  void terminate() {
    if (!isActive) return;
    _terminated = true;
    _status = SessionStatus.terminated;
    _timer?.cancel();
    _breakTimer?.cancel();
    _saveAndNotify();
  }

  void _saveAndNotify() {
    final record = _getRecord();
    historyService.saveRecord(record);
    for (final cb in _completeCallbacks) {
      try {
        cb(record);
      } catch (e) {
        debugPrint('完成回调错误: $e');
      }
    }
  }

  SessionRecord _getRecord() {
    final now = DateTime.now();
    final started = _startedAt ?? now;
    final outcome = _status == SessionStatus.terminated
        ? 'terminated'
        : _status == SessionStatus.completed
            ? 'completed'
            : _status.value;
    return SessionRecord(
      startedAt: started.toIso8601String(),
      endedAt: now.toIso8601String(),
      durationMinutes: _config?.durationMinutes ?? 0,
      actualFocusSeconds: _elapsed,
      distractionCount: _distractions,
      escUsed: _escUsed,
      mode: _config?.mode ?? 'Standard',
      whitelistedApps: _config?.whitelist.toList() ?? [],
      distractions: _distractionEvents.map((e) => e.toJson()).toList(),
      goal: _config?.goal,
      outcome: outcome,
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _breakTimer?.cancel();
    super.dispose();
  }
}
