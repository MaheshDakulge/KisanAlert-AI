import 'package:flutter/material.dart';
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
    final crop = state.currentCrop!;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Emergency RED banner
          if (crop.alertLevel == 'RED') ...[
            const SizedBox(height: 8),
            _RedBanner(isDark: isDark, isMarathi: state.isMarathi, cropName: state.activeCrop),
          ],
          const SizedBox(height: 16),

          // Crop selector
          _CropTabs(state: state, isDark: isDark),
          const SizedBox(height: 16),

          // Hero Alert Card
          _HeroAlertCard(crop: crop, isDark: isDark, isMarathi: state.isMarathi, onOpenMandi: () {
            state.setActiveTab(1);
          }),
          const SizedBox(height: 20),

          // Three quick crop cards
          _CropQuickCards(state: state, isDark: isDark),
          const SizedBox(height: 24),

          // Best mandi today
          _SectionHeader(
            mrTitle: 'आज सर्वोत्तम मंडी',
            enTitle: 'Best Mandi Today',
            mrSub: 'भाव + अंतर + हवामान + वाहतूक खर्च',
            enSub: 'Based on price + distance + weather + transport cost',
            isMarathi: state.isMarathi, isDark: isDark,
          ),
          const SizedBox(height: 12),
          ...state.currentMandis.where((m) => m.signal != 'RED').take(3).toList().asMap().entries.map((e) {
            final ranks = ['🥇', '🥈', '🥉'];
            final m = e.value;
            return MandiCard(
              rank: ranks[e.key],
              name: m.name,
              distanceKm: m.distanceKm,
              price: m.priceForCrop(state.activeCrop),
              signal: m.signal,
              weather: m.weather,
              advice: m.advice,
              isDark: isDark,
              activeCrop: state.activeCrop,
              isBest: m.isBest,
              onTap: () => onOpenMandi(m),
            );
          }),
          GestureDetector(
            onTap: () => state.setActiveTab(1),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Text(
                state.isMarathi ? 'सर्व ८ मंडी पहा →' : 'View all 8 mandis →',
                style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.green),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // 7-day forecast
          _SectionHeader(mrTitle: '७ दिवसांचा अंदाज', enTitle: '7-Day Forecast', isMarathi: state.isMarathi, isDark: isDark),
          const SizedBox(height: 12),
          SizedBox(
            height: 130,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              itemCount: state.currentForecast.length,
              itemBuilder: (_, i) => ForecastDayCard(
                dayEn: state.currentForecast[i].dayEn, dayMr: state.currentForecast[i].dayMr,
                price: state.currentForecast[i].price, direction: state.currentForecast[i].direction,
                risk: state.currentForecast[i].risk, isDark: isDark, isMarathi: state.isMarathi,
              ),
            ),
          ),
          const SizedBox(height: 24),

          // Active signals
          _SectionHeader(
            mrTitle: 'सक्रिय संकेत', enTitle: 'Active Signals',
            mrSub: 'या संकेतांमुळे RED अलर्ट आला', enSub: 'These signals caused the RED alert',
            isMarathi: state.isMarathi, isDark: isDark,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8, runSpacing: 8,
            children: state.currentSignals.map((s) => SignalChip(
              label: s.label, level: s.level, isDark: isDark,
              onTap: () => onOpenSignal(s),
            )).toList(),
          ),
          const SizedBox(height: 24),

          // Community Chopal
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(state.isMarathi ? 'Community Chopal' : 'Community Chopal',
                style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700,
                  color: textPrimary)),
              GestureDetector(
                onTap: () => state.setActiveTab(4),
                child: Text(state.isMarathi ? 'सगळ्या →' : 'See all →',
                  style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.green)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...state.currentStories.take(2).map((s) => ChopalCard(
            initials: s.initials, avatarColor: s.avatarColor,
            nameEn: s.nameEn, distanceKm: s.distanceKm,
            messageMr: s.messageMr, messageEn: s.messageEn,
            isVerified: s.isVerified, verifiedDate: s.verifiedDate,
            crop: s.crop, saved: s.saved,
            isDark: isDark, isMarathi: state.isMarathi,
          )),
          const SizedBox(height: 24),

          // Quick actions grid
          _SectionHeader(mrTitle: 'जलद क्रिया', enTitle: 'Quick Actions', isMarathi: state.isMarathi, isDark: isDark),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2, shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10, mainAxisSpacing: 10,
            childAspectRatio: 2.5,
            children: [
              _QuickAction(icon: '🎤', mrLabel: 'आवाज प्रश्न', enLabel: 'Voice Query', isMarathi: state.isMarathi, isDark: isDark, onTap: onOpenVoice),
              _QuickAction(icon: '🔔', mrLabel: 'व्हॉट्सअॅप', enLabel: 'WhatsApp Setup', isMarathi: state.isMarathi, isDark: isDark, onTap: () {}),
              _QuickAction(icon: '📊', mrLabel: 'इतिहास', enLabel: 'View Backtest', isMarathi: state.isMarathi, isDark: isDark, onTap: () => state.setActiveTab(2)),
              _QuickAction(icon: '📤', mrLabel: 'शेअर', enLabel: 'Share Alert', isMarathi: state.isMarathi, isDark: isDark, onTap: () {}),
            ],
          ),
          const SizedBox(height: 24),

          // Crisis support
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  state.isMarathi ? 'मानसिक आधार: किसान कॉल सेंटर' : 'Mental health support: Kisan Call Centre',
                  style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w500, color: textMuted),
                ),
                const SizedBox(height: 4),
                Text('📞 1800-180-1551 (Toll Free)',
                  style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.green)),
                Text(state.isMarathi ? '24/7 उपलब्ध' : '24/7 Available',
                  style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Sub-widgets ──────────────────────────────────────────────────────

class _RedBanner extends StatefulWidget {
  final bool isDark;
  final bool isMarathi;
  final String cropName;
  const _RedBanner({required this.isDark, required this.isMarathi, required this.cropName});

  @override
  State<_RedBanner> createState() => _RedBannerState();
}

class _RedBannerState extends State<_RedBanner> with SingleTickerProviderStateMixin {
  bool _dismissed = false;
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1000))
      ..repeat(reverse: true);
    _anim = Tween(begin: 1.0, end: 0.85).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, _) => Opacity(
        opacity: _anim.value,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: AppColors.red,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.isMarathi
                      ? '🚨 RED अलर्ट — ${widget.cropName == "Soybean" ? "सोयाबीन" : widget.cropName} विकू नका आज'
                      : '🚨 RED ALERT ACTIVE — Do not sell ${widget.cropName} today',
                  style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                ),
              ),
              GestureDetector(
                onTap: () => setState(() => _dismissed = true),
                child: const Icon(Icons.close, color: Colors.white, size: 20),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CropTabs extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _CropTabs({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final crops = [
      ('Soybean', '🌱', 'सोयाबीन'),
      ('Cotton', '🌿', 'कापूस'),
      ('Turmeric', '🌾', 'हळद'),
    ];
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: crops.map((c) {
        final isActive = state.activeCrop == c.$1;
        return GestureDetector(
          onTap: () => state.setActiveCrop(c.$1),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: isActive ? AppColors.green : (isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              '${c.$2} ${state.isMarathi ? c.$3 : c.$1}',
              style: GoogleFonts.workSans(
                fontSize: 14, fontWeight: FontWeight.w600,
                color: isActive ? Colors.white : (isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

class _HeroAlertCard extends StatelessWidget {
  final CropData crop;
  final bool isDark;
  final bool isMarathi;
  final VoidCallback onOpenMandi;

  const _HeroAlertCard({required this.crop, required this.isDark, required this.isMarathi, required this.onOpenMandi});

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final borderColor = crop.alertLevel == 'RED' ? AppColors.red : crop.alertLevel == 'AMBER' ? AppColors.amber : AppColors.green;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final mspGap = crop.price - crop.msp;

    return Container(
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(24),
        border: Border(top: BorderSide(color: borderColor, width: 4)),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.06), blurRadius: 20, offset: const Offset(0, 6))],
      ),
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('16 April 2026 · ${isMarathi ? "आजचा अंदाज" : "Today's Forecast"}',
                style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
              Row(children: [
                const LiveDot(), const SizedBox(width: 6),
                Text('3 Models + Live Data', style: GoogleFonts.jetBrainsMono(fontSize: 10, color: textMuted)),
              ]),
            ],
          ),
          const SizedBox(height: 20),
          CrashScoreGauge(score: crop.crashScore, isDark: isDark),
          const SizedBox(height: 16),
          AlertBadge(
            level: crop.alertLevel,
            label: crop.alertLevel == 'RED'
                ? (isMarathi ? '🚨 RED — ${_cropMr(crop.name)} विकू नका' : '🚨 RED — Do NOT sell ${crop.name}')
                : crop.alertLevel == 'AMBER'
                    ? (isMarathi ? '⚠️ AMBER — सावध राहा' : '⚠️ AMBER — Be cautious')
                    : (isMarathi ? '✅ GREEN — आत्ता विका!' : '✅ GREEN — Safe to sell!'),
            isDark: isDark,
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('₹${crop.price.toStringAsFixed(0)}',
                style: GoogleFonts.spaceGrotesk(fontSize: 38, fontWeight: FontWeight.w800, color: textPrimary)),
              Padding(
                padding: const EdgeInsets.only(bottom: 6, left: 4),
                child: Text(isMarathi ? '/क्विंटल' : '/qtl',
                  style: GoogleFonts.workSans(fontSize: 14, color: textMuted)),
              ),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
            decoration: BoxDecoration(
              color: mspGap >= 0 ? AppColors.greenPale : AppColors.redPale,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              isMarathi
                  ? 'MSP ₹${crop.msp.toStringAsFixed(0)} · ${mspGap >= 0 ? "+₹${mspGap.toStringAsFixed(0)} जास्त ✅" : "₹${(-mspGap).toStringAsFixed(0)} कमी 🔴"}'
                  : 'MSP ₹${crop.msp.toStringAsFixed(0)} · ${mspGap >= 0 ? "+₹${mspGap.toStringAsFixed(0)} above MSP ✅" : "₹${(-mspGap).toStringAsFixed(0)} below MSP 🔴"}',
              style: GoogleFonts.workSans(
                fontSize: 13, fontWeight: FontWeight.w600,
                color: mspGap >= 0 ? AppColors.greenText : AppColors.redText,
              ),
            ),
          ),
          const SizedBox(height: 16),
          MarathiAIBox(
            marathiText: crop.message,
            englishText: 'Do not sell ${crop.name} today. NAFED released stock + arrivals 65% up at Latur. Osmanabad paying ₹550 more — go there today.',
            isDark: isDark,
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: onOpenMandi,
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(colors: [AppColors.green, AppColors.greenVivid]),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      isMarathi ? '🗺️ आज सर्वोत्तम मंडी' : '🗺️ Best Mandi Today',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  decoration: BoxDecoration(
                    border: Border.all(color: AppColors.greenVivid),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    isMarathi ? '📤 WhatsApp वर शेअर' : '📤 Share on WhatsApp',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.green),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _cropMr(String c) {
    if (c == 'Soybean') return 'सोयाबीन';
    if (c == 'Cotton') return 'कापूस';
    return 'हळद';
  }
}

class _CropQuickCards extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _CropQuickCards({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final crops = [
      ('Soybean', '🌱', 'सोयाबीन', 5352.0, 'RED', -120.0),
      ('Cotton', '🌿', 'कापूस', 7845.0, 'RED', -80.0),
      ('Turmeric', '🌾', 'हळद', 12000.0, 'AMBER', 0.0),
    ];
    return SizedBox(
      height: 120,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        itemCount: crops.length,
        itemBuilder: (_, i) {
          final c = crops[i];
          final isActive = state.activeCrop == c.$1;
          final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;
          return GestureDetector(
            onTap: () => state.setActiveCrop(c.$1),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 140,
              margin: const EdgeInsets.only(right: 10),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: surface,
                borderRadius: BorderRadius.circular(16),
                border: isActive ? Border.all(color: AppColors.greenVivid, width: 2) : null,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(c.$2, style: const TextStyle(fontSize: 18)),
                    const SizedBox(width: 6),
                    Text(state.isMarathi ? c.$3 : c.$1,
                      style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w600,
                        color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
                  ]),
                  const SizedBox(height: 6),
                  Text('₹${c.$4.toStringAsFixed(0)}',
                    style: GoogleFonts.spaceGrotesk(fontSize: 20, fontWeight: FontWeight.w700,
                      color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
                  const SizedBox(height: 4),
                  Row(children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: signalBgColor(c.$5, isDark), borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(c.$5, style: GoogleFonts.spaceGrotesk(
                        fontSize: 9, fontWeight: FontWeight.w700, color: signalColor(c.$5, isDark))),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      c.$6 < 0 ? '↓ ₹${(-c.$6).toStringAsFixed(0)}' : c.$6 > 0 ? '↑ ₹${c.$6.toStringAsFixed(0)}' : '→ stable',
                      style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w500,
                        color: c.$6 < 0 ? AppColors.red : c.$6 > 0 ? AppColors.green : AppColors.amber),
                    ),
                  ]),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String mrTitle;
  final String enTitle;
  final String? mrSub;
  final String? enSub;
  final bool isMarathi;
  final bool isDark;

  const _SectionHeader({
    required this.mrTitle, required this.enTitle,
    this.mrSub, this.enSub,
    required this.isMarathi, required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          isMarathi ? '$mrTitle / $enTitle' : enTitle,
          style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700,
            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary),
        ),
        if (mrSub != null) Text(
          isMarathi ? mrSub! : enSub ?? '',
          style: GoogleFonts.workSans(fontSize: 12,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
        ),
      ],
    );
  }
}

class _QuickAction extends StatelessWidget {
  final String icon;
  final String mrLabel;
  final String enLabel;
  final bool isMarathi;
  final bool isDark;
  final VoidCallback onTap;

  const _QuickAction({
    required this.icon, required this.mrLabel, required this.enLabel,
    required this.isMarathi, required this.isDark, required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: (isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Text(icon, style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                isMarathi ? mrLabel : enLabel,
                style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600,
                  color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
