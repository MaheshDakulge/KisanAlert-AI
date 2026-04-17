import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ═══════════════════════════════════════════════════════════════════════════════
// KisanAlert v2.0 — Premium Agricultural Design System
// Inspired by: Maharashtrian soil tones, crop greens, monsoon blues,
//              sunset ambers, and the urgency of a RED mandi board.
// ═══════════════════════════════════════════════════════════════════════════════

class AppColors {
  // ── Light Mode — Warm Earth Palette ──────────────────────────────────────
  static const pageBg       = Color(0xFFFAF8F3);   // Warm parchment white
  static const surface      = Color(0xFFFFFFFF);   // Clean white cards
  static const surfaceRaised = Color(0xFFF3EFE6);  // Warm sand
  static const surfaceSunken = Color(0xFFF5F1EA);  // Soft wheat
  static const surfaceHigh  = Color(0xFFE8E2D6);   // Clay border
  static const textPrimary  = Color(0xFF1A1712);   // Deep earth brown
  static const textSecondary = Color(0xFF4A4438);  // Warm dark
  static const textMuted    = Color(0xFF8A8070);   // Faded soil
  static const textDisabled = Color(0xFFB8AFA0);   // Dried clay

  // ── Dark Mode — Midnight Field ─────────────────────────────────────────
  static const darkPageBg       = Color(0xFF0D0E08);  // Night field
  static const darkSurface      = Color(0xFF161812);  // Deep humus
  static const darkSurfaceRaised = Color(0xFF1E211A); // Dark loam
  static const darkSurfaceSunken = Color(0xFF0A0B06); // Pitch dark
  static const darkSurfaceHigh  = Color(0xFF2A2D24);  // Moonlit soil
  static const darkTextPrimary  = Color(0xFFF5F2EB);  // Warm cream
  static const darkTextSecondary = Color(0xFFCBC4B0); // Soft straw

  // ── PRIMARY GREEN — Crop Vitality ──────────────────────────────────────
  static const green       = Color(0xFF0D7C3E);  // Deep leaf green
  static const greenVivid  = Color(0xFF16A34A);  // Fresh crop green
  static const greenLight  = Color(0xFF4ADE80);  // Spring leaf
  static const greenPale   = Color(0xFFD1FAE5);  // Morning dew
  static const greenText   = Color(0xFF052E16);  // Forest floor
  static const greenGlow   = Color(0xFF10B981);  // Neon harvest

  // ── AMBER — Caution / Harvest Gold ────────────────────────────────────
  static const amber       = Color(0xFFD97706);  // Turmeric gold
  static const amberVivid  = Color(0xFFF59E0B);  // Sunflower
  static const amberPale   = Color(0xFFFEF3C7);  // Pale saffron
  static const amberText   = Color(0xFF451A03);  // Dark spice
  static const amberGlow   = Color(0xFFFBBF24);  // Golden hour

  // ── RED — Danger / Price Crash ────────────────────────────────────────
  static const red         = Color(0xFFDC2626);  // Alert red
  static const redVivid    = Color(0xFFEF4444);  // Emergency
  static const redPale     = Color(0xFFFEE2E2);  // Blush warning
  static const redText     = Color(0xFF7F1D1D);  // Blood earth
  static const redGlow     = Color(0xFFF87171);  // Pulse red

  // ── BLUE — Information / Water / Monsoon ──────────────────────────────
  static const blue        = Color(0xFF1D4ED8);  // Monsoon sky
  static const blueVivid   = Color(0xFF3B82F6);  // Rain cloud
  static const bluePale    = Color(0xFFDBEAFE);  // Morning mist
  static const blueText    = Color(0xFF1E3A8A);  // Deep river

  // ── PURPLE — AI / Intelligence ────────────────────────────────────────
  static const purple      = Color(0xFF7C3AED);  // AI purple
  static const purpleVivid = Color(0xFF8B5CF6);  // Smart glow
  static const purplePale  = Color(0xFFEDE9FE);  // Soft lavender

  // ── TEAL — Fresh / New Feature ────────────────────────────────────────
  static const teal        = Color(0xFF0D9488);  // Fresh mint
  static const tealPale    = Color(0xFFCCFBF1);  // Cool leaf

