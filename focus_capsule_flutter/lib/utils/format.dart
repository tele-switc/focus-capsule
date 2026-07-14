extension FormatExt on num {
  String get minutesFormatted {
    final m = toInt();
    if (m >= 60) {
      final h = m ~/ 60;
      final rm = m % 60;
      if (rm == 0) return '${h}小时';
      return '${h}小时${m}分';
    }
    return '${m}分钟';
  }

  String get secondsFormatted {
    final s = toInt().clamp(0, 999999);
    final mins = s ~/ 60;
    final secs = s % 60;
    return '${mins.toString().padLeft(2, '0')}:${secs.toString().padLeft(2, '0')}';
  }

  String get totalHoursFormatted {
    final hrs = this / 3600;
    return '${hrs.toStringAsFixed(1)}小时';
  }
}

String formatDate(DateTime date) {
  final y = date.year;
  final m = date.month.toString().padLeft(2, '0');
  final d = date.day.toString().padLeft(2, '0');
  final h = date.hour.toString().padLeft(2, '0');
  final min = date.minute.toString().padLeft(2, '0');
  return '$y-$m-$d $h:$min';
}

String formatDuration(int seconds) {
  final totalMin = (seconds + 29) ~/ 60;
  if (totalMin < 60) return '${totalMin}分钟';
  final h = totalMin ~/ 60;
  final m = totalMin % 60;
  if (m == 0) return '${h}小时';
  return '${h}小时${m}分';
}
