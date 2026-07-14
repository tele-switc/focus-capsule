import 'package:flutter/material.dart';

import '../theme.dart';

class AppChip extends StatelessWidget {
  final String appName;
  final bool isSelected;
  final VoidCallback onTap;
  final IconData icon;

  const AppChip({
    super.key,
    required this.appName,
    required this.isSelected,
    required this.onTap,
    this.icon = Icons.apps,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF17342F) : const Color(0xFF111B2A),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? AppTheme.accent : AppTheme.bgBorder,
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: isSelected ? AppTheme.accent : AppTheme.textSecondary),
            const SizedBox(width: 6),
            Text(
              appName,
              style: TextStyle(
                color: isSelected ? AppTheme.accentLight : AppTheme.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
