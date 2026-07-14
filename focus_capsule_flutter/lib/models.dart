enum IntensityMode {
  light('Light', '轻模式 — 仅通知提醒'),
  standard('Standard', '标准模式 — 弹窗 + 休息'),
  deep('Deep', '深度模式 — 严格锁定');

  const IntensityMode(this.label, this.description);
  final String label;
  final String description;

  static IntensityMode fromString(String value) {
    return IntensityMode.values.firstWhere(
      (m) => m.label == value,
      orElse: () => IntensityMode.standard,
    );
  }
}

enum SessionStatus {
  idle('idle'),
  running('running'),
  break_('break'),
  overlay('overlay'),
  completed('completed'),
  terminated('terminated');

  const SessionStatus(this.value);
  final String value;

  static SessionStatus fromString(String value) {
    return SessionStatus.values.firstWhere(
      (s) => s.value == value,
      orElse: () => SessionStatus.idle,
    );
  }
}

class FocusConfig {
  final List<String> whitelist;
  final int durationMinutes;
  final String mode;
  final int maxEsc;
  final int escBreakMinutes;
  final String? goal;
  final List<String> customApps;

  FocusConfig({
    this.whitelist = const [],
    this.durationMinutes = 25,
    this.mode = 'Standard',
    this.maxEsc = 2,
    this.escBreakMinutes = 3,
    this.goal,
    this.customApps = const [],
  });

  FocusConfig copyWith({
    List<String>? whitelist,
    int? durationMinutes,
    String? mode,
    int? maxEsc,
    int? escBreakMinutes,
    String? goal,
    List<String>? customApps,
  }) {
    return FocusConfig(
      whitelist: whitelist ?? this.whitelist,
      durationMinutes: durationMinutes ?? this.durationMinutes,
      mode: mode ?? this.mode,
      maxEsc: maxEsc ?? this.maxEsc,
      escBreakMinutes: escBreakMinutes ?? this.escBreakMinutes,
      goal: goal ?? this.goal,
      customApps: customApps ?? this.customApps,
    );
  }
}

class ScheduleRule {
  final int startHour;
  final int startMinute;
  final int endHour;
  final int endMinute;
  final List<String> whitelistedApps;
  final String mode;
  final bool enabled;
  final String label;

  ScheduleRule({
    this.startHour = 0,
    this.startMinute = 0,
    this.endHour = 0,
    this.endMinute = 0,
    this.whitelistedApps = const [],
    this.mode = 'Deep',
    this.enabled = true,
    this.label = '',
  });

  Map<String, dynamic> toJson() => {
        'start_hour': startHour,
        'start_minute': startMinute,
        'end_hour': endHour,
        'end_minute': endMinute,
        'whitelisted_apps': whitelistedApps,
        'mode': mode,
        'enabled': enabled,
        'label': label,
      };

  factory ScheduleRule.fromJson(Map<String, dynamic> json) {
    final enabledValue = json['enabled'];
    bool enabled;
    if (enabledValue is String) {
      final normalized = enabledValue.trim().toLowerCase();
      enabled = ['true', '1', 'yes', 'on'].contains(normalized);
    } else {
      enabled = json['enabled'] ?? true;
    }
    return ScheduleRule(
      startHour: json['start_hour'] ?? 0,
      startMinute: json['start_minute'] ?? 0,
      endHour: json['end_hour'] ?? 0,
      endMinute: json['end_minute'] ?? 0,
      whitelistedApps: List<String>.from(json['whitelisted_apps'] ?? []),
      mode: json['mode'] ?? 'Deep',
      enabled: enabled,
      label: json['label'] ?? '',
    );
  }

  ScheduleRule copyWith({
    int? startHour,
    int? startMinute,
    int? endHour,
    int? endMinute,
    List<String>? whitelistedApps,
    String? mode,
    bool? enabled,
    String? label,
  }) {
    return ScheduleRule(
      startHour: startHour ?? this.startHour,
      startMinute: startMinute ?? this.startMinute,
      endHour: endHour ?? this.endHour,
      endMinute: endMinute ?? this.endMinute,
      whitelistedApps: whitelistedApps ?? this.whitelistedApps,
      mode: mode ?? this.mode,
      enabled: enabled ?? this.enabled,
      label: label ?? this.label,
    );
  }
}

class DistractionEntry {
  final String processName;
  final String? windowTitle;
  final String occurredAt;

  DistractionEntry({
    required this.processName,
    this.windowTitle,
    required this.occurredAt,
  });

  Map<String, dynamic> toJson() => {
        'process_name': processName,
        'window_title': windowTitle,
        'occurred_at': occurredAt,
      };

  factory DistractionEntry.fromJson(Map<String, dynamic> json) {
    return DistractionEntry(
      processName: json['process_name'] ?? '',
      windowTitle: json['window_title'],
      occurredAt: json['occurred_at'] ?? '',
    );
  }
}

class SessionRecord {
  final String startedAt;
  final String endedAt;
  final int durationMinutes;
  final int actualFocusSeconds;
  final int distractionCount;
  final int escUsed;
  final String mode;
  final List<String> whitelistedApps;
  final List<Map<String, dynamic>> distractions;
  final String? goal;
  final String outcome;

  SessionRecord({
    required this.startedAt,
    required this.endedAt,
    required this.durationMinutes,
    required this.actualFocusSeconds,
    required this.distractionCount,
    required this.escUsed,
    required this.mode,
    required this.whitelistedApps,
    this.distractions = const [],
    this.goal,
    this.outcome = 'completed',
  });

  Map<String, dynamic> toJson() => {
        'started_at': startedAt,
        'ended_at': endedAt,
        'duration_minutes': durationMinutes,
        'actual_focus_seconds': actualFocusSeconds,
        'distraction_count': distractionCount,
        'esc_used': escUsed,
        'mode': mode,
        'whitelisted_apps': whitelistedApps,
        'distractions': distractions,
        'goal': goal,
        'outcome': outcome,
      };

  factory SessionRecord.fromJson(Map<String, dynamic> json) {
    return SessionRecord(
      startedAt: json['started_at'] ?? '',
      endedAt: json['ended_at'] ?? '',
      durationMinutes: json['duration_minutes'] ?? 0,
      actualFocusSeconds: json['actual_focus_seconds'] ?? 0,
      distractionCount: json['distraction_count'] ?? 0,
      escUsed: json['esc_used'] ?? 0,
      mode: json['mode'] ?? 'Standard',
      whitelistedApps: List<String>.from(json['whitelisted_apps'] ?? []),
      distractions: (json['distractions'] as List<dynamic>?)
              ?.map((d) => d as Map<String, dynamic>)
              .toList() ??
          [],
      goal: json['goal'],
      outcome: json['outcome'] ?? 'completed',
    );
  }
}
