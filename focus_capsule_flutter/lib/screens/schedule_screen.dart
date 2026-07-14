import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../services/settings_service.dart';
import '../widgets/common.dart';
import '../theme.dart';

class ScheduleScreen extends StatefulWidget {
  const ScheduleScreen({super.key});

  @override
  State<ScheduleScreen> createState() => _ScheduleScreenState();
}

class _ScheduleScreenState extends State<ScheduleScreen> {
  List<ScheduleRule> _rules = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadRules();
  }

  Future<void> _loadRules() async {
    setState(() => _loading = true);
    try {
      final service = context.read<SettingsService>();
      setState(() {
        _rules = service.loadScheduleRules();
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _saveRules() async {
    final service = context.read<SettingsService>();
    await service.saveScheduleRules(_rules);
  }

  void _addRule() {
    final rule = ScheduleRule(
      startHour: 9,
      startMinute: 0,
      endHour: 10,
      endMinute: 0,
      mode: 'Deep',
      enabled: false,
    );
    setState(() => _rules.add(rule));
    _saveRules();
  }

  void _deleteRule(int index) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.bgCard,
        title: const Text('删除此规则?'),
        content: const Text('确认删除这个日程锁定规则?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          TextButton(
            onPressed: () {
              setState(() => _rules.removeAt(index));
              Navigator.pop(ctx);
              _saveRules();
            },
            child: const Text('删除', style: TextStyle(color: AppTheme.textDanger)),
          ),
        ],
      ),
    );
  }

  void _editRule(int index) {
    final rule = _rules[index];
    final formKey = GlobalKey<FormState>();
    final startH = TextEditingController(text: rule.startHour.toString());
    final startM = TextEditingController(text: rule.startMinute.toString());
    final endH = TextEditingController(text: rule.endHour.toString());
    final endM = TextEditingController(text: rule.endMinute.toString());
    var labelCtrl = TextEditingController(text: rule.label);
    var enabled = rule.enabled;
    var mode = rule.mode;
    var appsCtrl = TextEditingController(text: rule.whitelistedApps.join(', '));

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AppTheme.bgCard,
          title: const Text('编辑日程规则'),
          content: SingleChildScrollView(
            child: Form(
              key: formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: startH,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: '时', hintText: '开始小时'),
                          validator: (v) => v == null || v.isEmpty ? '必填' : null,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextFormField(
                          controller: startM,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: '分', hintText: '开始分钟'),
                          validator: (v) => v == null || v.isEmpty ? '必填' : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextFormField(
                          controller: endH,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: '时', hintText: '结束小时'),
                          validator: (v) => v == null || v.isEmpty ? '必填' : null,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextFormField(
                          controller: endM,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: '分', hintText: '结束分钟'),
                          validator: (v) => v == null || v.isEmpty ? '必填' : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: labelCtrl,
                    decoration: const InputDecoration(labelText: '规则名称', hintText: '例如: 工作时间'),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: mode,
                    decoration: const InputDecoration(labelText: '强度模式'),
                    items: ['Light', 'Standard', 'Deep']
                        .map((m) => DropdownMenuItem(value: m, child: Text(m)))
                        .toList(),
                    onChanged: (v) => setDialogState(() => mode = v!),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: appsCtrl,
                    decoration: const InputDecoration(
                      labelText: '允许的应用 (逗号分隔)',
                      hintText: 'chrome, vscode',
                    ),
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    title: const Text('启用此规则'),
                    value: enabled,
                    onChanged: (v) => setDialogState(() => enabled = v),
                    activeColor: AppTheme.accent,
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
            ElevatedButton(
              onPressed: () {
                if (formKey.currentState!.validate()) {
                  final apps = appsCtrl.text
                      .split(',')
                      .map((s) => s.trim())
                      .where((s) => s.isNotEmpty)
                      .toList();
                  setState(() {
                    _rules[index] = rule.copyWith(
                      startHour: int.tryParse(startH.text) ?? 0,
                      startMinute: int.tryParse(startM.text) ?? 0,
                      endHour: int.tryParse(endH.text) ?? 0,
                      endMinute: int.tryParse(endM.text) ?? 0,
                      label: labelCtrl.text.trim(),
                      mode: mode,
                      enabled: enabled,
                      whitelistedApps: apps,
                    );
                  });
                  _saveRules();
                  Navigator.pop(ctx);
                }
              },
              child: const Text('保存'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: SectionHeader(
                title: '日程锁定',
                subtitle: '按中国时间定时锁定，到点自动切换允许的应用',
              ),
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _rules.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.calendar_today, size: 64, color: AppTheme.textMuted.withValues(alpha: 0.4)),
                              const SizedBox(height: 16),
                              Text(
                                '还没有日程规则',
                                style: TextStyle(color: AppTheme.textSecondary, fontSize: 16),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                '点击下方按钮添加一个时段，例如 9~10 点只能用 VS Code',
                                style: TextStyle(color: AppTheme.textMuted, fontSize: 13),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                          itemBuilder: (context, index) => _buildRuleCard(index),
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemCount: _rules.length,
                        ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addRule,
        backgroundColor: AppTheme.accent,
        foregroundColor: const Color(0xFF071510),
        icon: const Icon(Icons.add),
        label: const Text('添加时段规则'),
      ),
    );
  }

  Widget _buildRuleCard(int index) {
    final rule = _rules[index];
    final timeStr =
        '${rule.startHour.toString().padLeft(2, '0')}:${rule.startMinute.toString().padLeft(2, '0')} → ${rule.endHour.toString().padLeft(2, '0')}:${rule.endMinute.toString().padLeft(2, '0')}';
    final appsText = rule.whitelistedApps.isEmpty
        ? '未设置（全部锁定）'
        : rule.whitelistedApps.join(', ');

    return SectionCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Switch(
                value: rule.enabled,
                onChanged: (v) {
                  setState(() => _rules[index] = rule.copyWith(enabled: v));
                  _saveRules();
                },
                activeColor: AppTheme.accent,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      rule.label.isNotEmpty ? rule.label : timeStr,
                      style: const TextStyle(color: AppTheme.textPrimary, fontSize: 15, fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '允许: $appsText',
                      style: const TextStyle(color: AppTheme.accent, fontSize: 11),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: rule.enabled ? const Color(0xFF17342F) : AppTheme.bgSoft,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  rule.enabled ? '已启用' : '待命',
                  style: TextStyle(
                    color: rule.enabled ? AppTheme.accent : AppTheme.textMuted,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton.icon(
                onPressed: () => _editRule(index),
                icon: const Icon(Icons.edit_outlined, size: 16),
                label: const Text('编辑'),
                style: TextButton.styleFrom(foregroundColor: AppTheme.accent),
              ),
              const SizedBox(width: 8),
              TextButton.icon(
                onPressed: () => _deleteRule(index),
                icon: const Icon(Icons.delete_outline, size: 16),
                label: const Text('删除'),
                style: TextButton.styleFrom(foregroundColor: AppTheme.textDanger),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
