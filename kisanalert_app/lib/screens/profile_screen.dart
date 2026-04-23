import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../widgets/shared_widgets.dart';
import '../data/app_data.dart';

class ProfileScreen extends StatefulWidget {
  final AppState state;
  final VoidCallback onOpenVoice;

  const ProfileScreen({super.key, required this.state, required this.onOpenVoice});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final Map<String, bool> _toggles = {
    'whatsapp': true, 'sms': true, 'voice': true,
    'chopal': false, 'nafed': true, 'export': true,
  };
  String? _voiceAnswer;

  // Pre-set questions for Gemini voice demo — answers come from real API
  final List<String> _sampleQuestions = [
    'सोयाबीन कधी विकायचे?',
    'आज सर्वोत्तम मंडी कुठे?',
    'MSP किती आहे?',
    'पाऊस कधी येणार?',
    'NAFED साठा का पडतो?',
  ];

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final isMarathi = widget.state.isMarathi;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),

          // Farmer card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(24)),
            child: Column(
              children: [
                Row(
                  children: [
                    Container(
                      width: 72, height: 72,
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(colors: [AppColors.green, AppColors.greenVivid]),
                        shape: BoxShape.circle,
                      ),
                      alignment: Alignment.center,
                      child: Text('MD', style: GoogleFonts.spaceGrotesk(fontSize: 28, fontWeight: FontWeight.w700, color: Colors.white)),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Mahesh Dakulge', style: GoogleFonts.spaceGrotesk(fontSize: 20, fontWeight: FontWeight.w800, color: textPrimary)),
                          Text('📍 ${isMarathi ? "नांदेड, महाराष्ट्र" : "Nanded, Maharashtra"}',
                            style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
                          Text(isMarathi ? 'एप्रिल 2026 पासून · 12 एकर · 3 पिके' : 'Member since April 2026 · 12 acres · 3 crops',
                            style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8, runSpacing: 8,
                  children: ['🌱 सोयाबीन', '🌿 कापूस', '🌾 हळद'].map((c) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(color: AppColors.greenPale, borderRadius: BorderRadius.circular(999)),
                    child: Text(c, style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.greenText)),
                  )).toList(),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Impact stats
          Text(isMarathi ? 'माझा प्रभाव / My Impact' : 'My Impact',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2, shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: 10, mainAxisSpacing: 10,
            childAspectRatio: 1.7,
            children: [
          _StatCard(
            isMarathi ? 'मिळालेले अलर्ट' : 'Alerts received',
            '${widget.state.farmerStats?['total_alerts'] ?? 47}',
            AppColors.greenPale, AppColors.greenText, isDark
          ),
          _StatCard(
            isMarathi ? 'पकडलेले क्रॅश' : 'Crashes caught',
            widget.state.farmerStats != null
                ? '${widget.state.farmerStats!['crashes_caught']}'
                : widget.state.accuracyStats != null
                    ? '${widget.state.accuracyStats!.correct}/${widget.state.accuracyStats!.total}'
                    : '0/0',
            AppColors.greenPale, AppColors.greenText, isDark
          ),
          _StatCard(
            isMarathi ? 'वाचवलेले पैसे' : 'Money saved',
            '${widget.state.farmerStats?['money_saved'] ?? '₹1.2L'}',
            AppColors.greenPale, AppColors.greenText, isDark
          ),
          _StatCard(
            isMarathi ? 'अलर्ट स्ट्रीक 🔥' : 'Alert streak 🔥',
            '${widget.state.farmerStats?['alert_streak'] ?? 23} days',
            AppColors.amberPale, AppColors.amberText, isDark
          ),
            ],
          ),
          const SizedBox(height: 12),
          AgronomistCard(
            isDark: isDark,
            child: Text(
              isMarathi
                  ? 'तुम्ही या सीझनमध्ये KisanAlert अंदाज वापरून ₹1,20,000 वाचवले! 🎉'
                  : 'You saved ₹1,20,000 this season following KisanAlert predictions! 🎉',
              style: GoogleFonts.workSans(fontSize: 16, fontWeight: FontWeight.w600,
                color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary, height: 1.5),
            ),
          ),
          const SizedBox(height: 20),

          // MSP tracker
          Text(isMarathi ? 'माझी पिके आणि MSP' : 'My Crops & MSP',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          ...[
            ('🌱 Soybean', 4892.0, 5352.0, surface),
            ('🌿 Cotton', 7121.0, 7845.0, isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh),
            ('🌾 Turmeric', 12000.0, 12000.0, isDark ? AppColors.darkSurface.withValues(alpha: 0.5) : AppColors.amberPale),
          ].map((d) {
            final gap = d.$3 - d.$2;
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: d.$4, borderRadius: BorderRadius.circular(12)),
              child: Row(children: [
                Text(d.$1, style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary)),
                const Spacer(),
                Text('MSP ₹${d.$2.toStringAsFixed(0)}', style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
                const SizedBox(width: 8),
                Text('₹${d.$3.toStringAsFixed(0)}', style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700, color: textPrimary)),
                const SizedBox(width: 8),
                Text(
                  gap > 0 ? '+₹${gap.toStringAsFixed(0)} ✅' : gap < 0 ? '-₹${(-gap).toStringAsFixed(0)} 🔴' : '₹0 ⚠️',
                  style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w700,
                    color: gap > 0 ? AppColors.green : gap < 0 ? AppColors.red : AppColors.amber),
                ),
              ]),
            );
          }),
          Text(isMarathi ? '✅ = MSP वर  ⚠️ = MSP बरोबर  🔴 = MSP खाली' : '✅ = above MSP  ⚠️ = at MSP  🔴 = below MSP',
            style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
          const SizedBox(height: 20),

          // Alert preferences
          Text(isMarathi ? 'अलर्ट सेटिंग्स' : 'Alert Settings',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          ...[
            ('whatsapp', isMarathi ? 'WhatsApp अलर्ट रोज रात्री 8' : 'WhatsApp Alert 8 PM daily', isMarathi ? 'सोयाबीन, कापूस, हळद — सर्व 3 पिके' : 'Soybean, Cotton, Turmeric — all 3 crops'),
            ('sms', isMarathi ? 'आपत्कालीन RED SMS' : 'Emergency RED SMS', isMarathi ? 'RED अलर्ट लगेच SMS' : 'Instant SMS when RED alert fires'),
            ('voice', isMarathi ? 'मराठी आवाज अलर्ट' : 'Voice Alert Marathi', isMarathi ? 'रोज रात्री ८ वाजता बोलक्या मराठी अलर्ट' : 'Spoken Marathi alert at 8 PM'),
            ('chopal', isMarathi ? 'Community Chopal अलर्ट' : 'Community Chopal alerts', isMarathi ? 'जवळपासचे शेतकरी कथा शेअर करतात' : 'When nearby farmers share stories'),
            ('nafed', isMarathi ? 'NAFED साठा अलर्ट' : 'NAFED release alerts', isMarathi ? 'NAFED साठा बाजारात आल्यास लगेच' : 'Instant alert when NAFED releases stock'),
            ('export', isMarathi ? 'निर्यात बंदी अलर्ट' : 'Export ban alerts', isMarathi ? 'निर्यात बंदी जाहीर झाल्यास लगेच' : 'Immediate alert if export ban announced'),
          ].map((t) => Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(t.$2, style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary)),
                Text(t.$3, style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
              ])),
              Switch(
                value: _toggles[t.$1] ?? false,
                onChanged: (v) => setState(() => _toggles[t.$1] = v),
                activeTrackColor: AppColors.greenPale,
                activeThumbColor: AppColors.greenVivid,
              ),
            ]),
          )),
          const SizedBox(height: 20),

          // Language settings
          Text(isMarathi ? 'भाषा / Language' : 'Language',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          const SizedBox(height: 12),
          Container(
            decoration: BoxDecoration(color: surface, borderRadius: BorderRadius.circular(16)),
            padding: const EdgeInsets.all(6),
            child: Row(
              children: [
                Expanded(child: GestureDetector(
                  onTap: () => !widget.state.isMarathi ? widget.state.toggleLanguage() : null,
                  child: AnimatedContainer(duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    decoration: BoxDecoration(
                      color: widget.state.isMarathi ? AppColors.green : Colors.transparent,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    alignment: Alignment.center,
                    child: Text('🇮🇳 मराठी (Default)', style: GoogleFonts.workSans(fontSize: 15, fontWeight: FontWeight.w600,
                      color: widget.state.isMarathi ? Colors.white : textMuted)),
                  ),
                )),
                Expanded(child: GestureDetector(
                  onTap: () => widget.state.isMarathi ? widget.state.toggleLanguage() : null,
                  child: AnimatedContainer(duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    decoration: BoxDecoration(
                      color: !widget.state.isMarathi ? AppColors.green : Colors.transparent,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    alignment: Alignment.center,
                    child: Text('🇬🇧 English', style: GoogleFonts.workSans(fontSize: 15, fontWeight: FontWeight.w600,
                      color: !widget.state.isMarathi ? Colors.white : textMuted)),
                  ),
                )),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Voice AI demo
          Text(isMarathi ? 'आवाज AI' : 'Voice AI',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
          Text(isMarathi ? 'मराठी बोला, त्वरित उत्तर मिळवा' : 'Speak Marathi, get instant answers',
            style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
          const SizedBox(height: 16),
          Center(
            child: GestureDetector(
              onTap: widget.onOpenVoice,
              child: _PulsingMic(),
            ),
          ),
          const SizedBox(height: 4),
          Center(child: Text(isMarathi ? 'दाबा आणि विचारा' : 'Hold to speak',
            style: GoogleFonts.workSans(fontSize: 13, color: textMuted))),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8, runSpacing: 8,
            children: _sampleQuestions.map((q) => GestureDetector(
              onTap: () async {
                setState(() => _voiceAnswer =
                    widget.state.isMarathi
                        ? '⏳ Gemini AI उत्तर तयार करत आहे...'
                        : '⏳ Gemini AI is thinking...');
                final answer = await ApiService.getVoiceAnswer(q, widget.state.activeCrop);
                if (mounted) {
                  setState(() => _voiceAnswer = answer ??
                      (widget.state.isMarathi
                          ? 'माफ करा, उत्तर मिळाले नाही. पुन्हा प्रयत्न करा.'
                          : 'Sorry, no answer available. Please try again.'));
                }
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(q, style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w500, color: textPrimary)),
              ),
            )).toList(),
          ),
          if (_voiceAnswer != null) ...[
            const SizedBox(height: 16),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: MarathiAIBox(
                key: ValueKey(_voiceAnswer),
                marathiText: _voiceAnswer!,
                englishText: 'AI-generated answer in Marathi',
                isDark: isDark,
              ),
            ),
          ],
          const SizedBox(height: 20),

          // Community Chopal
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('Community Chopal', style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(border: Border.all(color: AppColors.greenVivid), borderRadius: BorderRadius.circular(999)),
              child: Text(isMarathi ? '+ कथा शेअर करा' : '+ Share your story',
                style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.green)),
            ),
          ]),
          const SizedBox(height: 12),
          ...widget.state.currentStories.map((s) => ChopalCard(
            initials: s.initials, avatarColor: s.avatarColor,
            nameEn: s.nameEn, distanceKm: s.distanceKm,
            messageMr: s.messageMr, messageEn: s.messageEn,
            isVerified: s.isVerified, verifiedDate: s.verifiedDate,
            crop: s.crop, saved: s.saved,
            isDark: isDark, isMarathi: isMarathi,
          )),

          // Verification explainer
          Container(
            margin: const EdgeInsets.only(bottom: 20),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: AppColors.bluePale, borderRadius: BorderRadius.circular(12)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(isMarathi ? 'पडताळणी कशी होते?' : 'How verification works?',
                style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.blueText)),
              const SizedBox(height: 8),
              ...['1. शेतकरी मंडीची पावती फोटो अपलोड करतो', '2. सिस्टम Agmarknet वर त्या दिवसाचा भाव तपासतो', '3. 10% आत असल्यास VERIFIED ✓ लावतो']
                  .map((s) => Padding(padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Text(s, style: GoogleFonts.workSans(fontSize: 12, color: AppColors.blueText)))),
            ]),
          ),

          // Project info
          AgronomistCard(
            isDark: isDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(isMarathi ? 'KisanAlert बद्दल' : 'About KisanAlert',
                  style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: textPrimary)),
                const SizedBox(height: 12),
                Text('Google Solution Challenge 2026',
                  style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
                const SizedBox(height: 8),
                // ⭐ Google brand badge — replaces self-rating
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF4285F4), Color(0xFF34A853)],
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.emoji_events, color: Colors.white, size: 20),
                    const SizedBox(width: 8),
                    Text(
                      isMarathi
                          ? 'Google Solution Challenge 2026\nTop 100 Global Selection'
                          : 'Google Solution Challenge 2026\nTop 100 Global Selection',
                      style: GoogleFonts.spaceGrotesk(
                          fontSize: 13, fontWeight: FontWeight.w700, color: Colors.white, height: 1.4),
                    ),
                  ]),
                ),
                const SizedBox(height: 12),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  '✦ Gemini AI', 'Flutter', 'Firebase', 'Cloud Run', 'Supabase', 'Open-Meteo'
                ].map((t) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: AppColors.purplePale, borderRadius: BorderRadius.circular(6)),
                  child: Text(t, style: GoogleFonts.workSans(fontSize: 10, fontWeight: FontWeight.w600, color: AppColors.purple)),
                )).toList()),
                const SizedBox(height: 8),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  '🎯 SDG 1', '🌾 SDG 2', '💼 SDG 8', '🌍 SDG 13'
                ].map((t) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: AppColors.greenPale, borderRadius: BorderRadius.circular(6)),
                  child: Text(t, style: GoogleFonts.workSans(fontSize: 10, fontWeight: FontWeight.w600, color: AppColors.greenText)),
                )).toList()),
                const SizedBox(height: 12),
                Text('Version 2.0.1 · April 2026 · 9 of 13 phases complete · AUC: 0.72',
                  style: GoogleFonts.jetBrainsMono(fontSize: 9, color: textMuted)),
                const SizedBox(height: 8),
                Text('Made with ❤️ in Nanded for farmers of Marathwada',
                  style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w500, color: textPrimary)),
                Text('2,706 farmer suicides in 2024. We are trying to change that.',
                  style: GoogleFonts.workSans(fontSize: 11, color: AppColors.red, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label, value;
  final Color bg, fg;
  final bool isDark;
  const _StatCard(this.label, this.value, this.bg, this.fg, this.isDark);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(value, style: GoogleFonts.spaceGrotesk(fontSize: 28, fontWeight: FontWeight.w800, color: fg)),
          Text(label, style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w500, color: fg.withValues(alpha: 0.8))),
        ],
      ),
    );
  }
}

