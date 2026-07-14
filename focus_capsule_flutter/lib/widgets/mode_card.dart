import 'package:flutter/material.dart';

import '../theme.dart';
import '../models.dart';

class ModeCard extends StatelessWidget {
  final IntensityMode mode;
  final bool isSelected;
  final VoidCallback onTap;

  const ModeCard({
    super.key,
    required this.mode,
    required this.isSelected,
    required this.onTap,
  });

  Color _getBorderColor() => isSelected ? AppTheme.accent : AppTheme.bgBorder;
  Color _getBackgroundColor() =>
      isSelected ? const Color(0xFF17342F) : AppTheme.bgSoft;
  Color _getTextColor() => isSelected ? AppTheme.textPrimary : AppTheme.textSecondary;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: _getBackgroundColor(),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _getBorderColor(), width: isSelected ? 2 : 1),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isSelected ? AppTheme.accent : AppTheme.textMuted,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    mode.label,
                    style: TextStyle(
                      color: _getTextColor(),
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              mode.description,
              style: TextStyle(
                color: _getTextColor().withValues(alpha: 0.7),
                fontSize: 11,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
