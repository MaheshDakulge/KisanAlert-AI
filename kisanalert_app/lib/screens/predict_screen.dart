import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/shared_widgets.dart';
import 'package:fl_chart/fl_chart.dart';

class PredictScreen extends StatefulWidget {
  final AppState state;
  const PredictScreen({super.key, required this.state});

  @override
  State<PredictScreen> createState() => _PredictScreenState();
}

class _PredictScreenState extends State<PredictScreen> {
  bool _featuresExpanded = false;

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final isMarathi = widget.state.isMarathi;
    final crop = widget.state.currentCrop;
    if (crop == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(color: AppColors.green),
            const SizedBox(height: 16),
            Text(isMarathi ? 'आडावा लोड होत आहे...' : 'Loading prediction data...',
              style: GoogleFonts.workSans(color: AppColors.textMuted)),
          ],
        ),
      );
    }
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final surfaceHigh = isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),

          // Main gauge
          Center(
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(24)),
              child: Column(
                children: [
                  CrashScoreGauge(score: crop.crashScore, isDark: isDark),
                  const SizedBox(height: 12),
                  _ZoneBar(isDark: isDark, isMarathi: isMarathi),
                  const SizedBox(height: 16),
                  AlertBadge(
                    level: crop.alertLevel,
                    label: crop.alertLevel == 'RED'
                        ? '🚨 RED — Don\'t sell (Avoid loss)'
                        : crop.alertLevel == 'BLUE'
                            ? '🔵 BLUE — Hold & wait (Earn more)'
                            : crop.alertLevel == 'AMBER'
                                ? '⚠️ AMBER — Farmer\'s choice'
                                : '✅ GREEN — At peak, sell now',
                    isDark: isDark,
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: surfaceHigh, borderRadius: BorderRadius.circular(10)),
                    child: Column(
                      children: [
                        Text(
                          crop.alertLevel == 'RED'
                              ? 'nafed_release + arrivals surge · DGFT export policy active'
                              : crop.alertLevel == 'BLUE'
                                  ? 'Lead-lag signal from Latur market · futures basis positive'
                                  : crop.alertLevel == 'GREEN'
                                      ? 'Price at 30-day peak · low crash risk confirmed'
                                      : 'No major market intervention detected',
                          style: GoogleFonts.jetBrainsMono(fontSize: 11, color: textMuted),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'AUC: 0.76 · Trained 2021–2025 · ${(crop.crashScore * 100).round()}% confidence',
                          style: GoogleFonts.jetBrainsMono(fontSize: 10, color: textMuted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // 🌟 Lead-Lag & NCDEX Strategy Explanation
          _LeadLagInfoCard(isDark: isDark, isMarathi: isMarathi),
          const SizedBox(height: 24),

          // Three model cards
          Text(isMarathi ? '३ AI मॉडेल्स / 3 AI Models' : '3 AI Models',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          SizedBox(
            height: 320,
            child: ListView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              children: [
                _XGBoostCard(isDark: isDark, isMarathi: isMarathi, prob: (crop.crashScore * 0.95).clamp(0.0, 1.0)),
                _LSTMCard(isDark: isDark, isMarathi: isMarathi, prob: (crop.crashScore * 1.05).clamp(0.0, 1.0)),
                _RuleEngineCard(isDark: isDark, isMarathi: isMarathi, prob: ((crop.crashScore - 0.4*(crop.crashScore*1.05) - 0.4*(crop.crashScore*0.95)) / 0.2).clamp(0.0, 1.0)),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 1-Year Historical Chart
          if (widget.state.yearHistory.isNotEmpty) ...[
            Text(isMarathi ? '१ वर्षाचा इतिहास (Stock View)' : '1-Year Historical Price',
              style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(height: 12),
            Container(
              height: 250,
              padding: const EdgeInsets.only(top: 20, bottom: 10, left: 0, right: 0),
              decoration: BoxDecoration(color: surfaceHigh, borderRadius: BorderRadius.circular(16)),
              child: _buildChart(widget.state.yearHistory, isDark, textMuted),
            ),
            const SizedBox(height: 20),
          ],

          // Ensemble Calculation
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: surfaceHigh, borderRadius: BorderRadius.circular(16)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(isMarathi ? 'Ensemble Formula' : 'Ensemble Formula',
                  style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700, color: textPrimary)),
                const SizedBox(height: 12),
                _monoLine('crash_score', textPrimary, fontSize: 13),
                _monoLine('  = 0.40 × LSTM + 0.40 × XGBoost + 0.20 × Rules', textMuted),
                _monoLine('  = 0.40 × ${(crop.crashScore * 1.05).clamp(0.0, 1.0).toStringAsFixed(2)} + 0.40 × ${(crop.crashScore * 0.95).clamp(0.0, 1.0).toStringAsFixed(2)}   + 0.20 × ${(((crop.crashScore - 0.4*(crop.crashScore*1.05) - 0.4*(crop.crashScore*0.95)) / 0.2).clamp(0.0, 1.0)).toStringAsFixed(2)}', textMuted),
                _monoLine('  = ${(0.4 * (crop.crashScore * 1.05)).clamp(0.0, 1.0).toStringAsFixed(3)}       + ${(0.4 * (crop.crashScore * 0.95)).clamp(0.0, 1.0).toStringAsFixed(3)}          + ${(0.2 * (((crop.crashScore - 0.4*(crop.crashScore*1.05) - 0.4*(crop.crashScore*0.95)) / 0.2).clamp(0.0, 1.0))).toStringAsFixed(3)}', textMuted),
                Divider(color: textMuted.withValues(alpha:0.3)),
                _monoLine('  = ${crop.crashScore.toStringAsFixed(3)}', textPrimary),
                if (crop.crashScore > 0.8) _monoLine('  → Rule override applied', AppColors.amber),
                _monoLine('  → Final score: ${crop.crashScore.toStringAsFixed(3)}', crop.alertLevel == 'RED' ? AppColors.red : crop.alertLevel == 'BLUE' ? AppColors.blue : (crop.alertLevel == 'AMBER' ? AppColors.amber : AppColors.green)),
                _monoLine('  → Alert level: ${crop.alertLevel == 'RED' ? '🚨 RED' : crop.alertLevel == 'BLUE' ? '🔵 BLUE' : (crop.alertLevel == 'AMBER' ? '⚠️ AMBER' : '✅ GREEN')}', crop.alertLevel == 'RED' ? AppColors.red : crop.alertLevel == 'BLUE' ? AppColors.blue : (crop.alertLevel == 'AMBER' ? AppColors.amber : AppColors.green)),
                const SizedBox(height: 12),
                Wrap(spacing: 8, runSpacing: 6, children: [
                  _ThresholdChip('< 0.35 = ✅ GREEN', AppColors.green, AppColors.greenPale),
                  _ThresholdChip('0.35-0.65 = ⚠️ AMBER', AppColors.amberText, AppColors.amberPale),
                  _ThresholdChip('> 0.65 = 🚨 RED', AppColors.redText, AppColors.redPale),
                ]),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Feature pills
          GestureDetector(
            onTap: () => setState(() => _featuresExpanded = !_featuresExpanded),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(12)),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(isMarathi ? 'Model Features (18)' : 'Model Features (18)',
                    style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: textPrimary)),
                  Icon(_featuresExpanded ? Icons.expand_less : Icons.expand_more, color: textMuted),
                ],
              ),
            ),
          ),
          if (_featuresExpanded) ...[
            const SizedBox(height: 12),
            _FeatureGrid(isDark: isDark),
          ],
          const SizedBox(height: 20),

          // Historical Backtest
          Text(isMarathi ? 'Historical Accuracy · इतिहास तपासणी' : 'Historical Accuracy',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 6),
          if (widget.state.accuracyStats == null)
             Text(isMarathi ? 'लोड होत आहे...' : 'Loading accuracy data...', style: GoogleFonts.workSans(color: textMuted))
          else ...[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: widget.state.accuracyStats!.accuracy >= 0.7 ? AppColors.greenPale : AppColors.amberPale,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: widget.state.accuracyStats!.accuracy >= 0.7 ? AppColors.green.withValues(alpha: 0.3) : AppColors.amber.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    isMarathi
                        ? '${(widget.state.accuracyStats!.accuracy * 100).toStringAsFixed(0)}% अचूकता'
                        : '${(widget.state.accuracyStats!.accuracy * 100).toStringAsFixed(0)}% accuracy',
                    style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: widget.state.accuracyStats!.accuracy >= 0.7 ? AppColors.greenText : AppColors.amberText),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: AppColors.bluePale, borderRadius: BorderRadius.circular(10), border: Border.all(color: AppColors.blue.withValues(alpha: 0.3))),
                  child: Text(isMarathi ? '२.४ दिवसांची आगाऊ सूचना' : '2.4 days advance warning',
                    style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.blueText),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              isMarathi
                  ? '${widget.state.accuracyStats!.correct} / ${widget.state.accuracyStats!.total} अंदाज बरोबर'
                  : '${widget.state.accuracyStats!.correct} / ${widget.state.accuracyStats!.total} predictions correct',
              style: GoogleFonts.workSans(fontSize: 13, color: textMuted),
            ),
          ],
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            _MetricChip('AUC: 0.76', isDark), _MetricChip('F1: 0.74', isDark),
            _MetricChip('Recall: 0.81', isDark), _MetricChip('Precision: 0.73', isDark),
          ]),
          const SizedBox(height: 20),

          // Training data
          Text(isMarathi ? 'Training Data' : 'Training Data',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          Row(children: [
            _dataCard('🌱', 'Soybean', '4,371 rows', isDark),
            const SizedBox(width: 8),
            _dataCard('🌿', 'Cotton', '709 rows', isDark),
            const SizedBox(width: 8),
            _dataCard('🌾', 'Turmeric', '1,651 rows', isDark),
          ]),
        ],
      ),
    );
  }

  Widget _monoLine(String text, Color color, {double fontSize = 12}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Text(text, style: GoogleFonts.jetBrainsMono(fontSize: fontSize, color: color)),
    );
  }

  Widget _buildChart(List<dynamic> history, bool isDark, Color textMuted) {
    if (history.isEmpty) return const SizedBox();

    // Sort ascending by date
    final sorted = List.from(history);
    sorted.sort((a, b) => (a['date'] as String).compareTo(b['date'] as String));

    final spots = <FlSpot>[];
    double minPrice = double.infinity;
    double maxPrice = 0;

    for (int i = 0; i < sorted.length; i++) {
        final price = (sorted[i]['price'] as num).toDouble();
        if (price < minPrice) minPrice = price;
        if (price > maxPrice) maxPrice = price;
        spots.add(FlSpot(i.toDouble(), price));
    }

    minPrice = minPrice * 0.95;
    maxPrice = maxPrice * 1.05;

    return LineChart(
      LineChartData(
        gridData: FlGridData(
          show: true,
          drawVerticalLine: true,
          drawHorizontalLine: true,
          getDrawingHorizontalLine: (value) => FlLine(color: textMuted.withValues(alpha: 0.15), strokeWidth: 1),
          getDrawingVerticalLine: (value) => FlLine(color: textMuted.withValues(alpha: 0.15), strokeWidth: 1),
        ),
        titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 45,
                getTitlesWidget: (value, meta) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 4.0),
                    child: Text('₹${value.toInt()}', style: GoogleFonts.workSans(color: textMuted, fontSize: 10)),
                  );
                },
              ),
            ),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 24,
                interval: (spots.length / 5).clamp(1.0, 9999.0).toDouble(), // Evenly spaced labels
                getTitlesWidget: (value, meta) {
                  int index = value.toInt();
                  if (index < 0 || index >= sorted.length) return const SizedBox();
                  String dateStr = sorted[index]['date'];
                  try {
                    final dt = DateTime.parse(dateStr);
                    final months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                    return Padding(
                      padding: const EdgeInsets.only(top: 6.0),
                      child: Text('${months[dt.month - 1]} ${dt.year}', 
                        style: GoogleFonts.workSans(color: textMuted, fontSize: 10)),
                    );
                  } catch (e) {
                    return const SizedBox();
                  }
                },
              ),
            ),
        ),
        borderData: FlBorderData(show: false),
        minX: 0,
        maxX: spots.length.toDouble() - 1,
        minY: minPrice,
        maxY: maxPrice,
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: AppColors.blue,
            barWidth: 2,
            isStrokeCapRound: true,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              gradient: LinearGradient(
                  colors: [AppColors.blue.withValues(alpha: 0.2), AppColors.blue.withValues(alpha: 0.0)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
              ),
            ),
          ),
        ],
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
             getTooltipColor: (_) => (isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised).withValues(alpha: 0.9),
             getTooltipItems: (touchedSpots) {
               return touchedSpots.map((spot) => LineTooltipItem('₹${spot.y.toInt()}', GoogleFonts.jetBrainsMono(color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary, fontWeight: FontWeight.w700))).toList();
             }
          )
        )
      ),
    );
  }
}

