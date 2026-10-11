import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models.dart';
import '../services/session_controller.dart';
import '../widgets/circular_progress.dart';
import '../theme.dart';
import '../utils/format.dart';

class TimerScreen extends StatefulWidget {
  const TimerScreen({super.key});

  @override
  State<TimerScreen> createState() => _TimerScreenState();
}

class _TimerScreenState extends State<TimerScreen> with SingleTickerProviderStateMixin {
  final TextEditingController _goalController = TextEditingController();
  String _remainingText = '25:00';
  String _caption = '准备开始';
  RingState _ringState = RingState.ready;
  bool _showOverlayHint = false;
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    final controller = context.read<SessionController>();
    controller.addListener(_onControllerUpdate);
    _goalController.text = controller.config?.goal ?? '';
    
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    );
  }

  @override
  void dispose() {
    final controller = context.read<SessionController>();
    controller.removeListener(_onControllerUpdate);
    _goalController.dispose();
    _animationController.dispose();
    super.dispose();
  }

  void _onControllerUpdate() {
    final controller = context.read<SessionController>();
    setState(() {
      final remaining = controller.total - controller.elapsed;
      if (controller.status == SessionStatus.break_) {
        _remainingText = controller.breakRemaining.secondsFormatted;
        _caption = '临时休息中...';
        _ringState = RingState.break_;
        _showOverlayHint = false;
      } else if (controller.status == SessionStatus.running) {
        _remainingText = remaining.secondsFormatted;
        _caption = '专注中';
        _ringState = RingState.running;
        _showOverlayHint = false;
      } else if (controller.status == SessionStatus.overlay) {
        _remainingText = remaining.secondsFormatted;
        _caption = '检测到干扰';
        _ringState = RingState.danger;
        _showOverlayHint = true;
      } else if (controller.status == SessionStatus.completed) {
        _remainingText = '00:00';
        _caption = '完成!';
        _ringState = RingState.completed;
        _showOverlayHint = false;
      } else if (controller.status == SessionStatus.terminated) {
        _remainingText = '00:00';
        _caption = '已停止';
        _ringState = RingState.stopped;
        _showOverlayHint = false;
      } else {
        _remainingText = '${controller.config?.durationMinutes ?? 25}:00';
        _caption = '准备开始';
        _ringState = RingState.ready;
        _showOverlayHint = false;
      }
    });
  }

  void _startSession() {
    final controller = context.read<SessionController>();
    final config = controller.config ?? FocusConfig();
    final updatedConfig = config.copyWith(
      goal: _goalController.text.trim().isEmpty ? null : _goalController.text.trim(),
    );
    controller.startSession(updatedConfig);
    _animationController.forward();
  }

  void _pauseSession() {
    final controller = context.read<SessionController>();
    controller.handleEscape();
    _animationController.forward();
  }

  void _stopSession() {
    final controller = context.read<SessionController>();
    controller.terminate();
    _animationController.forward();
  }

  bool get _isIdle => context.read<SessionController>().status == SessionStatus.idle;
  bool get _isRunning => context.read<SessionController>().status == SessionStatus.running;
  bool get _isBreak => context.read<SessionController>().status == SessionStatus.break_;
  bool get _isOverlay => context.read<SessionController>().status == SessionStatus.overlay;
  bool get _isDone => context.read<SessionController>().status == SessionStatus.completed ||
                      context.read<SessionController>().status == SessionStatus.terminated;

  @override
  Widget build(BuildContext context) {
    final controller = context.read<SessionController>();
    final config = controller.config ?? FocusConfig();
    final size = MediaQuery.of(context).size;
    final isLarge = size.width > 600;

    return WillPopScope(
      onWillPop: () async {
        // Prevent back during active session
        return !controller.isActive;
      },
      child: Scaffold(
        body: SafeArea(
          child: Stack(
            children: [
              SingleChildScrollView(
                padding: EdgeInsets.symmetric(
                  horizontal: isLarge ? 40 : 16,
                  vertical: 24,
                ),
                child: Column(
                  children: [
                    // Goal input
                    if (_isIdle) ...[
                      TextField(
                        controller: _goalController,
                        style: const TextStyle(color: AppTheme.textPrimary, fontSize: 14),
                        decoration: InputDecoration(
                          hintText: '今天的专注目标是什么？',
                          prefixIcon: Icon(Icons.flag_outlined, size: 18, color: AppTheme.accent),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(color: AppTheme.borderSubtle),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(color: AppTheme.borderSubtle),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(color: AppTheme.accent),
                          ),
                        ),
                        maxLines: 2,
                        textInputAction: TextInputAction.done,
                      ),
                      const SizedBox(height: 24),
                    ],

                    // Circular progress
                    AnimatedOpacity(
                      opacity: _showOverlayHint ? 0.7 : 1.0,
                      duration: const Duration(milliseconds: 300),
                      child: CircularProgressRing(
                        progress: _isIdle
                            ? 0
                            : _isDone
                                ? 100
                                : (controller.elapsed / controller.total * 100).clamp(0, 100),
                        centerText: _remainingText,
                        caption: _caption,
                        state: _ringState,
                        size: Size(
                          size.width.clamp(180, 260),
                          260,
                        ),
                      ),
                    ),

                    const SizedBox(height: 24),

                    // Mode badge
                    if (!_isIdle && !_isDone) ...[
                      _buildModeBadge(config.mode),
                      const SizedBox(height: 16),
                    ],

                    // Overlay hint card
                    if (_isOverlay) ...[
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.amber.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppTheme.amberBorder),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.warning_amber_rounded, color: AppTheme.amber, size: 20),
                                const SizedBox(width: 8),
                                Text(
                                  '检测到应用切换',
                                  style: TextStyle(
                                    color: AppTheme.amber,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '请切回白名单应用继续专注',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: AppTheme.textSecondary,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(height: 12),
                            GestureDetector(
                              onTap: () {
                                controller.onOverlayDismissed(config.whitelist.firstOrNull ?? '');
                              },
                              child: Text(
                                '已切回，点击继续',
                                style: TextStyle(
                                  color: AppTheme.accent,
                                  fontSize: 13,
                                  decoration: TextDecoration.underline,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    // ESC indicator
                    if (_isRunning || _isBreak) ...[
                      Text(
                        _isBreak
                            ? '剩余休息: ${config.escBreakMinutes} 分钟'
                            : '剩余逃脱次数: ${controller.escRemaining}',
                        style: const TextStyle(color: AppTheme.textSecondary, fontSize: 14),
                      ),
                      const SizedBox(height: 8),
                    ],

                    const SizedBox(height: 24),

                    // Controls
                    _buildControls(controller),

                    const SizedBox(height: 24),

                    // Distraction count during session
                    if (!_isIdle && !_isDone && controller.distractionCount > 0) ...[
                      _buildDistractionCard(controller.distractionCount),
                      const SizedBox(height: 16),
                    ],

                    // Completed / Terminated summary
                    if (_isDone) ...[
                      _buildSummaryCard(controller, config),
                    ],

                    // Bottom spacing
                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildControls(SessionController controller) {
    if (_isIdle) {
      return SizedBox(
        width: double.infinity,
        height: 52,
        child: ElevatedButton(
          onPressed: _startSession,
          style: ElevatedButton.styleFrom(
            backgroundColor: AppTheme.accent,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: const Text('开始专注', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600)),
        ),
      );
    }

    if (_isDone) return const SizedBox.shrink();

    return Row(
      children: [
        if (_isRunning && controller.escRemaining > 0) ...[
          Expanded(
            child: SizedBox(
              height: 48,
              child: OutlinedButton(
                onPressed: _pauseSession,
                style: OutlinedButton.styleFrom(
                  backgroundColor: AppTheme.amberBg,
                  side: const BorderSide(color: AppTheme.amberBorder),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: Text(
                  '休息 (${controller.escRemaining})',
                  style: const TextStyle(color: AppTheme.amber, fontSize: 14, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
        ],
        Expanded(
          flex: 2,
          child: SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: _isBreak ? null : _pauseSession,
              style: ElevatedButton.styleFrom(
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: Text(_isBreak ? '休息计时中...' : '暂停', style: const TextStyle(fontSize: 15)),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: SizedBox(
            height: 48,
            child: OutlinedButton(
              onPressed: _stopSession,
              style: OutlinedButton.styleFrom(
                backgroundColor: const Color(0xFF2E1B22),
                side: const BorderSide(color: AppTheme.bgDanger),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('停止', style: TextStyle(color: AppTheme.textDanger, fontSize: 14)),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildModeBadge(String mode) {
    final isDeep = mode == 'Deep';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isDeep ? AppTheme.amberBg : const Color(0xFF17342F),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDeep ? AppTheme.amberBorder : const Color(0xFF275148),
        ),
      ),
      child: Text(
        isDeep ? '深度模式' : '标准模式',
        style: TextStyle(
          color: isDeep ? AppTheme.amber : AppTheme.accentLight,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildDistractionCard(int count) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.amberBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.amberBorder),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: AppTheme.amber, size: 20),
          const SizedBox(width: 10),
          Text(
            '检测到 $count 次干扰',
            style: TextStyle(color: AppTheme.amber, fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryCard(SessionController controller, FocusConfig config) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.bgCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderSubtle),
      ),
      child: Column(
        children: [
          Text(
            controller.status == SessionStatus.completed ? '专注完成!' : '专注已停止',
            style: TextStyle(
              color: controller.status == SessionStatus.completed
                  ? AppTheme.accent
                  : AppTheme.textDanger,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          _buildStatRow('专注时长', formatDuration(controller.elapsed)),
          _buildStatRow('分散注意力', '${controller.distractionCount} 次'),
          _buildStatRow('使用逃脱', '${controller.escUsed} 次'),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: () {
                setState(() {
                  _ringState = RingState.ready;
                  final dur = config.durationMinutes;
                  _remainingText = '$dur:00';
                  _caption = '准备开始';
                });
              },
              child: const Text('重新开始'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatRow(String key, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(key, style: TextStyle(color: AppTheme.textLabel, fontSize: 13)),
          Text(value, style: TextStyle(color: AppTheme.textPrimary, fontSize: 14, fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
