import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../services/history_service.dart';
import '../theme.dart';
import '../utils/format.dart';
import '../widgets/common.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<SessionRecord> _records = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = context.read<HistoryService>();
      final records = await service.loadHistory();
      setState(() {
        _records = records.reversed.toList();
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: SectionHeader(title: '专注历史'),
            ),
            // Summary bar
            if (_records.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                  decoration: BoxDecoration(
                    color: AppTheme.bgCard,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.borderSubtle),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _summaryStat('总次数', '${_records.length}'),
                      _summaryStat('总时长', formatDuration(
                        _records.fold(0, (sum, r) => sum + r.actualFocusSeconds),
                      )),
                      _summaryStat('平均专注', formatDuration(
                        _records.fold(0, (sum, r) => sum + r.actualFocusSeconds) ~/ _records.length,
                      )),
                      _summaryStat('完成率', '${(_records.where((r) => r.outcome == 'completed').length / _records.length * 100).toStringAsFixed(0)}%'),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.error_outline, color: AppTheme.textDanger, size: 48),
                              const SizedBox(height: 12),
                              Text('加载失败: $_error', style: const TextStyle(color: AppTheme.textDanger)),
                              const SizedBox(height: 12),
                              OutlinedButton(onPressed: _loadHistory, child: const Text('重试')),
                            ],
                          ),
                        )
                      : _records.isEmpty
                          ? Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.history, size: 64, color: AppTheme.textMuted.withValues(alpha: 0.4)),
                                  const SizedBox(height: 16),
                                  Text(
                                    '还没有专注记录',
                                    style: TextStyle(color: AppTheme.textSecondary, fontSize: 16),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    '开始第一次专注会话吧!',
                                    style: TextStyle(color: AppTheme.textMuted, fontSize: 13),
                                  ),
                                ],
                              ),
                            )
                          : RefreshIndicator(
                              onRefresh: _loadHistory,
                              child: ListView.separated(
                                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                                itemBuilder: (context, index) => _buildRecordCard(_records[index]),
                                separatorBuilder: (_, __) => const SizedBox(height: 10),
                                itemCount: _records.length,
                              ),
                            ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecordCard(SessionRecord record) {
    DateTime? date;
    try {
      date = DateTime.tryParse(record.startedAt);
    } catch (_) {}

    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                date != null ? DateFormat('MM-dd HH:mm').format(date) : record.startedAt.substring(5),
                style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600),
              ),
              _outcomeBadge(record.outcome),
            ],
          ),
          if (record.goal != null && record.goal!.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '目标: ${record.goal}',
              style: const TextStyle(color: AppTheme.accent, fontSize: 12),
            ),
          ],
          const Divider(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _miniStat('计划', '${record.durationMinutes}分钟'),
              _miniStat('实际', formatDuration(record.actualFocusSeconds)),
              _miniStat('干扰', '${record.distractionCount}次'),
              _miniStat('逃脱', '${record.escUsed}次'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _miniStat(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(label, style: TextStyle(color: AppTheme.textLabel, fontSize: 11)),
      ],
    );
  }

  Widget _summaryStat(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(color: AppTheme.textPrimary, fontSize: 15, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(label, style: TextStyle(color: AppTheme.textLabel, fontSize: 11)),
      ],
    );
  }

  Widget _outcomeBadge(String outcome) {
    Color bg;
    Color fg;
    String text;
    switch (outcome) {
      case 'completed':
        bg = const Color(0xFF17342F);
        fg = AppTheme.accentLight;
        text = '完成';
        break;
      case 'terminated':
        bg = const Color(0xFF2E1B22);
        fg = AppTheme.textDanger;
        text = '停止';
        break;
      default:
        bg = AppTheme.bgSoft;
        fg = AppTheme.textSecondary;
        text = outcome;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: bg),
      ),
      child: Text(text, style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.bold)),
    );
  }
}