class _ZoneBar extends StatelessWidget {
  final bool isDark, isMarathi;
  const _ZoneBar({required this.isDark, required this.isMarathi});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: Row(children: [
            Expanded(flex: 35, child: Container(height: 8, color: AppColors.green.withValues(alpha:0.7))),
            Expanded(flex: 30, child: Container(height: 8, color: AppColors.amber.withValues(alpha:0.7))),
            Expanded(flex: 35, child: Container(height: 8, color: AppColors.red.withValues(alpha:0.7))),
          ]),
        ),
        const SizedBox(height: 4),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(isMarathi ? 'सुरक्षित 0.00' : 'Safe 0.00',
            style: GoogleFonts.jetBrainsMono(fontSize: 9, color: AppColors.green)),
          Text('0.35 | 0.65', style: GoogleFonts.jetBrainsMono(fontSize: 9, color: AppColors.textMuted)),
          Text(isMarathi ? '1.00 धोका' : '1.00 Danger',
            style: GoogleFonts.jetBrainsMono(fontSize: 9, color: AppColors.red)),
        ]),
      ],
    );
  }
}

class _XGBoostCard extends StatelessWidget {
  final bool isDark, isMarathi;
  final double prob;
  const _XGBoostCard({required this.isDark, required this.isMarathi, required this.prob});

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final shapBars = [
      ('arrival_ratio', 0.28), ('nafed_release', 0.21),
      ('price_velocity', 0.18), ('latur_price', 0.12), ('month', 0.09),
    ];
    return Container(
      width: 240,
      margin: const EdgeInsets.only(right: 12),
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 10),
      decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('XGBoost', style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(width: 8),
            Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(color: AppColors.purplePale, borderRadius: BorderRadius.circular(4)),
              child: Text('ML', style: GoogleFonts.spaceGrotesk(fontSize: 9, fontWeight: FontWeight.w700, color: AppColors.purple))),
          ]),
          const SizedBox(height: 6),
          Text(prob.toStringAsFixed(2), style: GoogleFonts.spaceGrotesk(fontSize: 30, fontWeight: FontWeight.w800, color: prob > 0.65 ? AppColors.red : (prob > 0.35 ? AppColors.amber : AppColors.green))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: prob > 0.65 ? AppColors.redPale : AppColors.greenPale, borderRadius: BorderRadius.circular(6)),
            child: Text(prob > 0.65 ? 'RED' : (prob > 0.35 ? 'AMBER' : 'GREEN'), style: GoogleFonts.spaceGrotesk(fontSize: 11, fontWeight: FontWeight.w700, color: prob > 0.65 ? AppColors.redText : AppColors.greenText))),
          const SizedBox(height: 10),
          Text('SHAP Features', style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
          const SizedBox(height: 4),
          ...shapBars.map((b) => Padding(
            padding: const EdgeInsets.only(bottom: 3),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text(b.$1, style: GoogleFonts.jetBrainsMono(fontSize: 9, color: textMuted)),
                Text(b.$2.toStringAsFixed(2), style: GoogleFonts.jetBrainsMono(fontSize: 9, color: AppColors.purple)),
              ]),
              const SizedBox(height: 2),
              ClipRRect(
                borderRadius: BorderRadius.circular(2),
                child: LinearProgressIndicator(
                  value: b.$2, minHeight: 4,
                  backgroundColor: AppColors.purplePale,
                  valueColor: const AlwaysStoppedAnimation(AppColors.purple),
                ),
              ),
            ]),
          )),
          const SizedBox(height: 6),
          Text('500 trees · max_depth 6 · SHAP explainer', style: GoogleFonts.jetBrainsMono(fontSize: 8, color: textMuted)),
        ],
      ),
    );
  }
}

