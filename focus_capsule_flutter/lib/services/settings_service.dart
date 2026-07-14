import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models.dart';

class SettingsService {
  static const _kGoal = 'goal';
  static const _kDuration = 'duration_minutes';
  static const _kMode = 'mode';
  static const _kMaxEsc = 'max_esc';
  static const _kEscBreak = 'esc_break_minutes';
  static const _kWhitelist = 'whitelist';
  static const _kCustomApps = 'custom_apps';
  static const _kScheduleRules = 'schedule_rules';

  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  FocusConfig loadConfig() {
    if (_prefs == null) return FocusConfig();
    final whitelist = _getStringList(_kWhitelist);
    final customApps = _getStringList(_kCustomApps);
    return FocusConfig(
      whitelist: whitelist,
      durationMinutes: _prefs!.getInt(_kDuration) ?? 25,
      mode: _prefs!.getString(_kMode) ?? 'Standard',
      maxEsc: _prefs!.getInt(_kMaxEsc) ?? 2,
      escBreakMinutes: _prefs!.getInt(_kEscBreak) ?? 3,
      goal: _prefs!.getString(_kGoal),
      customApps: customApps,
    );
  }

  Future<void> saveConfig(FocusConfig config) async {
    if (_prefs == null) return;
    await _prefs!.setString(_kGoal, config.goal ?? '');
    await _prefs!.setInt(_kDuration, config.durationMinutes);
    await _prefs!.setString(_kMode, config.mode);
    await _prefs!.setInt(_kMaxEsc, config.maxEsc);
    await _prefs!.setInt(_kEscBreak, config.escBreakMinutes);
    await _prefs!.setStringList(_kWhitelist, config.whitelist);
    await _prefs!.setStringList(_kCustomApps, config.customApps);
  }

  List<ScheduleRule> loadScheduleRules() {
    if (_prefs == null) return [];
    final raw = _prefs!.getString(_kScheduleRules);
    if (raw == null || raw.isEmpty) return [];
    try {
      final data = jsonDecode(raw) as List;
      return data
          .whereType<Map>()
          .map((d) => ScheduleRule.fromJson(d as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> saveScheduleRules(List<ScheduleRule> rules) async {
    if (_prefs == null) return;
    final encoder = JsonEncoder();
    await _prefs!.setString(
      _kScheduleRules,
      encoder.convert(rules.map((r) => r.toJson()).toList()),
    );
  }

  List<String> _getStringList(String key) {
    final data = _prefs?.getStringList(key);
    if (data == null) return [];
    return data.where((s) => s.isNotEmpty).toList();
  }
}
