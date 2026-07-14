import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models.dart';
import '../services/settings_service.dart';
import '../widgets/common.dart';
import '../widgets/mode_card.dart';
import '../theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _durationCtrl;
  late TextEditingController _maxEscCtrl;
  late TextEditingController _escBreakCtrl;
  late TextEditingController _goalCtrl;
  late FocusConfig _config;
  IntensityMode _selectedMode = IntensityMode.standard;
  bool _saving = false;

  static const _commonApps = [
    ('VS Code', 'code.exe'),
    ('Chrome', 'chrome.exe'),
    ('Edge', 'msedge.exe'),
    ('Firefox', 'firefox.exe'),
    ('Word', 'winword.exe'),
    ('Excel', 'excel.exe'),
    ('终端', 'windowsterminal.exe'),
    ('记事本', 'notepad.exe'),
    ('PyCharm', 'pycharm64.exe'),
    ('IntelliJ', 'idea64.exe'),
  ];

  Set<String> _whitelist = {};

  @override
  void initState() {
    super.initState();
    _config = context.read<SettingsService>().loadConfig();
    _durationCtrl = TextEditingController(text: _config.durationMinutes.toString());
    _maxEscCtrl = TextEditingController(text: _config.maxEsc.toString());
    _escBreakCtrl = TextEditingController(text: _config.escBreakMinutes.toString());
    _goalCtrl = TextEditingController(text: _config.goal ?? '');
    _selectedMode = IntensityMode.fromString(_config.mode);
    _whitelist = Set.from(_config.whitelist);
  }

  @override
  void dispose() {
    _durationCtrl.dispose();
    _maxEscCtrl.dispose();
    _escBreakCtrl.dispose();
    _goalCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final dur = int.tryParse(_durationCtrl.text) ?? 25;
    final maxEsc = int.tryParse(_maxEscCtrl.text) ?? 2;
    final escBreak = int.tryParse(_escBreakCtrl.text) ?? 3;
    final config = _config.copyWith(
      durationMinutes: dur.clamp(1, 120),
      maxEsc: maxEsc.clamp(0, 10),
      escBreakMinutes: escBreak.clamp(1, 15),
      mode: _selectedMode.label,
      goal: _goalCtrl.text.trim().isEmpty ? null : _goalCtrl.text.trim(),
      whitelist: _whitelist.toList(),
    );
    final service = context.read<SettingsService>();
    await service.saveConfig(config);
    if (mounted) {
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('设置已保存'),
          backgroundColor: AppTheme.accent,
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeader(title: '专注设置'),

              // Duration
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('专注时长', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _durationCtrl,
                            keyboardType: TextInputType.number,
                            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
                            decoration: const InputDecoration(
                              hintText: '5-120 分钟',
                              prefixIcon: Icon(Icons.timer_outlined, size: 18, color: AppTheme.accent),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Text(
                          '${_durationCtrl.text} 分钟',
                          style: const TextStyle(color: AppTheme.accent, fontSize: 14, fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Intensity mode
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('强度模式', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    Column(
                      children: IntensityMode.values.map((mode) {
                        final selected = _selectedMode == mode;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: ModeCard(
                            mode: mode,
                            isSelected: selected,
                            onTap: () => setState(() => _selectedMode = mode),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Escape settings
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('逃脱设置', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _maxEscCtrl,
                            keyboardType: TextInputType.number,
                            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
                            decoration: const InputDecoration(
                              labelText: '最大逃脱次数',
                              hintText: '0-10',
                              prefixIcon: Icon(Icons.swap_horiz, size: 18, color: AppTheme.accent),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _escBreakCtrl,
                            keyboardType: TextInputType.number,
                            style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
                            decoration: const InputDecoration(
                              labelText: '休息时长(分)',
                              hintText: '1-15',
                              prefixIcon: Icon(Icons.coffee, size: 18, color: AppTheme.accent),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Goal
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('专注目标', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _goalCtrl,
                      style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
                      decoration: const InputDecoration(
                        hintText: '今天为什么要专注?',
                        prefixIcon: Icon(Icons.flag_outlined, size: 18, color: AppTheme.accent),
                      ),
                      maxLines: 2,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Whitelist
              SectionCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('允许的应用', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      '专注期间允许使用的应用不会被计为干扰',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _commonApps.map((tuple) {
                        final name = tuple.$1;
                        final process = tuple.$2;
                        final selected = _whitelist.contains(process);
                        return FilterChip(
                          label: Text(name),
                          selected: selected,
                          onSelected: (v) {
                            setState(() {
                              if (v) {
                                _whitelist.add(process);
                              } else {
                                _whitelist.remove(process);
                              }
                            });
                          },
                          selectedColor: AppTheme.accent.withValues(alpha: 0.2),
                          checkmarkColor: AppTheme.accent,
                          side: BorderSide(color: selected ? AppTheme.accent : AppTheme.bgBorder),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // Save button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? const SizedBox(
                          height: 24,
                          width: 24,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('保存设置', style: TextStyle(fontSize: 17)),
                ),
              ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