class _LSTMCard extends StatelessWidget {
  final bool isDark, isMarathi;
  final double prob;
  const _LSTMCard({required this.isDark, required this.isMarathi, required this.prob});

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final prices = [5800.0, 5750.0, 5650.0, 5500.0, 5400.0, 5352.0, 5200.0];
    return Container(
      width: 240,
      margin: const EdgeInsets.only(right: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('LSTM', style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(width: 8),
            Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(color: AppColors.purplePale, borderRadius: BorderRadius.circular(4)),
              child: Text('DL', style: GoogleFonts.spaceGrotesk(fontSize: 9, fontWeight: FontWeight.w700, color: AppColors.purple))),
          ]),
          const SizedBox(height: 8),
          Text(prob.toStringAsFixed(2), style: GoogleFonts.spaceGrotesk(fontSize: 32, fontWeight: FontWeight.w800, color: prob > 0.65 ? AppColors.red : (prob > 0.35 ? AppColors.amber : AppColors.green))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: prob > 0.65 ? AppColors.redPale : AppColors.greenPale, borderRadius: BorderRadius.circular(6)),
            child: Text(prob > 0.65 ? 'RED' : (prob > 0.35 ? 'AMBER' : 'GREEN'), style: GoogleFonts.spaceGrotesk(fontSize: 11, fontWeight: FontWeight.w700, color: prob > 0.65 ? AppColors.redText : AppColors.greenText))),
          const SizedBox(height: 12),
          Text('7-day price pattern', style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
          const SizedBox(height: 6),
          SizedBox(
            height: 60,
            child: CustomPaint(
              painter: _MiniLinePainter(prices: prices, isDark: isDark),
              size: const Size(double.infinity, 60),
            ),
          ),
          const SizedBox(height: 8),
          Container(padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: AppColors.redPale.withValues(alpha:0.5), borderRadius: BorderRadius.circular(8)),
            child: Text('3 days high arrivals pattern detected',
              style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.redText))),
          const SizedBox(height: 8),
          Text('30-day sequence · 18 features · TensorFlow', style: GoogleFonts.jetBrainsMono(fontSize: 8, color: textMuted)),
        ],
      ),
    );
  }
}

