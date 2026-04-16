import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  // Light mode
  static const pageBg = Color(0xFFF5F4EF);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceRaised = Color(0xFFEEEEE8);
  static const surfaceSunken = Color(0xFFF0EFEA);
  static const surfaceHigh = Color(0xFFE4E4DC);
  static const textPrimary = Color(0xFF14140E);
  static const textSecondary = Color(0xFF4A4A3E);
  static const textMuted = Color(0xFF7A7A6A);
  static const textDisabled = Color(0xFFAEAE9E);

  // Dark mode
  static const darkPageBg = Color(0xFF0E0F09);
  static const darkSurface = Color(0xFF14140E);
  static const darkSurfaceRaised = Color(0xFF20201A);
  static const darkSurfaceSunken = Color(0xFF0A0A06);
  static const darkSurfaceHigh = Color(0xFF2A2A24);
  static const darkTextPrimary = Color(0xFFF5F4EF);
  static const darkTextSecondary = Color(0xFFC4C4B0);

  // Primary green
  static const green = Color(0xFF15803D);
  static const greenVivid = Color(0xFF22C55E);
  static const greenLight = Color(0xFF4ADE80);
  static const greenPale = Color(0xFFDCFCE7);
  static const greenText = Color(0xFF052E16);

  // Amber
  static const amber = Color(0xFFD97706);
  static const amberVivid = Color(0xFFF59E0B);
  static const amberPale = Color(0xFFFEF3C7);
  static const amberText = Color(0xFF451A03);

  // Red
  static const red = Color(0xFFDC2626);
  static const redVivid = Color(0xFFEF4444);
  static const redPale = Color(0xFFFEE2E2);
  static const redText = Color(0xFF7F1D1D);

  // Blue
  static const blue = Color(0xFF1D4ED8);
  static const bluePale = Color(0xFFDBEAFE);
  static const blueText = Color(0xFF1E3A8A);

  // Purple
  static const purple = Color(0xFF7C3AED);
  static const purplePale = Color(0xFFEDE9FE);

  // Dark mode alert tints
  static const darkGreenLight = Color(0xFF4ADE80);
  static const darkAmberLight = Color(0xFFFBBF24);
  static const darkRedLight = Color(0xFFF87171);
  static const darkBlueLight = Color(0xFF60A5FA);
  static const darkPurpleLight = Color(0xFFA78BFA);
}

class AppTheme {
  static ThemeData light() {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.pageBg,
      colorScheme: const ColorScheme.light(
        primary: AppColors.green,
        secondary: AppColors.greenVivid,
        surface: AppColors.surface,
        error: AppColors.red,
      ),
      textTheme: _textTheme(AppColors.textPrimary),
      useMaterial3: true,
    );
  }

  static ThemeData dark() {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.darkPageBg,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.greenVivid,
        secondary: AppColors.greenLight,
        surface: AppColors.darkSurface,
        error: AppColors.redVivid,
      ),
      textTheme: _textTheme(AppColors.darkTextPrimary),
      useMaterial3: true,
    );
  }

  static TextTheme _textTheme(Color baseColor) {
    return TextTheme(
      displayLarge: GoogleFonts.spaceGrotesk(
        fontSize: 56, fontWeight: FontWeight.w800, color: baseColor,
      ),
      displayMedium: GoogleFonts.spaceGrotesk(
        fontSize: 28, fontWeight: FontWeight.w700, color: baseColor,
      ),
      displaySmall: GoogleFonts.spaceGrotesk(
        fontSize: 20, fontWeight: FontWeight.w700, color: baseColor,
      ),
      headlineMedium: GoogleFonts.spaceGrotesk(
        fontSize: 18, fontWeight: FontWeight.w700, color: baseColor,
      ),
      bodyLarge: GoogleFonts.workSans(
        fontSize: 16, fontWeight: FontWeight.w400, color: baseColor,
      ),
      bodyMedium: GoogleFonts.workSans(
        fontSize: 14, fontWeight: FontWeight.w400, color: baseColor,
      ),
      labelLarge: GoogleFonts.workSans(
        fontSize: 16, fontWeight: FontWeight.w600, color: baseColor,
      ),
      labelSmall: GoogleFonts.spaceGrotesk(
        fontSize: 12, fontWeight: FontWeight.w600, color: baseColor,
        letterSpacing: 0.5,
      ),
    );
  }
}
