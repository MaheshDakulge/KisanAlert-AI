import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';

// ─────────────────────────────────────────────────────────────────────
// Signal level color helper
// ─────────────────────────────────────────────────────────────────────
Color signalColor(String level, bool isDark) {
  switch (level) {
    case 'RED': return isDark ? AppColors.darkRedLight : AppColors.red;
    case 'AMBER': return isDark ? AppColors.darkAmberLight : AppColors.amber;
    case 'GREEN': return isDark ? AppColors.darkGreenLight : AppColors.green;
    case 'BLUE': return isDark ? AppColors.darkBlueLight : AppColors.blue;
    case 'BEST': return isDark ? AppColors.darkGreenLight : AppColors.green;
    default: return isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
  }
}

Color signalBgColor(String level, bool isDark) {
  switch (level) {
    case 'RED': return isDark ? AppColors.red.withValues(alpha: 0.15) : AppColors.redPale;
    case 'AMBER': return isDark ? AppColors.amber.withValues(alpha: 0.15) : AppColors.amberPale;
    case 'GREEN': return isDark ? AppColors.green.withValues(alpha: 0.15) : AppColors.greenPale;
    case 'BLUE': return isDark ? AppColors.blue.withValues(alpha: 0.15) : AppColors.bluePale;
    case 'BEST': return isDark ? AppColors.green.withValues(alpha: 0.2) : AppColors.greenPale;
    default: return isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Crash Score SVG Gauge
// ─────────────────────────────────────────────────────────────────────
class CrashScoreGauge extends StatefulWidget {
  final double score;
  final bool isDark;
  const CrashScoreGauge({super.key, required this.score, required this.isDark});

  @override
  State<CrashScoreGauge> createState() => _CrashScoreGaugeState();
}

class _CrashScoreGaugeState extends State<CrashScoreGauge>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200));
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.elasticOut);
    _ctrl.forward();
  }

  @override
  void didUpdateWidget(CrashScoreGauge old) {
    super.didUpdateWidget(old);
    if (old.score != widget.score) {
      _ctrl.reset();
      _ctrl.forward();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, _) {
        final displayScore = widget.score * _anim.value;
        final level = widget.score >= 0.65 ? 'RED' : widget.score >= 0.35 ? 'AMBER' : 'GREEN';
        return CustomPaint(
          size: const Size(240, 140),
          painter: _GaugePainter(displayScore, widget.isDark),
          child: SizedBox(
            width: 240,
            height: 140,
            child: Align(
              alignment: const Alignment(0, 0.5),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    displayScore.toStringAsFixed(2),
                    style: GoogleFonts.spaceGrotesk(
                      fontSize: 40,
                      fontWeight: FontWeight.w800,
                      color: signalColor(level, widget.isDark),
                    ),
                  ),
                  Text(
                    'crash_score',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      color: widget.isDark ? AppColors.darkTextSecondary : AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double score;
  final bool isDark;
  _GaugePainter(this.score, this.isDark);

  static const double _startAngle = math.pi * 0.75;
  static const double _sweepAngle = math.pi * 1.5;

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height * 0.72;
    final r = size.width * 0.44;

    // Track
    final trackPaint = Paint()
      ..color = (isDark ? Colors.white : Colors.black).withValues(alpha: 0.08)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(Rect.fromCircle(center: Offset(cx, cy), radius: r), _startAngle, _sweepAngle, false, trackPaint);

    // Zone arcs (faint background tint)
    final zones = [(0.0, 0.35, AppColors.green), (0.35, 0.65, AppColors.amber), (0.65, 1.0, AppColors.red)];
    for (final z in zones) {
      final p = Paint()
        ..color = z.$3.withValues(alpha: 0.2)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 14
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCircle(center: Offset(cx, cy), radius: r),
        _startAngle + _sweepAngle * z.$1,
        _sweepAngle * (z.$2 - z.$1),
        false, p,
      );
    }

    // Active fill
    if (score > 0) {
      final color = score >= 0.65 ? AppColors.red : score >= 0.35 ? AppColors.amber : AppColors.green;
      final fillPaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 14
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCircle(center: Offset(cx, cy), radius: r),
        _startAngle, _sweepAngle * score.clamp(0.0, 1.0), false, fillPaint,
      );

      // Needle dot
      final needleAngle = _startAngle + _sweepAngle * score.clamp(0.0, 1.0);
      final nx = cx + r * math.cos(needleAngle);
      final ny = cy + r * math.sin(needleAngle);
      canvas.drawCircle(Offset(nx, ny), 7, Paint()..color = Colors.white);
      canvas.drawCircle(Offset(nx, ny), 5, Paint()..color = color);
    }
  }

  @override
  bool shouldRepaint(_GaugePainter old) => old.score != score;
}

// ─────────────────────────────────────────────────────────────────────
// Alert Badge
// ─────────────────────────────────────────────────────────────────────
class AlertBadge extends StatefulWidget {
  final String level;
  final String label;
  final bool isDark;
  const AlertBadge({super.key, required this.level, required this.label, required this.isDark});

  @override
  State<AlertBadge> createState() => _AlertBadgeState();
}

class _AlertBadgeState extends State<AlertBadge> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);
    _anim = Tween(begin: 1.0, end: 1.05).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final bg = signalBgColor(widget.level, widget.isDark);
    final fg = signalColor(widget.level, widget.isDark);

    Widget badge = Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(12)),
      child: Text(widget.label, textAlign: TextAlign.center,
        style: GoogleFonts.spaceGrotesk(fontSize: 17, fontWeight: FontWeight.w700, color: fg)),
    );

    if (widget.level == 'RED') {
      return AnimatedBuilder(
        animation: _anim,
        builder: (_, child) => Transform.scale(scale: _anim.value, child: child),
        child: badge,
      );
    }
    return badge;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Marathi AI Box