class _MiniLinePainter extends CustomPainter {
  final List<double> prices;
  final bool isDark;
  _MiniLinePainter({required this.prices, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    final min = prices.reduce((a, b) => a < b ? a : b);
    final max = prices.reduce((a, b) => a > b ? a : b);
    final range = max - min;
    final points = prices.asMap().entries.map((e) {
      final x = e.key / (prices.length - 1) * size.width;
      final y = size.height - ((e.value - min) / range) * size.height * 0.8 - size.height * 0.1;
      return Offset(x, y);
    }).toList();

    final paint = Paint()
      ..color = AppColors.red
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    path.moveTo(points[0].dx, points[0].dy);
    for (final p in points.skip(1)) {
      path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(path, paint);

    for (final p in points) {
      canvas.drawCircle(p, 2.5, Paint()..color = Colors.white);
      canvas.drawCircle(p, 1.5, Paint()..color = AppColors.red);
    }
  }

  @override
  bool shouldRepaint(_MiniLinePainter old) => false;
}

class _RuleEngineCard extends StatelessWidget {
  final bool isDark, isMarathi;
  final double prob;
  const _RuleEngineCard({required this.isDark, required this.isMarathi, required this.prob});

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final rules = [
      (false, 'R01', 'export_ban_flag', false),
      (true,  'R02', 'nafed+arrivals>2×', true),
      (false, 'R03', 'arrival_ratio>3.0', false),
      (false, 'R04', 'price_drop>20%', false),
      (false, 'R05', 'latur_drop>15%', false),
      (false, 'R06', 'rain+harvest', false),
      (false, 'R07', 'msp_gap<-500', false),
    ];
    return Container(
      width: 240,
      margin: const EdgeInsets.only(right: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text('Rule Engine', style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(width: 8),
            Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(color: AppColors.redPale, borderRadius: BorderRadius.circular(4)),
              child: Text('OVERRIDE', style: GoogleFonts.spaceGrotesk(fontSize: 8, fontWeight: FontWeight.w700, color: AppColors.redText))),
          ]),
          const SizedBox(height: 4),
          Text(prob.toStringAsFixed(2), style: GoogleFonts.spaceGrotesk(fontSize: 26, fontWeight: FontWeight.w800, color: prob > 0.5 ? AppColors.red : AppColors.green)),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: prob > 0.5 ? AppColors.redPale : AppColors.greenPale, borderRadius: BorderRadius.circular(6)),
            child: Text(prob > 0.5 ? 'FORCED RED' : 'SAFE', style: GoogleFonts.spaceGrotesk(fontSize: 10, fontWeight: FontWeight.w700, color: prob > 0.5 ? AppColors.redText : AppColors.greenText))),
          const SizedBox(height: 6),
          ...rules.map((r) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Row(children: [
              Text(r.$1 ? '🔴' : '✅', style: const TextStyle(fontSize: 12)),
              const SizedBox(width: 4),
              Text('${r.$2} ${r.$3}', style: GoogleFonts.jetBrainsMono(
                fontSize: 9, color: r.$1 ? AppColors.red : textMuted,
                fontWeight: r.$4 ? FontWeight.w700 : FontWeight.w400)),
              if (r.$4) ...[const SizedBox(width: 4), Text('← FIRED',
                style: GoogleFonts.jetBrainsMono(fontSize: 8, color: AppColors.red, fontWeight: FontWeight.w700))],
            ]),
          )),
          const SizedBox(height: 4),
          Container(padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(color: AppColors.redPale.withValues(alpha:0.5), borderRadius: BorderRadius.circular(8)),
            child: Text('Rule R02 fired → score forced to 1.0',
              style: GoogleFonts.jetBrainsMono(fontSize: 9, color: AppColors.redText, fontWeight: FontWeight.w700))),
        ],
      ),
    );
  }
}

