// kisanalert_app/lib/screens/home_screen.dart
// Farmer-first home: ONE decision, past 7d + next 10d chart, 1 best mandi.

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../data/app_data.dart';
import '../widgets/shared_widgets.dart';

class HomeScreen extends StatelessWidget {
  final AppState state;
  final VoidCallback onOpenVoice;
  final Function(MandiData) onOpenMandi;
  final Function(Signal) onOpenSignal;

  const HomeScreen({
    super.key,
    required this.state,
    required this.onOpenVoice,
    required this.onOpenMandi,
    required this.onOpenSignal,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = state.isDark;
    final crop = state.currentCrop;

    if (crop == null) {
      return const Center(child: CircularProgressIndicator(color: AppColors.green));
    }

    return RefreshIndicator(
      color: AppColors.green,
      onRefresh: () => state.fetchData(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(parent: BouncingScrollPhysics()),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _CropSelector(state: state, isDark: isDark),
            const SizedBox(height: 16),
            if (state.isLoading) 
               const Padding(
                 padding: EdgeInsets.only(bottom: 16),
                 child: LinearProgressIndicator(color: AppColors.green),
               ),
            AnimatedOpacity(
              duration: const Duration(milliseconds: 300),
              opacity: state.isLoading ? 0.4 : 1.0,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _HeroDecisionCard(
                    crop: crop,
                    forecast: state.forecast,
                    isDark: isDark,
                    isMarathi: state.isMarathi,
                  ),
                  const SizedBox(height: 14),
                  _PriceForecastChart(
                    forecast: state.forecast,
                    isDark: isDark,
                    isMarathi: state.isMarathi,
                  ),
                  const SizedBox(height: 14),
                  _BestMandiCard(
                    mandis: state.currentMandis,
                    activeCrop: state.activeCrop,
                    isDark: isDark,
                    isMarathi: state.isMarathi,
                    onTap: onOpenMandi,
                    onSeeAll: () => state.setActiveTab(1),
                  ),
                  const SizedBox(height: 14),
                  _TrustBadge(
                    accuracy: state.accuracyStats,
                    isDark: isDark,
                    isMarathi: state.isMarathi,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────
// CROP SELECTOR
// ─────────────────────────────────────────────────────────────────
class _CropSelector extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _CropSelector({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final crops = [
      ('Soybean', '🌱', 'सोयाबीन'),
      ('Cotton', '🌿', 'कापूस'),
      ('Turmeric', '🌾', 'हळद'),
    ];
    return Row(
      children: crops.map((c) {
        final isActive = state.activeCrop == c.$1;
        return Expanded(
          child: GestureDetector(
            onTap: () => state.setActiveCrop(c.$1),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              margin: const EdgeInsets.symmetric(horizontal: 3),
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: isActive
                    ? AppColors.green
                    : (isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Center(
                child: Text(
                  '${c.$2} ${state.isMarathi ? c.$3 : c.$1}',
                  style: GoogleFonts.workSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: isActive
                        ? Colors.white
                        : (isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
                  ),
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

// ─────────────────────────────────────────────────────────────────
// HERO DECISION CARD — The ONE answer farmer needs
// ─────────────────────────────────────────────────────────────────
class _HeroDecisionCard extends StatelessWidget {
  final CropData crop;
  final ForecastData? forecast;
  final bool isDark;
  final bool isMarathi;

  const _HeroDecisionCard({
    required this.crop,
    required this.forecast,
    required this.isDark,
    required this.isMarathi,
  });

  @override
  Widget build(BuildContext context) {
    final level = crop.alertLevel;
    final color = _levelColor(level);
    final bgColor = _levelBgColor(level, isDark);
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;

    final decision = _getDecision(level, isMarathi);
    final subtitle = _getSubtitle(level, forecast, isMarathi);

    final day10Price = forecast?.day10Predicted ?? crop.price;
    final day10Change = forecast?.day10ChangePct ?? 0.0;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceRaised : AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color, width: 3),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: 0.15),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'AI सल्ला · AI DECISION',
                  style: GoogleFonts.workSans(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: color,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const Spacer(),
              const LiveDot(),
              const SizedBox(width: 4),
              Text(
                'LIVE',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 9,
                  color: AppColors.greenVivid,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            decision,
            style: GoogleFonts.spaceGrotesk(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: GoogleFonts.workSans(
              fontSize: 13,
              color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _PriceBox(
                  label: isMarathi ? 'आजचा भाव' : 'Today',
                  value: '₹${crop.price.toStringAsFixed(0)}',
                  subtext: isMarathi ? 'प्रति क्विंटल' : '/quintal',
                  textColor: textPrimary,
                  isDark: isDark,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _PriceBox(
                  label: isMarathi ? '१० दिवसांत' : '10-day forecast',
                  value: '₹${day10Price.toStringAsFixed(0)}',
                  subtext: day10Change >= 0
                      ? '+${day10Change.toStringAsFixed(1)}% ↑'
                      : '${day10Change.toStringAsFixed(1)}% ↓',
                  textColor: day10Change >= 0 ? AppColors.greenVivid : AppColors.red,
                  isDark: isDark,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _getDecision(String level, bool mr) {
    switch (level) {
      case 'RED':
        return mr ? '🚨 विकू नका!' : '🚨 DO NOT SELL';
      case 'BLUE':
        return mr ? '💎 थांबा' : '💎 HOLD';
      case 'GREEN':
        return mr ? '✅ आजच विका!' : '✅ SELL TODAY';
      default:
        return mr ? '🟡 तुमची निवड' : '🟡 YOUR CHOICE';
    }
  }

  String _getSubtitle(String level, ForecastData? f, bool mr) {
    final days = level == 'BLUE' ? 10 : 7;
    switch (level) {
      case 'RED':
        return mr
            ? '$days दिवसात भाव पडण्याचा अंदाज\nCrash predicted in $days days'
            : 'Price crash predicted in $days days';
      case 'BLUE':
        final gain = f?.day10Predicted ?? 0;
        final curr = f?.currentPrice ?? 0;
        final diff = (gain - curr).toStringAsFixed(0);
        return mr
            ? '$days दिवसात ₹$diff+ वाढणार\nPrice will rise in $days days'
            : 'Price will rise ₹$diff+ in $days days';
      case 'GREEN':
        return mr
            ? '३० दिवसांतील सर्वोच्च भाव आहे\nHighest price in 30 days'
            : 'Highest price in 30 days';
      default:
        return mr
            ? 'भाव स्थिर आहे, गरजेनुसार निर्णय घ्या\nMarket stable, decide as needed'
            : 'Market stable, decide as needed';
    }
  }

  Color _levelColor(String level) {
    switch (level) {
      case 'RED': return AppColors.red;
      case 'BLUE': return AppColors.blue;
      case 'GREEN': return AppColors.green;
      default: return AppColors.amber;
    }
  }

  Color _levelBgColor(String level, bool isDark) {
    switch (level) {
      case 'RED': return AppColors.redPale;
      case 'BLUE': return AppColors.bluePale;
      case 'GREEN': return AppColors.greenPale;
      default: return AppColors.amberPale;
    }
  }
}

class _PriceBox extends StatelessWidget {
  final String label;
  final String value;
  final String subtext;
  final Color textColor;
  final bool isDark;

  const _PriceBox({
    required this.label,
    required this.value,
    required this.subtext,
    required this.textColor,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceSunken : AppColors.surfaceRaised,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.workSans(
              fontSize: 10,
              color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: GoogleFonts.spaceGrotesk(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: textColor,
            ),
          ),
          Text(
            subtext,
            style: GoogleFonts.workSans(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: textColor,
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────
// PRICE FORECAST CHART — Past 7d (solid) + Next 10d (dashed)
// ─────────────────────────────────────────────────────────────────
class _PriceForecastChart extends StatelessWidget {
  final ForecastData? forecast;
  final bool isDark;
  final bool isMarathi;

  const _PriceForecastChart({
    required this.forecast,
    required this.isDark,
    required this.isMarathi,
  });

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    if (forecast == null ||
        forecast!.past7Days.isEmpty ||
        forecast!.next10Days.isEmpty) {
      return Container(
        height: 200,
        decoration: BoxDecoration(
          color: surface,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Center(
          child: Text(
            isMarathi ? 'डेटा लोड होत आहे...' : 'Loading forecast...',
            style: GoogleFonts.workSans(color: textMuted),
          ),
        ),
      );
    }

    final pastSpots = <FlSpot>[];
    final futureSpots = <FlSpot>[];
    double minY = double.infinity;
    double maxY = 0;

    for (int i = 0; i < forecast!.past7Days.length; i++) {
      final p = forecast!.past7Days[i].price;
      pastSpots.add(FlSpot(i.toDouble(), p));
      if (p < minY) minY = p;
      if (p > maxY) maxY = p;
    }

    final startFuture = pastSpots.length - 1;
    futureSpots.add(pastSpots.last);

    for (int i = 0; i < forecast!.next10Days.length; i++) {
      final p = forecast!.next10Days[i].predictedPrice;
      futureSpots.add(FlSpot((startFuture + i + 1).toDouble(), p));
      if (p < minY) minY = p;
      if (p > maxY) maxY = p;
    }

    minY = (minY * 0.95).floorToDouble();
    maxY = (maxY * 1.05).ceilToDouble();

    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 10),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                isMarathi ? '१० दिवसांचा अंदाज' : '10-Day Forecast',
                style: GoogleFonts.spaceGrotesk(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: textPrimary,
                ),
              ),
              Text(
                isMarathi ? '₹/क्विंटल' : '₹/quintal',
                style: GoogleFonts.workSans(fontSize: 11, color: textMuted),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 150,
            child: LineChart(
              LineChartData(
                minY: minY,
                maxY: maxY,
                gridData: const FlGridData(show: false),
                titlesData: const FlTitlesData(show: false),
                borderData: FlBorderData(show: false),
                extraLinesData: ExtraLinesData(
                  verticalLines: [
                    VerticalLine(
                      x: startFuture.toDouble(),
                      color: AppColors.amber,
                      strokeWidth: 1.5,
                      dashArray: [3, 3],
                      label: VerticalLineLabel(
                        show: true,
                        alignment: Alignment.topRight,
                        padding: const EdgeInsets.only(left: 4, bottom: 2),
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 9,
                          color: AppColors.amber,
                          fontWeight: FontWeight.w700,
                        ),
                        labelResolver: (_) => isMarathi ? 'आज' : 'Today',
                      ),
                    ),
                  ],
                ),
                lineBarsData: [
                  // PAST (solid green)
                  LineChartBarData(
                    spots: pastSpots,
                    isCurved: true,
                    color: AppColors.greenVivid,
                    barWidth: 2.5,
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, p1, p2, p3) => FlDotCirclePainter(
                        radius: 3,
                        color: AppColors.greenVivid,
                        strokeWidth: 1.5,
                        strokeColor: surface,
                      ),
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: AppColors.greenVivid.withValues(alpha: 0.1),
                    ),
                  ),
                  // FUTURE (dashed blue)
                  LineChartBarData(
                    spots: futureSpots,
                    isCurved: true,
                    color: AppColors.blue,
                    barWidth: 2.5,
                    dashArray: [4, 3],
                    dotData: FlDotData(
                      show: true,
                      getDotPainter: (spot, p1, p2, p3) => FlDotCirclePainter(
                        radius: 3,
                        color: AppColors.blue,
                        strokeWidth: 1.5,
                        strokeColor: surface,
                      ),
                    ),
                    belowBarData: BarAreaData(
                      show: true,
                      color: AppColors.blue.withValues(alpha: 0.08),
                    ),
                  ),
                ],
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipColor: (_) =>
                        (isDark ? Colors.black : Colors.white).withValues(alpha: 0.9),
                    getTooltipItems: (spots) {
                      return spots.map((s) {
                        final isPast = s.x <= startFuture;
                        return LineTooltipItem(
                          '₹${s.y.toInt()}${isPast ? "" : " (AI)"}',
                          GoogleFonts.jetBrainsMono(
                            fontSize: 11,
                            color: isPast ? AppColors.greenVivid : AppColors.blue,
                            fontWeight: FontWeight.w700,
                          ),
                        );
                      }).toList();
                    },
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              _LegendDot(
                color: AppColors.greenVivid,
                solid: true,
                text: isMarathi ? 'गेले ७ दिवस' : 'Past 7 days',
                isDark: isDark,
              ),
              const SizedBox(width: 14),
              _LegendDot(
                color: AppColors.blue,
                solid: false,
                text: isMarathi ? 'पुढचे १० दिवस (AI)' : 'Next 10 days (AI)',
                isDark: isDark,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final bool solid;
  final String text;
  final bool isDark;
  const _LegendDot({
    required this.color,
    required this.solid,
    required this.text,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 2,
          decoration: BoxDecoration(
            color: solid ? color : null,
            border: !solid ? Border.all(color: color, width: 1) : null,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          text,
          style: GoogleFonts.workSans(
            fontSize: 10,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted,
          ),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────
// BEST MANDI CARD — Just ONE, big and clear
// ─────────────────────────────────────────────────────────────────
class _BestMandiCard extends StatelessWidget {
  final List<MandiData> mandis;
  final String activeCrop;
  final bool isDark;
  final bool isMarathi;
  final Function(MandiData) onTap;
  final VoidCallback onSeeAll;

  const _BestMandiCard({
    required this.mandis,
    required this.activeCrop,
    required this.isDark,
    required this.isMarathi,
    required this.onTap,
    required this.onSeeAll,
  });

  @override
  Widget build(BuildContext context) {
    if (mandis.isEmpty) return const SizedBox.shrink();

    final sorted = [...mandis]
      ..sort((a, b) =>
          b.priceForCrop(activeCrop).compareTo(a.priceForCrop(activeCrop)));
    final best = sorted.first;

    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final nandedPrice =
        activeCrop == 'Cotton' ? 7845.0 : activeCrop == 'Turmeric' ? 12000.0 : 5352.0;
    final netGain = best.priceForCrop(activeCrop) - nandedPrice - (best.distanceKm * 4.5);

    return GestureDetector(
      onTap: () => onTap(best),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.greenVivid.withValues(alpha: 0.3), width: 1),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('🥇', style: TextStyle(fontSize: 24)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isMarathi ? 'आज सर्वोत्तम मंडी' : 'Best mandi today',
                        style: GoogleFonts.workSans(fontSize: 11, color: textMuted),
                      ),
                      Text(
                        best.name,
                        style: GoogleFonts.spaceGrotesk(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '₹${best.priceForCrop(activeCrop).toStringAsFixed(0)}',
                      style: GoogleFonts.spaceGrotesk(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        color: textPrimary,
                      ),
                    ),
                    Text(
                      netGain >= 0
                          ? '+₹${netGain.toStringAsFixed(0)} net'
                          : '-₹${(-netGain).toStringAsFixed(0)} net',
                      style: GoogleFonts.workSans(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: netGain >= 0 ? AppColors.greenVivid : AppColors.red,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${best.distanceKm}km · ${best.weather}',
              style: GoogleFonts.workSans(fontSize: 12, color: textMuted),
            ),
            const SizedBox(height: 10),
            GestureDetector(
              onTap: onSeeAll,
              child: Text(
                isMarathi ? 'सर्व ७ मंडी पहा →' : 'View all 7 mandis →',
                style: GoogleFonts.workSans(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.greenVivid,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────
// TRUST BADGE — Small footer showing accuracy
// ─────────────────────────────────────────────────────────────────
class _TrustBadge extends StatelessWidget {
  final AccuracyStats? accuracy;
  final bool isDark;
  final bool isMarathi;

  const _TrustBadge({
    required this.accuracy,
    required this.isDark,
    required this.isMarathi,
  });

  @override
  Widget build(BuildContext context) {
    if (accuracy == null || accuracy!.total == 0) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            const Text('🌱', style: TextStyle(fontSize: 16)),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                isMarathi
                    ? 'AI शिकत आहे — पहिले काही अंदाज तपासले जात आहेत'
                    : 'AI learning — first predictions being verified',
                style: GoogleFonts.workSans(
                  fontSize: 12,
                  color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted,
                ),
              ),
            ),
          ],
        ),
      );
    }

    final pct = (accuracy!.accuracy * 100).round();
    final stars = '⭐' * ((accuracy!.accuracy * 5).round().clamp(2, 5));

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Text(stars, style: const TextStyle(fontSize: 14)),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              isMarathi
                  ? 'गेल्या ३० दिवसात ${accuracy!.correct}/${accuracy!.total} अंदाज बरोबर · $pct% अचूक'
                  : 'Last 30 days: ${accuracy!.correct}/${accuracy!.total} correct · $pct% accurate',
              style: GoogleFonts.workSans(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