  // ── ORANGE — Warmth / Community ───────────────────────────────────────
  static const orange      = Color(0xFFEA580C);  // Marigold
  static const orangePale  = Color(0xFFFFF7ED);  // Soft marigold

  // ── Dark Mode Alert Tints ─────────────────────────────────────────────
  static const darkGreenLight  = Color(0xFF4ADE80);
  static const darkAmberLight  = Color(0xFFFBBF24);
  static const darkRedLight    = Color(0xFFF87171);
  static const darkBlueLight   = Color(0xFF60A5FA);
  static const darkPurpleLight = Color(0xFFA78BFA);

  // ── Gradient Presets ──────────────────────────────────────────────────
  static const greenGradient = LinearGradient(
    colors: [Color(0xFF059669), Color(0xFF10B981)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const amberGradient = LinearGradient(
    colors: [Color(0xFFD97706), Color(0xFFF59E0B)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const redGradient = LinearGradient(
    colors: [Color(0xFFDC2626), Color(0xFFEF4444)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const heroGradient = LinearGradient(
    colors: [Color(0xFF064E3B), Color(0xFF059669), Color(0xFF10B981)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const darkHeroGradient = LinearGradient(
    colors: [Color(0xFF022C22), Color(0xFF064E3B), Color(0xFF065F46)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  // ── Signal-to-Gradient helper ──────────────────────────────────────────
  static LinearGradient signalGradient(String level) {
    switch (level) {
      case 'RED':
        return redGradient;
      case 'AMBER':
        return amberGradient;
      case 'GREEN':
        return greenGradient;
      default:
        return greenGradient;
    }
  }
}

class AppTheme {
  static ThemeData light() {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: AppColors.pageBg,
      colorScheme: const ColorScheme.light(
        primary: AppColors.green,
        secondary: AppColors.greenVivid,
        tertiary: AppColors.amber,
        surface: AppColors.surface,
        error: AppColors.red,
      ),
      textTheme: _textTheme(AppColors.textPrimary),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.surface.withValues(alpha: 0.92),
        elevation: 0,
        scrolledUnderElevation: 4,
        shadowColor: Colors.black.withValues(alpha: 0.06),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
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
        tertiary: AppColors.amberVivid,
        surface: AppColors.darkSurface,
        error: AppColors.redVivid,
      ),
      textTheme: _textTheme(AppColors.darkTextPrimary),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.darkSurface.withValues(alpha: 0.92),
        elevation: 0,
        scrolledUnderElevation: 4,
        shadowColor: Colors.black.withValues(alpha: 0.3),
      ),
      cardTheme: CardThemeData(
        color: AppColors.darkSurface,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      useMaterial3: true,
    );
  }

  static TextTheme _textTheme(Color baseColor) {
    return TextTheme(
      // Hero numbers — price displays
      displayLarge: GoogleFonts.spaceGrotesk(
        fontSize: 56, fontWeight: FontWeight.w800, color: baseColor, height: 1.0,
      ),
      // Section titles
      displayMedium: GoogleFonts.spaceGrotesk(
        fontSize: 28, fontWeight: FontWeight.w700, color: baseColor, height: 1.2,
      ),
      // Card titles
      displaySmall: GoogleFonts.spaceGrotesk(
        fontSize: 20, fontWeight: FontWeight.w700, color: baseColor,
      ),
      // Subsection headers
      headlineMedium: GoogleFonts.spaceGrotesk(
        fontSize: 18, fontWeight: FontWeight.w700, color: baseColor,
      ),
      // Body text
      bodyLarge: GoogleFonts.workSans(
        fontSize: 16, fontWeight: FontWeight.w400, color: baseColor, height: 1.5,
      ),
      bodyMedium: GoogleFonts.workSans(
        fontSize: 14, fontWeight: FontWeight.w400, color: baseColor, height: 1.5,
      ),
      // Buttons and labels
      labelLarge: GoogleFonts.workSans(
        fontSize: 16, fontWeight: FontWeight.w600, color: baseColor,
      ),
      // Chips and badges
      labelSmall: GoogleFonts.spaceGrotesk(
        fontSize: 12, fontWeight: FontWeight.w600, color: baseColor, letterSpacing: 0.5,
      ),
    );
  }
}