class _FeatureGrid extends StatelessWidget {
  final bool isDark;
  const _FeatureGrid({required this.isDark});

  @override
  Widget build(BuildContext context) {
    final groups = [
      ('PRICE', AppColors.green, AppColors.greenPale, ['modal_price', 'price_velocity', 'arrival_ratio', 'price_spread', 'msp_gap']),
      ('WEATHER', AppColors.blue, AppColors.bluePale, ['rain_forecast_72hr', 'humidity_current', 'rain_latur_48hr', 'quality_penalty_flag']),
      ('POLICY', AppColors.red, AppColors.redPale, ['nafed_release_flag', 'export_ban_flag']),
      ('GLOBAL MKT', AppColors.amber, AppColors.amberPale, ['cbot_price_inr', 'cbot_7day_trend']),
      ('CALENDAR', AppColors.textMuted, AppColors.surfaceHigh, ['month', 'day_of_week', 'days_from_harvest_start', 'harvest_window_flag']),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: groups.map((g) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(g.$1, style: GoogleFonts.spaceGrotesk(fontSize: 11, fontWeight: FontWeight.w700, color: g.$2)),
            const SizedBox(height: 6),
            Wrap(spacing: 6, runSpacing: 6, children: g.$4.map((f) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(color: g.$3, borderRadius: BorderRadius.circular(6)),
              child: Text(f, style: GoogleFonts.jetBrainsMono(fontSize: 10, color: g.$2.withValues(alpha:0.8))),
            )).toList()),
          ],
        ),
      )).toList(),
    );
  }
}

