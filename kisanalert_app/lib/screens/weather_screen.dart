import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../data/app_data.dart';
import '../widgets/shared_widgets.dart';

class WeatherScreen extends StatefulWidget {
  final AppState state;
  const WeatherScreen({super.key, required this.state});

  @override
  State<WeatherScreen> createState() => _WeatherScreenState();
}

class _WeatherScreenState extends State<WeatherScreen> {
  bool _loading = true;
  Map<String, dynamic>? _weatherData;

  @override
  void initState() {
    super.initState();
    _fetchWeather();
  }

  Future<void> _fetchWeather() async {
    setState(() { _loading = true; });
    try {
      final data = await ApiService.getWeather('Nanded');
      if (mounted) setState(() { _weatherData = data; _loading = false; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final isMarathi = widget.state.isMarathi;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;

    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: AppColors.green));
    }

    // Parse live forecast or use fallback
    final forecastRaw = (_weatherData?['forecast'] as List?) ?? [];
    final current = (_weatherData?['current'] as Map?) ?? {};
    final tempNow = current['temp_max_c'] != null ? '${current['temp_max_c']}°C' : '—';
    final rainNow = current['rain_mm'] != null ? '${current['rain_mm']}mm' : '0mm';
    final iconNow = current['icon'] as String? ?? '☀️';
    final riskNow = current['risk'] as String? ?? 'LOW';

    final dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    final dayNamesMr = ['र', 'सो', 'मं', 'बु', 'गु', 'शु', 'श'];

    return RefreshIndicator(
      color: AppColors.green,
      onRefresh: _fetchWeather,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 16),

            // Current conditions — LIVE
            AgronomistCard(
              isDark: isDark,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(iconNow, style: const TextStyle(fontSize: 48)),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(tempNow, style: GoogleFonts.spaceGrotesk(
                              fontSize: 28, fontWeight: FontWeight.w700, color: textPrimary)),
                            Text(isMarathi ? 'पाऊस: $rainNow' : 'Rain: $rainNow',
                              style: GoogleFonts.workSans(fontSize: 14, color: textMuted)),
                            Text(isMarathi ? 'धोका: $riskNow' : 'Risk: $riskNow',
                              style: GoogleFonts.workSans(fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: riskNow == 'HIGH' ? AppColors.red
                                    : riskNow == 'MED' ? AppColors.amber
                                    : AppColors.green)),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (riskNow == 'HIGH')
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                      decoration: BoxDecoration(
                        color: AppColors.redPale, borderRadius: BorderRadius.circular(10)),
                      child: Text(
                        isMarathi
                            ? '🔴 उच्च धोका — आज रात्री पाऊस, पिकाची काळजी घ्या'
                            : '🔴 HIGH RISK — Rain tonight, protect your harvest',
                        style: GoogleFonts.workSans(
                          fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.redText),
                      ),
                    ),
                  const SizedBox(height: 8),
                  Text(isMarathi
                      ? '📡 Open-Meteo · नांदेड · लाईव्ह डेटा'
                      : '📡 Open-Meteo · Nanded · Live Data',
                    style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // 7-day strip — LIVE
            Text(isMarathi ? '७ दिवसांचा हवामान अंदाज' : '7-Day Weather Forecast',
              style: GoogleFonts.spaceGrotesk(
                fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(height: 12),
            SizedBox(
              height: 130,
              child: forecastRaw.isEmpty
                  ? Center(child: Text(isMarathi ? 'डेटा उपलब्ध नाही' : 'No forecast available',
                      style: GoogleFonts.workSans(color: textMuted)))
                  : ListView.builder(
                      scrollDirection: Axis.horizontal,
                      physics: const BouncingScrollPhysics(),
                      itemCount: forecastRaw.length,
                      itemBuilder: (_, i) {
                        final d = forecastRaw[i] as Map;
                        final rain = (d['rain_mm'] as num?)?.toDouble() ?? 0.0;
                        final temp = '${d['temp_max_c'] ?? '--'}°';
                        final risk = d['risk'] as String? ?? 'LOW';
                        final icon = d['icon'] as String? ?? '☀️';
                        final isBest = risk == 'LOW' && rain == 0;
                        final date = DateTime.tryParse(d['date'] as String? ?? '');
                        String dayLabel = 'Day ${i+1}';
                        String dayLabelMr = '${i+1}';
                        if (date != null) {
                          dayLabel = i == 0 ? (isMarathi ? 'आज' : 'Today')
                              : dayNames[date.weekday % 7];
                          dayLabelMr = i == 0 ? 'आज' : dayNamesMr[date.weekday % 7];
                        }
                        final riskColor = risk == 'HIGH' ? AppColors.red
                            : risk == 'MED' ? AppColors.amber
                            : AppColors.green;
                        final bg = isBest
                            ? (isDark ? AppColors.green.withValues(alpha: 0.2) : AppColors.greenPale)
                            : risk == 'HIGH'
                                ? (isDark ? AppColors.red.withValues(alpha: 0.15) : AppColors.redPale)
                                : (isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised);
                        return Container(
                          width: 82,
                          margin: const EdgeInsets.only(right: 8),
                          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                          decoration: BoxDecoration(
                            color: bg,
                            borderRadius: BorderRadius.circular(12),
                            border: isBest ? Border.all(color: AppColors.greenVivid, width: 2) : null,
                          ),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              Text(isMarathi ? dayLabelMr : dayLabel,
                                style: GoogleFonts.workSans(
                                  fontSize: 11, fontWeight: FontWeight.w600, color: textMuted)),
                              Text(icon, style: const TextStyle(fontSize: 26)),
                              Text(temp, style: GoogleFonts.spaceGrotesk(
                                fontSize: 13, fontWeight: FontWeight.w700, color: textPrimary)),
                              Text('${rain.toStringAsFixed(0)}mm',
                                style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                                decoration: BoxDecoration(
                                  color: riskColor.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(4)),
                                child: Text(isBest ? '⭐ SELL' : risk,
                                  style: GoogleFonts.spaceGrotesk(
                                    fontSize: 8, fontWeight: FontWeight.w700, color: riskColor)),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
            const SizedBox(height: 24),

            // Climate-to-Cash Fusion
            Text(
              isMarathi ? 'Climate-to-Cash फ्यूजन' : 'Climate-to-Cash Fusion',
              style: GoogleFonts.spaceGrotesk(
                fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary),
            ),
            Text(
              isMarathi ? 'हवामान + भाव = एक निर्णय, एक रुपया' : 'Weather + Price = One Decision, One Number',
              style: GoogleFonts.workSans(fontSize: 12, color: textMuted),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 180,
              child: ListView(
                scrollDirection: Axis.horizontal,
                physics: const BouncingScrollPhysics(),
                children: [
                  _FusionStep('🌧️', isMarathi ? 'हवामान संकेत' : 'Weather Signal',
                    isMarathi ? '$rainNow पाऊस आज. काढणी विंडो बंद होत आहे.' : '$rainNow rain today. Harvest window closing.', AppColors.blue, isDark),
                  _ArrowStep(),
                  _FusionStep('📦', isMarathi ? 'गुणवत्ता धोका' : 'Quality Risk',
                    isMarathi ? 'ओला माल: Grade A ते Grade C. ₹2,000/qtl दंड.' : 'Wet crop: Grade A drops to C. ₹2,000/qtl penalty.', AppColors.amber, isDark),
                  _ArrowStep(),
                  _FusionStep('⚡', isMarathi ? 'तुमची कृती' : 'Your Action',
                    isMarathi ? 'आज रात्री काढा, उद्या विका.' : 'Harvest tonight, sell tomorrow.', AppColors.green, isDark),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // District weather comparison
            Text(isMarathi ? 'जवळच्या जिल्ह्यांचे हवामान' : 'Nearby Districts Weather',
              style: GoogleFonts.spaceGrotesk(
                fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(height: 12),
            ...[
              ('Nanded',    '🌧️', rainNow, riskNow == 'HIGH', riskNow),
              ('Latur',     '⛅',  '8mm',   false,             'MED'),

              ('Parbhani',  '⛈️', '45mm',  false,             'HIGH'),
              ('Hingoli',   '🌧️', '18mm',  false,             'MED'),
            ].map((d) {
              final riskC = d.$5 == 'HIGH' ? AppColors.red
                  : d.$5 == 'MED' ? AppColors.amber : AppColors.green;
              final bgC = d.$5 == 'HIGH' ? AppColors.redPale
                  : d.$5 == 'MED' ? AppColors.amberPale : AppColors.greenPale;
              final isBestD = d.$5 == 'LOW';
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: bgC,
                  borderRadius: BorderRadius.circular(12),
                  border: isBestD ? Border.all(color: AppColors.greenVivid, width: 2) : null,
                ),
                child: Row(
                  children: [
                    Text(d.$2, style: const TextStyle(fontSize: 22)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(d.$1, style: GoogleFonts.workSans(
                          fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                        Text('Rain: ${d.$3}',
                          style: GoogleFonts.workSans(fontSize: 12, color: AppColors.textMuted)),
                      ]),
                    ),
                    Text(
                      isBestD ? '⭐ CLEAR — SELL NOW' : '${d.$5} RISK',
                      style: GoogleFonts.spaceGrotesk(
                        fontSize: 12, fontWeight: FontWeight.w700, color: riskC),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 20),

            // Harvest calendar
            Text(isMarathi ? 'पीक काढणी कॅलेंडर' : 'Harvest Calendar',
              style: GoogleFonts.spaceGrotesk(
                fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
            const SizedBox(height: 12),
            ...[
              ('🌱 Soybean',  0.7, 1.0, isMarathi ? 'Oct-Nov · 🔴 आता सर्वात महत्त्वाचा काळ' : 'Oct-Nov · 🔴 PEAK SEASON NOW', AppColors.red),
              ('🌿 Cotton',   0.3, 0.7, isMarathi ? 'Nov-Dec · 📅 लवकरच सुरू' : 'Nov-Dec · 📅 Starting Soon', AppColors.amber),
              ('🌾 Turmeric', 0.1, 0.4, isMarathi ? 'Jan-Feb · ⏳ 2 महिने बाकी' : 'Jan-Feb · ⏳ 2 Months Away', AppColors.textMuted),
            ].map((c) => Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(12)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                  Text(c.$1, style: GoogleFonts.workSans(
                    fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary)),
                  Text(c.$4.split('·').last.trim(),
                    style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w600, color: c.$5)),
                ]),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: Stack(children: [
                    Container(height: 8, color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh),
                    FractionallySizedBox(
                      widthFactor: c.$3,
                      child: Container(
                        height: 8,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [c.$5.withValues(alpha: 0.4), c.$5],
                            begin: Alignment(-1 + c.$2 * 2, 0), end: Alignment(1, 0)),
                        ),
                      ),
                    ),
                  ]),
                ),
                const SizedBox(height: 4),
                Text(c.$4.split('·').first.trim(),
                  style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
              ]),
            )),
          ],
        ),
      ),
    );
  }
}

class _FusionStep extends StatelessWidget {
  final String icon, title, desc;
  final Color color;
  final bool isDark;
  const _FusionStep(this.icon, this.title, this.desc, this.color, this.isDark);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: isDark ? 0.15 : 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.3), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(icon, style: const TextStyle(fontSize: 28)),
          const SizedBox(height: 6),
          Text(title, style: GoogleFonts.spaceGrotesk(
            fontSize: 13, fontWeight: FontWeight.w700, color: color)),
          const SizedBox(height: 4),
          Text(desc, style: GoogleFonts.workSans(fontSize: 11, height: 1.4,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _ArrowStep extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 6),
      alignment: Alignment.center,
      child: const Text('→', style: TextStyle(
        fontSize: 20, color: AppColors.amber, fontWeight: FontWeight.w700)),
    );
  }
}
