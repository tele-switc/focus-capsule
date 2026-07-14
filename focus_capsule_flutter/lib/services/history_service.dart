import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../models.dart';

class HistoryService {
  late final File _file;
  bool _loadBlocked = false;

  Future<void> _ensureInitialized() async {
    if (_file.existsSync()) return;
    final dir = await _getDataDir();
    dir.createSync(recursive: true);
    _file = File(p.join(dir.path, 'history.json'));
  }

  Future<Directory> _getDataDir() async {
    if (kIsWeb) {
      return Directory.systemTemp;
    }
    final dir = await getApplicationDocumentsDirectory();
    return dir;
  }

  Future<void> init() async {
    await _ensureInitialized();
  }

  Future<List<SessionRecord>> loadHistory() async {
    _loadBlocked = false;
    if (!_file.existsSync()) return [];
    try {
      final content = await _file.readAsString();
      final dynamic data = jsonDecode(content);
      return _deserializeRecords(data);
    } on IOException {
      debugPrint('无法读取历史记录: ${_file.path}');
      return [];
    } on FormatException {
      debugPrint('历史记录文件损坏: ${_file.path}');
      try {
        await _backupCorruptFile();
      } on IOException {
        _loadBlocked = true;
        debugPrint('无法备份损坏的历史记录文件');
      }
      return [];
    }
  }

  List<SessionRecord> _deserializeRecords(dynamic payload) {
    List<dynamic> recordsData;
    if (payload is Map && payload.containsKey('records')) {
      recordsData = payload['records'] as List;
    } else if (payload is List) {
      recordsData = payload;
    } else {
      throw ArgumentError('历史记录根节点必须是列表');
    }

    final records = <SessionRecord>[];
    for (final item in recordsData) {
      if (item is! Map) throw ArgumentError('历史记录条目必须是对象');
      final migrated = Map<String, dynamic>.from(item);
      if (!migrated.containsKey('outcome')) {
        migrated['outcome'] = migrated.remove('status') ?? 'completed';
      } else {
        migrated.remove('status');
      }
      migrated.putIfAbsent('outcome', () => 'completed');
      migrated.putIfAbsent('goal', () => null);
      migrated.putIfAbsent('distractions', () => <dynamic>[]);

      final knownFields = <String, dynamic>{};
      for (final fieldName in _recordFieldNames) {
        if (migrated.containsKey(fieldName)) {
          knownFields[fieldName] = migrated[fieldName];
        }
      }
      records.add(SessionRecord.fromJson(knownFields));
    }
    return records;
  }

  static const List<String> _recordFieldNames = [
    'started_at',
    'ended_at',
    'duration_minutes',
    'actual_focus_seconds',
    'distraction_count',
    'esc_used',
    'mode',
    'whitelisted_apps',
    'distractions',
    'goal',
    'outcome',
  ];

  Future<void> _backupCorruptFile() async {
    final timestamp = DateTime.now().toString().replaceAll(RegExp(r'[\s:.]'), '-');
    final backup = File('${_file.path}.corrupt-$timestamp.json');
    await _file.rename(backup.path);
  }

  Future<void> saveRecord(SessionRecord record) async {
    if (_loadBlocked) {
      throw StateError('拒绝在损坏的数据备份上覆盖历史记录');
    }
    var history = await loadHistory();
    history.add(record);
    if (history.length > 100) {
      history = history.sublist(history.length - 100);
    }
    final encoder = JsonEncoder.withIndent('  ');
    await _atomicWrite(encoder.convert(history.map((r) => r.toJson()).toList()));
  }

  Future<void> _atomicWrite(String payload) async {
    final dir = _file.parent;
    final tempFile = File(p.join(dir.path, '.${_file.path.split(Platform.pathSeparator).last}.tmp'));
    try {
      await tempFile.writeAsString('$payload\n', encoding: utf8);
      await tempFile.rename(_file.path);
    } finally {
      if (tempFile.existsSync()) {
        await tempFile.delete();
      }
    }
  }

  Future<void> clearHistory() async {
    _loadBlocked = false;
    if (_file.existsSync()) {
      await _file.delete();
    }
  }
}