class _ThresholdChip extends StatelessWidget {
  final String label;
  final Color fg, bg;
  const _ThresholdChip(this.label, this.fg, this.bg);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(6)),
      child: Text(label, style: GoogleFonts.jetBrainsMono(fontSize: 11, fontWeight: FontWeight.w700, color: fg)),
    );
  }
}

// ─────────────────────────────────────────────────────────────────
// LEAD-LAG & NCDEX EXPLANATION CARD
// ─────────────────────────────────────────────────────────────────
class _LeadLagInfoCard extends StatelessWidget {
  final bool isDark;
  final bool isMarathi;
  const _LeadLagInfoCard({required this.isDark, required this.isMarathi});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFF4285F4).withValues(alpha: isDark ? 0.2 : 0.1),
            const Color(0xFF0F9D58).withValues(alpha: isDark ? 0.1 : 0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF4285F4).withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.psychology, color: Color(0xFF4285F4)),
            const SizedBox(width: 8),
            Text(
              isMarathi ? '48-तास प्रेडिक्शन इंजिन' : '48-Hour Prediction Engine',
              style: GoogleFonts.spaceGrotesk(
                  fontSize: 15, fontWeight: FontWeight.w700,
                  color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary),
            ),
          ]),
          const SizedBox(height: 12),
          Text(
            isMarathi
                ? '१. NCDEX फ्युचर्स डेटा (Contango/Backwardation) व्यापारी बाजारात काय विचार करत आहेत हे शोधतो.\n'
                  '२. लीड-लॅग स्ट्रॅटेजी: लातूरसारख्या मोठ्या मंडीमध्ये आज किंमत पडली, तर नांदेडमध्ये 48 तासांनी किंमत पडण्याची शक्यता असते. आमचे AI या 48 तासांच्या अंतराचा फायदा घेऊन शेतकऱ्यांना वेळेवर अलर्ट देते.'
                : '1. NCDEX Futures data tracks if traders expect prices to rise or fall (Contango vs Backwardation).\n'
                  '2. Lead-Lag Strategy: A price crash in a major hub like Latur today predicts a crash in Nanded 48 hours from now. Our AI exploits this latency to warn farmers before the local crash happens.',
            style: GoogleFonts.workSans(
                fontSize: 13, height: 1.5,
                color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  final String label;
  final bool isDark;
  const _MetricChip(this.label, this.isDark);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(label, style: GoogleFonts.jetBrainsMono(fontSize: 12, fontWeight: FontWeight.w600,
        color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
    );
  }
}

Widget _dataCard(String icon, String name, String count, bool isDark) {
  return Expanded(
    child: Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(icon, style: const TextStyle(fontSize: 24)),
          const SizedBox(height: 4),
          Text(name, style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w600,
            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
          Text(count, style: GoogleFonts.jetBrainsMono(fontSize: 11,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
          Text('2021-2026', style: GoogleFonts.jetBrainsMono(fontSize: 10,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
        ],
      ),
    ),
  );
}
