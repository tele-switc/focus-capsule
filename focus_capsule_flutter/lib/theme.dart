import 'package:flutter/material.dart';

class AppTheme {
  static const bgPrimary = Color(0xFF0B121D);
  static const bgCard = Color(0xFF111C2B);
  static const bgSoft = Color(0xFF131F30);
  static const bgSurface = Color(0xFF0E1826);
  static const bgDivider = Color(0xFF203047);
  static const bgBorder = Color(0xFF2B3C57);
  static const bgHover = Color(0xFF1D2D45);
  static const bgDanger = Color(0xFF5B343B);

  static const accent = Color(0xFF67CFBB);
  static const accentDark = Color(0xFF35786D);
  static const accentLight = Color(0xFF86DECE);
  static const accentSuccess = Color(0xFF8BD6A8);

  static const amber = Color(0xFFF0C98F);
  static const amberBg = Color(0xFF382C1D);
  static const amberBorder = Color(0xFF5A4529);

  static const textPrimary = Color(0xFFF5F7FA);
  static const textSecondary = Color(0xFF93A1AF);
  static const textLabel = Color(0xFF7F8DA3);
  static const textMuted = Color(0xFF718097);
  static const textPlaceholder = Color(0xFF65748A);
  static const textDanger = Color(0xFFF2A2A2);

  static const borderSubtle = Color(0xFF22334D);
  static const borderCard = Color(0xFF213149);

  static ThemeData get theme => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: bgPrimary,
        colorScheme: ColorScheme.dark(
          primary: accent,
          secondary: accent,
          surface: bgCard,
          onSurface: textPrimary,
          onError: textDanger,
          error: textDanger,
        ),
        appBarTheme: AppBarTheme(
          backgroundColor: bgPrimary,
          elevation: 0,
          centerTitle: true,
          titleTextStyle: TextStyle(
            color: textPrimary,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
          iconTheme: IconThemeData(color: textPrimary),
        ),
        bottomNavigationBarTheme: BottomNavigationBarThemeData(
          backgroundColor: bgSurface,
          selectedItemColor: accent,
          unselectedItemColor: textLabel,
          type: BottomNavigationBarType.fixed,
          elevation: 8,
          selectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
          unselectedLabelStyle: const TextStyle(fontSize: 11),
        ),
        textTheme: TextTheme(
          headlineLarge: TextStyle(
            color: textPrimary,
            fontSize: 72,
            fontWeight: FontWeight.bold,
            letterSpacing: -2,
          ),
          headlineMedium: TextStyle(
            color: textPrimary,
            fontSize: 26,
            fontWeight: FontWeight.bold,
          ),
          headlineSmall: TextStyle(
            color: textPrimary,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
          titleLarge: TextStyle(
            color: textPrimary,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
          titleMedium: TextStyle(
            color: textPrimary,
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
          titleSmall: TextStyle(
            color: accent,
            fontSize: 11,
            fontWeight: FontWeight.bold,
            letterSpacing: 1,
          ),
          bodyLarge: TextStyle(
            color: textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
          bodyMedium: TextStyle(
            color: textSecondary,
            fontSize: 14,
          ),
          bodySmall: TextStyle(
            color: textSecondary,
            fontSize: 12,
          ),
          labelLarge: TextStyle(
            color: textPrimary,
            fontSize: 15,
            fontWeight: FontWeight.w700,
          ),
          labelMedium: TextStyle(
            color: textLabel,
            fontSize: 11,
            fontWeight: FontWeight.bold,
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: bgSurface,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: bgBorder),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: bgBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: accent, width: 2),
          ),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          hintStyle: const TextStyle(color: textPlaceholder, fontSize: 14),
          labelStyle: const TextStyle(color: textSecondary, fontSize: 14),
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            backgroundColor: accent,
            foregroundColor: const Color(0xFF071510),
            elevation: 0,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            foregroundColor: textPrimary,
            backgroundColor: bgSoft,
            side: const BorderSide(color: bgBorder),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
          ),
        ),
        cardTheme: CardTheme(
          color: bgCard,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: borderSubtle),
          ),
          margin: EdgeInsets.zero,
        ),
        dividerTheme: const DividerThemeData(
          color: bgDivider,
          thickness: 1,
        ),
        iconTheme: const IconThemeData(color: textSecondary),
      );
}