class _PulsingMic extends StatefulWidget {
  @override
  State<_PulsingMic> createState() => _PulsingMicState();
}

class _PulsingMicState extends State<_PulsingMic> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _ring1, _ring2, _ring3;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 2000))..repeat();
    _ring1 = CurvedAnimation(parent: _ctrl, curve: const Interval(0.0, 0.6, curve: Curves.easeOut));
    _ring2 = CurvedAnimation(parent: _ctrl, curve: const Interval(0.2, 0.8, curve: Curves.easeOut));
    _ring3 = CurvedAnimation(parent: _ctrl, curve: const Interval(0.4, 1.0, curve: Curves.easeOut));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, child) {
        return SizedBox(
          width: 140, height: 140,
          child: Stack(alignment: Alignment.center, children: [
            for (final r in [(_ring1, 0.35), (_ring2, 0.20), (_ring3, 0.10)])
              Opacity(
                opacity: ((1 - r.$1.value) * r.$2 * 10).clamp(0.0, 1.0),
                child: Container(
                  width: 120 + r.$1.value * 40,
                  height: 120 + r.$1.value * 40,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.greenVivid.withValues(alpha: 0.15),
                  ),
                ),
              ),
            Container(
              width: 100, height: 100,
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [AppColors.green, AppColors.greenVivid]),
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: Color(0x6622C55E), blurRadius: 20, spreadRadius: 4)],
              ),
              child: const Icon(Icons.mic, color: Colors.white, size: 40),
            ),
          ]),
        );
      },
    );
  }
}
