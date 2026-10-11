import 'dart:math';
import 'package:flutter/material.dart';

import '../theme.dart';

class CircularProgressRing extends StatefulWidget {
  final double progress;
  final String centerText;
  final String caption;
  final RingState state;
  final Size size;

  const CircularProgressRing({
    super.key,
    required this.progress,
    required this.centerText,
    this.caption = '',
    this.state = RingState.ready,
    this.size = const Size(220, 220),
  });

  @override
  State<CircularProgressRing> createState() => _CircularProgressRingState();
}

class _CircularProgressRingState extends State<CircularProgressRing>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _progressAnim;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _progressAnim = Tween<double>(begin: 0, end: widget.progress).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _controller.forward();
  }

  @override
  void didUpdateWidget(CircularProgressRing oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.progress != widget.progress) {
      _progressAnim = Tween<double>(
        begin: oldWidget.progress,
        end: widget.progress,
      ).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOut),
      );
      _controller.reset();
      _controller.forward();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getAccentColor() {
    switch (widget.state) {
      case RingState.ready:
      case RingState.running:
        return AppTheme.accent;
      case RingState.break_:
        return AppTheme.amber;
      case RingState.completed:
        return AppTheme.accentSuccess;
      case RingState.stopped:
        return AppTheme.textDanger;
      case RingState.danger:
        return AppTheme.bgDanger;
    }
  }

  String _getCaption() {
    switch (widget.state) {
      case RingState.ready:
        return '准备开始';
      case RingState.running:
        return '专注中';
      case RingState.break_:
        return '休息时间';
      case RingState.completed:
        return '完成!';
      case RingState.stopped:
        return '已停止';
      case RingState.danger:
        return '检测到干扰';
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = widget.size;
    final trackColor = const Color(0xFF26364F);
    final accentColor = _getAccentColor();
    final strokeWidth = size.width * 0.06;
    final radius = (size.width - strokeWidth * 2) / 2;

    return SizedBox(
      width: size.width,
      height: size.height,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: size,
            painter: _RingPainter(
              progress: _progressAnim.value,
              trackColor: trackColor,
              accentColor: accentColor,
              strokeWidth: strokeWidth,
              state: widget.state,
              radius: radius,
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.centerText,
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: size.width * 0.1,
                  fontWeight: FontWeight.bold,
                  letterSpacing: -0.5,
                  height: 1.1,
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: size.height * 0.08),
              Text(
                widget.caption.isNotEmpty ? widget.caption : _getCaption(),
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: size.width * 0.045,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  final double progress;
  final Color trackColor;
  final Color accentColor;
  final double strokeWidth;
  final RingState state;
  final double radius;

  _RingPainter({
    required this.progress,
    required this.trackColor,
    required this.accentColor,
    required this.strokeWidth,
    required this.state,
    required this.radius,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final paintTrack = Paint()
      ..color = trackColor
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, paintTrack);

    if (progress > 0) {
      final angle = progress * 3.6 * pi / 180.0;
      final paintProgress = Paint()
        ..color = accentColor
        ..strokeWidth = strokeWidth
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -pi / 2,
        -angle,
        false,
        paintProgress,
      );

      // Marker dot at the end of progress arc
      if (progress > 0) {
        final endAngle = -pi / 2 - angle;
        final markerX = center.dx + cos(endAngle) * radius;
        final markerY = center.dy + sin(endAngle) * radius;
        final paintMarker = Paint()
          ..color = AppTheme.textPrimary
          ..style = PaintingStyle.fill;
        canvas.drawCircle(Offset(markerX, markerY), strokeWidth * 0.25, paintMarker);
      }
    }
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) {
    return progress != oldDelegate.progress ||
        accentColor != oldDelegate.accentColor ||
        state != oldDelegate.state;
  }
}

enum RingState { ready, running, break_, completed, stopped, danger }