// ─────────────────────────────────────────────────────────────────────
class MarathiAIBox extends StatelessWidget {
  final String marathiText;
  final String englishText;
  final bool isDark;
  const MarathiAIBox({super.key, required this.marathiText, required this.englishText, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final surfaceColor = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    return Container(
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(16),
        border: const Border(left: BorderSide(color: AppColors.amber, width: 4)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('✦ Gemini AI · Marathi',
                style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.purple)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: AppColors.purplePale, borderRadius: BorderRadius.circular(999)),
                child: Text('AI', style: GoogleFonts.spaceGrotesk(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.purple)),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(marathiText,
            style: GoogleFonts.workSans(fontSize: 17, fontWeight: FontWeight.w500, height: 1.6,
              color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
          const SizedBox(height: 8),
          Text(englishText,
            style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w400, height: 1.5,
              color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Signal Chip
// ─────────────────────────────────────────────────────────────────────
class SignalChip extends StatelessWidget {
  final String label;
  final String level;
  final bool isDark;
  final VoidCallback? onTap;
  const SignalChip({super.key, required this.label, required this.level, required this.isDark, this.onTap});

  @override
  Widget build(BuildContext context) {
    final bg = signalBgColor(level, isDark);
    final fg = signalColor(level, isDark);
    final dot = level == 'RED' ? '🔴' : level == 'BLUE' ? '🔵' : level == 'AMBER' ? '🟡' : '🟢';
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(8)),
        child: Text('$dot $label', style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: fg)),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Agronomist Insight Card
// ─────────────────────────────────────────────────────────────────────
class AgronomistCard extends StatelessWidget {
  final Widget child;
  final bool isDark;
  const AgronomistCard({super.key, required this.child, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: (isDark ? AppColors.darkSurfaceRaised : AppColors.surface).withValues(alpha: 0.90),
        borderRadius: BorderRadius.circular(16),
        border: const Border(top: BorderSide(color: AppColors.amber, width: 4)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.06), blurRadius: 20, offset: const Offset(0, 8))],
      ),
      padding: const EdgeInsets.all(20),
      child: child,
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Mandi Card
// ─────────────────────────────────────────────────────────────────────
class MandiCard extends StatelessWidget {
  final String rank;
  final String name;
  final int distanceKm;
  final double price;
  final String signal;
  final String weather;
  final String advice;
  final bool isBest;
  final bool isDark;
  final String activeCrop;
  final VoidCallback? onTap;

  const MandiCard({
    super.key, required this.rank, required this.name, required this.distanceKm,
    required this.price, required this.signal, required this.weather, required this.advice,
    required this.isDark, required this.activeCrop, this.isBest = false, this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final nandedPrice = activeCrop == 'Cotton' ? 7845.0 : activeCrop == 'Turmeric' ? 12000.0 : 5352.0;
    final netGain = price - nandedPrice - (distanceKm * 4.5);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: surface, borderRadius: BorderRadius.circular(16),
          border: isBest ? Border.all(color: AppColors.greenVivid, width: 2) : null,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(rank, style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(name, style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
                    if (isBest) ...[
                      const SizedBox(width: 6),
                      Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(color: AppColors.greenPale, borderRadius: BorderRadius.circular(999)),
                        child: Text('BEST ⭐', style: GoogleFonts.spaceGrotesk(fontSize: 9, fontWeight: FontWeight.w700, color: AppColors.greenText))),
                    ],
                    const Spacer(),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: signalBgColor(signal, isDark), borderRadius: BorderRadius.circular(999)),
                      child: Text(signal, style: GoogleFonts.spaceGrotesk(fontSize: 11, fontWeight: FontWeight.w700, color: signalColor(signal, isDark)))),
                  ]),
                  const SizedBox(height: 6),
                  Row(children: [
                    Text('₹${price.toStringAsFixed(0)}',
                      style: GoogleFonts.spaceGrotesk(fontSize: 22, fontWeight: FontWeight.w700, color: textPrimary)),
                    Text('/qtl', style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
                    const Spacer(),
                    Text(netGain >= 0 ? '+₹${netGain.toStringAsFixed(0)} net' : '-₹${(-netGain).toStringAsFixed(0)} net',
                      style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600,
                        color: netGain >= 0 ? AppColors.green : AppColors.red)),
                  ]),
                  const SizedBox(height: 4),
                  Text('$distanceKm km · $weather', style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
                  const SizedBox(height: 2),
                  Text(advice, style: GoogleFonts.workSans(fontSize: 12, color: textMuted, fontStyle: FontStyle.italic)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Forecast Day Card
// ─────────────────────────────────────────────────────────────────────
class ForecastDayCard extends StatelessWidget {
  final String dayEn, dayMr, direction, risk;
  final double price;
  final bool isDark, isMarathi;

  const ForecastDayCard({super.key, required this.dayEn, required this.dayMr,
    required this.price, required this.direction, required this.risk, required this.isDark, required this.isMarathi});

  @override
  Widget build(BuildContext context) {
    final isBest = risk == 'BEST';
    final bg = isBest ? (isDark ? AppColors.green.withValues(alpha: 0.2) : AppColors.greenPale) : signalBgColor(risk, isDark);
    final arrow = direction == 'up' ? '↑' : direction == 'down' ? '↓' : '→';
    final arrowColor = direction == 'up' ? AppColors.green : direction == 'down' ? AppColors.red : AppColors.amber;

    return Container(
      width: 78,
      margin: const EdgeInsets.only(right: 8),
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: bg, borderRadius: BorderRadius.circular(12),
        border: isBest ? Border.all(color: AppColors.greenVivid, width: 2) : null,
      ),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(isMarathi ? dayMr : dayEn, style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w600,
          color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
        const SizedBox(height: 6),
        Text(arrow, style: TextStyle(fontSize: 16, color: arrowColor, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text('₹${(price / 1000).toStringAsFixed(1)}k',
          style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700,
            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
        const SizedBox(height: 6),
        if (isBest)
          Text('⭐ SELL', style: GoogleFonts.spaceGrotesk(fontSize: 9, fontWeight: FontWeight.w800, color: AppColors.green))
        else Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          decoration: BoxDecoration(color: signalColor(risk, isDark).withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
          child: Text(risk, style: GoogleFonts.spaceGrotesk(fontSize: 8, fontWeight: FontWeight.w700, color: signalColor(risk, isDark))),
        ),
      ]),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Community Story Card
// ─────────────────────────────────────────────────────────────────────
class ChopalCard extends StatelessWidget {
  final String initials, avatarColor, nameEn, distanceKm, messageMr, messageEn, verifiedDate, crop, saved;
  final bool isVerified, isDark, isMarathi;

  const ChopalCard({super.key, required this.initials, required this.avatarColor,
    required this.nameEn, required this.distanceKm, required this.messageMr, required this.messageEn,
    required this.isVerified, required this.verifiedDate, required this.crop, required this.saved,
    required this.isDark, required this.isMarathi});

  Color _avatarBg() {
    if (avatarColor == 'green') return AppColors.green;
    if (avatarColor == 'amber') return AppColors.amber;
    return AppColors.blue;
  }

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(16)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        CircleAvatar(radius: 22, backgroundColor: _avatarBg(),
          child: Text(initials, style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white))),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(nameEn, style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: textPrimary)),
          Text('$distanceKm दूर · $crop', style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
          const SizedBox(height: 8),
          Text(isMarathi ? messageMr : messageEn,
            style: GoogleFonts.workSans(fontSize: 16, fontWeight: FontWeight.w500, height: 1.5, color: textPrimary)),
          const SizedBox(height: 8),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(color: isVerified ? AppColors.greenPale : AppColors.amberPale, borderRadius: BorderRadius.circular(6)),
            child: Text(isVerified ? '✓ Verified — $verifiedDate' : '⏳ $verifiedDate',
              style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w600,
                color: isVerified ? AppColors.greenText : AppColors.amberText))),
          const SizedBox(height: 4),
          Text('Saved: $saved', style: GoogleFonts.workSans(fontSize: 11, color: AppColors.green, fontWeight: FontWeight.w600)),
        ])),
      ]),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Live dot
// ─────────────────────────────────────────────────────────────────────
class LiveDot extends StatefulWidget {
  const LiveDot({super.key});
  @override
  State<LiveDot> createState() => _LiveDotState();
}

class _LiveDotState extends State<LiveDot> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500))..repeat(reverse: true);
    _anim = Tween(begin: 1.0, end: 0.3).animate(_ctrl);
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, _) => Opacity(opacity: _anim.value,
        child: Container(width: 8, height: 8,
          decoration: const BoxDecoration(color: AppColors.greenVivid, shape: BoxShape.circle))),
    );
  }
}
