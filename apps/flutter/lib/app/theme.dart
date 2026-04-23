import 'package:flutter/material.dart';

/// NyayaAI brand palette — Indian flag.
///
/// These exact hex values appear in the audit-report HTML template
/// (`services/reporter/.../report.html.j2`). Keep them in sync — the
/// demo video cuts between the Flutter web app and the rendered report.
class NyayaColors {
  NyayaColors._();

  static const Color saffron = Color(0xFFFF9933);
  static const Color green = Color(0xFF138808);
  static const Color navy = Color(0xFF000080);

  // Semantic status colors (mirrored in report template).
  static const Color ok = Color(0xFF0A7B2E);
  static const Color warn = Color(0xFFB45309);
  static const Color fail = Color(0xFFB91C1C);

  // Surfaces.
  static const Color bg = Color(0xFFFAFAFA);
  static const Color card = Color(0xFFFFFFFF);
  static const Color border = Color(0xFFE5E5E5);
  static const Color ink = Color(0xFF1A1A1A);
  static const Color muted = Color(0xFF545454); // meets 4.5:1 on #FAFAFA
}

ThemeData buildNyayaTheme() {
  final ColorScheme scheme = ColorScheme.fromSeed(
    seedColor: NyayaColors.navy,
    brightness: Brightness.light,
    primary: NyayaColors.navy,
    secondary: NyayaColors.saffron,
    tertiary: NyayaColors.green,
    error: NyayaColors.fail,
    surface: NyayaColors.card,
  );

  const double minTarget = 48.0;

  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    scaffoldBackgroundColor: NyayaColors.bg,
    visualDensity: VisualDensity.standard,
    fontFamily: 'Roboto',

    // Ensure every interactive surface meets WCAG 2.2 target size.
    materialTapTargetSize: MaterialTapTargetSize.padded,

    textTheme: const TextTheme(
      displaySmall: TextStyle(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        color: NyayaColors.navy,
        letterSpacing: -0.5,
      ),
      headlineMedium: TextStyle(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: NyayaColors.navy,
      ),
      titleLarge: TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: NyayaColors.ink,
      ),
      bodyLarge: TextStyle(fontSize: 16, color: NyayaColors.ink, height: 1.5),
      bodyMedium: TextStyle(fontSize: 14, color: NyayaColors.ink, height: 1.5),
      labelLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: NyayaColors.card,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: NyayaColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: NyayaColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        // 3px focus ring — meets WCAG 2.2 focus-not-obscured minimum.
        borderSide: const BorderSide(color: NyayaColors.navy, width: 3),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: NyayaColors.fail, width: 2),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: NyayaColors.fail, width: 3),
      ),
      labelStyle: const TextStyle(color: NyayaColors.muted, fontSize: 14),
      helperStyle: const TextStyle(color: NyayaColors.muted, fontSize: 12),
      errorStyle: const TextStyle(color: NyayaColors.fail, fontSize: 13),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 16),
    ),

    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: NyayaColors.navy,
        foregroundColor: Colors.white,
        minimumSize: const Size(minTarget, minTarget),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: NyayaColors.navy,
        minimumSize: const Size(minTarget, minTarget),
        side: const BorderSide(color: NyayaColors.navy, width: 1.5),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: NyayaColors.navy,
        minimumSize: const Size(minTarget, minTarget),
      ),
    ),

    cardTheme: CardThemeData(
      color: NyayaColors.card,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: NyayaColors.border),
      ),
    ),

    // High-visibility focus rings for keyboard users on web.
    focusColor: NyayaColors.saffron.withValues(alpha: 0.25),
    highlightColor: NyayaColors.saffron.withValues(alpha: 0.15),

    dividerTheme: const DividerThemeData(color: NyayaColors.border, space: 1),
  );
}
