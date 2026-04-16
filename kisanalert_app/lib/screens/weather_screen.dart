import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/shared_widgets.dart';

class WeatherScreen extends StatelessWidget {
  final AppState state;
  const WeatherScreen({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final isDark = state.isDark;
    final isMarathi = state.isMarathi;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
    final surfaceHigh = isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh;

    final days = [
      ('🌧️', isMarathi ? 'आज' : 'Today', '29°', '22mm', 'HIGH', true),
      ('⛅', isMarathi ? 'उद्या' : 'Day 2', '31°', '8mm', 'MED', false),
      ('☀️', isMarathi ? 'रवि' : 'Day 3', '34°', '0mm', 'LOW', false),
      ('☀️', isMarathi ? 'सोम' : 'Day 4', '35°', '0mm', 'LOW', false),
      ('🌤️', isMarathi ? 'मंगळ' : 'Day 5', '33°', '3mm', 'LOW', false),
      ('☀️', isMarathi ? 'बुध' : 'Day 6', '36°', '0mm', 'BEST', true),
      ('☀️', isMarathi ? 'गुरु' : 'Day 7', '37°', '0mm', 'BEST', true),
    ];

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),

          // Current conditions
          AgronomistCard(
            isDark: isDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('🌧️', style: TextStyle(fontSize: 48)),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('29°C', style: GoogleFonts.spaceGrotesk(fontSize: 28, fontWeight: FontWeight.w700, color: textPrimary)),
                          Text(isMarathi ? 'आर्द्रता: 84%' : 'Humidity: 84%', style: GoogleFonts.workSans(fontSize: 14, color: textMuted)),
                          Text(isMarathi ? 'आज रात्री: 22mm पाऊस' : 'Tonight: 22mm rain expected', style: GoogleFonts.workSans(fontSize: 14, color: textMuted)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                  decoration: BoxDecoration(color: AppColors.redPale, borderRadius: BorderRadius.circular(10)),
                  child: Text(
                    isMarathi
                        ? '🔴 उच्च धोका — आज रात्री पाऊस न काढलेल्या पिकाला नुकसान करेल'
                        : '🔴 HIGH RISK — Rain tonight will damage unharvested crops',
                    style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.redText),
                  ),
                ),
                const SizedBox(height: 8),
                Text(isMarathi ? '📡 Open-Meteo · नांदेड · ३ तासांपूर्वी अपडेट' : '📡 Open-Meteo · Nanded · Updated 3 hours ago',
                  style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // 7-day strip
          Text(isMarathi ? '७ दिवसांचा हवामान अंदाज' : '7-Day Weather Forecast',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          SizedBox(
            height: 130,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              itemCount: days.length,
              itemBuilder: (_, i) {
                final d = days[i];
                final isBest = d.$5 == 'BEST';
                final riskColor = d.$5 == 'HIGH' ? AppColors.red
                    : d.$5 == 'MED' ? AppColors.amber
                    : d.$5 == 'BEST' ? AppColors.green
                    : AppColors.green;
                final bg = isBest
                    ? (isDark ? AppColors.green.withValues(alpha: 0.2) : AppColors.greenPale)
                    : d.$5 == 'HIGH'
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
                      Text(d.$2, style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w600, color: textMuted)),
                      Text(d.$1, style: const TextStyle(fontSize: 26)),
                      Text(d.$3, style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700, color: textPrimary)),
                      Text(d.$4, style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                        decoration: BoxDecoration(color: riskColor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
                        child: Text(isBest ? '⭐ SELL' : d.$5,
                          style: GoogleFonts.spaceGrotesk(fontSize: 8, fontWeight: FontWeight.w700, color: riskColor)),
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
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary),
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
                  isMarathi ? '38mm पाऊस उद्या. काढणी विंडो लवकर बंद होत आहे.' : '38mm rain forecast tomorrow. Harvest window closing fast.', AppColors.blue, isDark),
                _ArrowStep(),
                _FusionStep('📦', isMarathi ? 'गुणवत्ता धोका' : 'Quality Risk',
                  isMarathi ? 'ओला माल: Grade A ते Grade C. ₹2,000/qtl दंड.' : 'Wet crop: Grade A drops to Grade C. Rs.2,000/qtl penalty.', AppColors.amber, isDark),
                _ArrowStep(),
                _FusionStep('📊', isMarathi ? 'भाव संकेत' : 'Price Signal',
                  isMarathi ? '₹14,200 आत्ता. पावसानंतर 2 दिवसात ₹11,800.' : '₹14,200 now. Post-rain drop to ₹11,800 in 2 days.', AppColors.amber, isDark),
                _ArrowStep(),
                _FusionStep('⚡', isMarathi ? 'तुमची कृती' : 'Your Action',
                  isMarathi ? 'आज रात्री काढा. उद्या सकाळी उस्मानाबादला विका. फायदा: ₹4,400/qtl' : 'Harvest TONIGHT. Sell at Osmanabad tomorrow AM. Gain: ₹4,400/qtl', AppColors.green, isDark),
              ],
            ),
          ),
          const SizedBox(height: 16),
          AgronomistCard(
            isDark: isDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isMarathi
                      ? 'हळद आत्ताच काढा! उद्या पाऊस येणार आहे आणि माल खराब होईल. थांबल्यास ₹4,400 प्रति क्विंटल नुकसान होईल. आज रात्री काढा, उद्या सकाळी विका.'
                      : 'Harvest turmeric tonight. Rain tomorrow will damage quality. Waiting costs ₹4,400/quintal. Harvest tonight, sell tomorrow morning.',
                  style: GoogleFonts.workSans(fontSize: 17, fontWeight: FontWeight.w500, height: 1.6,
                    color: textPrimary),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Formula card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: surfaceHigh, borderRadius: BorderRadius.circular(16)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(isMarathi ? 'नुकसान कसे मोजतो' : 'How we calculate your loss:',
                  style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: textPrimary)),
                const SizedBox(height: 12),
                ...[
                  ('quality_loss_if_wait', null, null),
                  ('  = base_price × 0.15 × your_quantity', null, null),
                  ('  = ₹14,200 × 0.15 × 10 quintals', null, null),
                  ('  = ₹21,300 quality penalty', AppColors.amber, null),
                  ('', null, null),
                  ('price_drop_if_wait', null, null),
                  ('  = predicted_drop × your_quantity', null, null),
                  ('  = ₹2,400 × 10 quintals', null, null),
                  ('  = ₹24,000 price loss', AppColors.amber, null),
                  ('', null, null),
                  ('Total loss if you wait:', null, null),
                  ('  = ₹21,300 + ₹24,000', null, null),
                  ('  = ₹45,300 total at risk', AppColors.red, FontWeight.w700),
                ].map((l) => l.$1.isEmpty ? const SizedBox(height: 4) : Text(l.$1,
                  style: GoogleFonts.jetBrainsMono(fontSize: 11,
                    color: l.$2 ?? textMuted,
                    fontWeight: l.$3 ?? FontWeight.w400))),
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: AppColors.greenPale, borderRadius: BorderRadius.circular(10)),
                  child: Text(
                    isMarathi ? 'आज रात्री विका: ₹45,300 पर्यंत वाचवा' : 'Sell tonight: Save up to ₹45,300',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: AppColors.greenText),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // District weather comparison
          Text(isMarathi ? 'जवळच्या जिल्ह्यांचे हवामान' : 'Nearby Districts Weather',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          ...[
            ('Nanded', '🌧️', '22mm', AppColors.redPale, 'HIGH RISK', false),
            ('Latur', '⛅', '8mm', AppColors.amberPale, 'MED RISK', false),
            ('Osmanabad', '☀️', '0mm', AppColors.greenPale, 'CLEAR ⭐', true),
            ('Parbhani', '⛈️', '45mm', AppColors.redPale, 'STORM AVOID ✗', false),
            ('Hingoli', '🌧️', '18mm', AppColors.amberPale, 'MED RISK', false),
          ].map((d) => Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: d.$4,
              borderRadius: BorderRadius.circular(12),
              border: d.$6 ? Border.all(color: AppColors.greenVivid, width: 2) : null,
            ),
            child: Row(
              children: [
                Text(d.$2, style: const TextStyle(fontSize: 22)),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(d.$1, style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary)),
                    Text('Rain: ${d.$3}', style: GoogleFonts.workSans(fontSize: 12, color: AppColors.textMuted)),
                  ]),
                ),
                Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text(d.$5, style: GoogleFonts.spaceGrotesk(fontSize: 12, fontWeight: FontWeight.w700,
                    color: d.$5.contains('CLEAR') ? AppColors.greenText
                        : d.$5.contains('STORM') ? AppColors.redText
                        : AppColors.amberText)),
                  if (d.$6) GestureDetector(
                    onTap: () {},
                    child: Container(
                      margin: const EdgeInsets.only(top: 4),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(gradient: const LinearGradient(colors: [AppColors.green, AppColors.greenVivid]), borderRadius: BorderRadius.circular(6)),
                      child: Text(isMarathi ? 'दिशा मिळवा' : 'Get Directions',
                        style: GoogleFonts.workSans(fontSize: 10, fontWeight: FontWeight.w700, color: Colors.white)),
                    ),
                  ),
                ]),
              ],
            ),
          )),
          const SizedBox(height: 20),

          // Harvest calendar
          Text(isMarathi ? 'पीक काढणी कॅलेंडर' : 'Harvest Calendar',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          ...[
            ('🌱 Soybean', 0.7, 1.0, isMarathi ? 'Oct-Nov · 🔴 आता सर्वात महत्त्वाचा काळ' : 'Oct-Nov · 🔴 PEAK SEASON NOW', AppColors.red),
            ('🌿 Cotton', 0.3, 0.7, isMarathi ? 'Nov-Dec · 📅 लवकरच सुरू' : 'Nov-Dec · 📅 Starting Soon', AppColors.amber),
            ('🌾 Turmeric', 0.1, 0.4, isMarathi ? 'Jan-Feb · ⏳ 2 महिने बाकी' : 'Jan-Feb · ⏳ 2 Months Away', AppColors.textMuted),
          ].map((c) => Container(
            margin: const EdgeInsets.only(bottom: 10),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text(c.$1, style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary)),
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
                        gradient: LinearGradient(colors: [c.$5.withValues(alpha: 0.4), c.$5], begin: Alignment(-1 + c.$2 * 2, 0), end: Alignment(1, 0)),
                      ),
                    ),
                  ),
                ]),
              ),
              const SizedBox(height: 4),
              Text(c.$4.split('·').first.trim(), style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
            ]),
          )),
        ],
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
          Text(title, style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700, color: color)),
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
      child: const Text('→', style: TextStyle(fontSize: 20, color: AppColors.amber, fontWeight: FontWeight.w700)),
    );
  }
}
