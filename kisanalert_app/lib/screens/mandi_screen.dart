import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../data/app_data.dart';
import '../widgets/shared_widgets.dart';

class MandiScreen extends StatelessWidget {
  final AppState state;
  final Function(MandiData) onOpenMandi;

  const MandiScreen({super.key, required this.state, required this.onOpenMandi});

  @override
  Widget build(BuildContext context) {
    final isDark = state.isDark;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 120),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          // SVG Marathwada Map
          _MaratwaadaMap(isDark: isDark, state: state, onPinTap: onOpenMandi),
          const SizedBox(height: 16),

          // Crop filter
          _CropFilter(state: state, isDark: isDark),
          const SizedBox(height: 20),

          // Ranked mandi list
          Text(
            state.isMarathi ? 'आजचे सर्वोत्तम मंडी / Best Mandis Today' : 'Best Mandis Today',
            style: GoogleFonts.spaceGrotesk(fontSize: 16, fontWeight: FontWeight.w700, color: textPrimary),
          ),
          Text(
            state.isMarathi ? 'नफ्यानुसार क्रम' : 'Ranked by net profit after transport cost',
            style: GoogleFonts.workSans(fontSize: 12, color: textMuted),
          ),
          const SizedBox(height: 12),

          ...() {
            final sorted = [...state.currentMandis]
              ..sort((a, b) => b.priceForCrop(state.activeCrop).compareTo(a.priceForCrop(state.activeCrop)));
            final ranks = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣'];
            return sorted.asMap().entries.map((e) => MandiCard(
              rank: ranks[e.key],
              name: e.value.name,
              distanceKm: e.value.distanceKm,
              price: e.value.priceForCrop(state.activeCrop),
              signal: e.value.signal,
              weather: e.value.weather,
              advice: e.value.advice,
              isDark: isDark,
              activeCrop: state.activeCrop,
              isBest: e.value.isBest,
              onTap: () => onOpenMandi(e.value),
            ));
          }(),
          const SizedBox(height: 20),

          // Lead-Lag Alert Card
          AgronomistCard(
            isDark: isDark,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('📡 Lead-Lag Engine Active',
                  style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w700,
                    color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
                const SizedBox(height: 12),
                // Visual timeline
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.redPale, borderRadius: BorderRadius.circular(10),
                        ),
                        child: Column(
                          children: [
                            Text('Latur', style: GoogleFonts.spaceGrotesk(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.redText)),
                            Text('-12% आज', style: GoogleFonts.workSans(fontSize: 11, color: AppColors.redText)),
                          ],
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: Column(
                        children: [
                          Text('→→→', style: TextStyle(color: AppColors.amber, fontSize: 18, fontWeight: FontWeight.w700)),
                          Text('36 hrs', style: GoogleFonts.jetBrainsMono(fontSize: 9, color: textMuted)),
                        ],
                      ),
                    ),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.amberPale, borderRadius: BorderRadius.circular(10),
                        ),
                        child: Column(
                          children: [
                            Text('Nanded', style: GoogleFonts.spaceGrotesk(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.amberText)),
                            Text('-8% अपेक्षित', style: GoogleFonts.workSans(fontSize: 11, color: AppColors.amberText)),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  state.isMarathi
                      ? 'लातूरमध्ये आज ₹600 घसरले. नांदेडला ३६ तासात ₹400-500 पडण्याची शक्यता.'
                      : 'Latur fell ₹600 today. Nanded likely to drop ₹400-500 in 36 hours.',
                  style: GoogleFonts.workSans(fontSize: 16, fontWeight: FontWeight.w500,
                    color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary, height: 1.5),
                ),
                const SizedBox(height: 12),
                GestureDetector(
                  onTap: () {},
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(colors: [AppColors.amber, AppColors.amberVivid]),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      state.isMarathi ? 'आत्ताच उस्मानाबादला विका' : 'Sell at Osmanabad NOW',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // MSP Procurement centers (shown when price < MSP — example for Turmeric)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.bluePale,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  state.isMarathi ? 'MSP खरेदी केंद्रे जवळपास' : 'MSP Procurement Centers Nearby',
                  style: GoogleFonts.spaceGrotesk(fontSize: 14, fontWeight: FontWeight.w700, color: AppColors.blueText),
                ),
                Text(
                  state.isMarathi ? 'सरकारला MSP वर खरेदी करणे बंधनकारक आहे'
                      : 'Government must buy at MSP',
                  style: GoogleFonts.workSans(fontSize: 12, color: AppColors.blueText),
                ),
                const SizedBox(height: 10),
                ...['NAFED Nanded · 📞 02462-281234', 'APMC Biloli · 📞 02461-222345', 'NAFED Hingoli · 📞 02456-234123']
                    .map((c) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Text(c, style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w500, color: AppColors.blueText)),
                        )),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MaratwaadaMap extends StatelessWidget {
  final bool isDark;
  final AppState state;
  final Function(MandiData) onPinTap;

  const _MaratwaadaMap({required this.isDark, required this.state, required this.onPinTap});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 300,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1A1A12) : const Color(0xFFF9F4E8),
        borderRadius: BorderRadius.circular(20),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: CustomPaint(
          painter: _MapPainter(isDark: isDark, activeCrop: state.activeCrop),
          child: Stack(
            children: [
              // Pin overlays
              ..._buildPins(context),
            ],
          ),
        ),
      ),
    );
  }

  List<Widget> _buildPins(BuildContext context) {
    MandiData? find(String name) {
      try { return state.currentMandis.firstWhere((m) => m.name == name); }
      catch (_) { return null; }
    }

    final pins = [
      (0.5, 0.52, 'Nanded', '₹5,352', 'AMBER', find('Nanded')),
      (0.35, 0.38, 'Osmanabad', '₹5,200', 'GREEN', find('Osmanabad')),
      (0.30, 0.65, 'Latur', '₹5,050', 'GREEN', find('Latur')),
      (0.57, 0.32, 'Parbhani', '₹4,400', 'RED', find('Parbhani')),
      (0.22, 0.28, 'Beed', '₹4,980', 'GREEN', find('Beed')),
      (0.65, 0.63, 'Hingoli', '₹4,700', 'AMBER', find('Hingoli')),
      (0.76, 0.40, 'Jalna', '₹4,820', 'GREEN', find('Jalna')),
      (0.80, 0.72, 'Sambhajinagar', '₹4,550', 'AMBER', find('Sambhajinagar')),
    ];

    return pins.map((p) {
    final priceStr = p.$6 != null
        ? '₹${p.$6!.priceForCrop(state.activeCrop).toStringAsFixed(0)}'
        : '—';  // Show dash, never fake data
      final signalStr = p.$6?.signal ?? 'NONE';  // NONE = grey, no hardcoded colour
      final isBest = p.$6 != null && p.$6!.isBest;
      final color = signalStr == 'GREEN' ? AppColors.greenVivid
          : signalStr == 'RED' ? AppColors.redVivid
          : signalStr == 'AMBER' ? AppColors.amberVivid
          : AppColors.textMuted;  // Grey when no live data

      return Positioned(
        left: p.$1 * 370 - 30,
        top: p.$2 * 280 - 30,
        child: GestureDetector(
          onTap: p.$6 != null ? () => onPinTap(p.$6!) : null,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: p.$1 == 0.5 ? 20 : 14,
                height: p.$1 == 0.5 ? 20 : 14,
                decoration: BoxDecoration(
                  color: color, shape: BoxShape.circle,
                  boxShadow: [BoxShadow(color: color.withValues(alpha: 0.5), blurRadius: 8, spreadRadius: 2)],
                ),
              ),
              Container(
                margin: const EdgeInsets.only(top: 3),
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
                decoration: BoxDecoration(
                  color: (isDark ? Colors.black : Colors.white).withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text(p.$3 + (isBest ? ' BEST⭐' : ''), style: GoogleFonts.spaceGrotesk(fontSize: 8, fontWeight: FontWeight.w700,
                    color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
                  Text(priceStr, style: GoogleFonts.jetBrainsMono(fontSize: 7,
                    color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
                ]),
              ),
            ],
          ),
        ),
      );
    }).toList();
  }
}

class _MapPainter extends CustomPainter {
  final bool isDark;
  final String activeCrop;
  _MapPainter({required this.isDark, required this.activeCrop});

  @override
  void paint(Canvas canvas, Size size) {
    // Distance rings
    final ringPaint = Paint()
      ..color = AppColors.green.withValues(alpha: 0.12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;
    final center = Offset(size.width * 0.5, size.height * 0.52);
    canvas.drawCircle(center, size.width * 0.22, ringPaint..color = AppColors.green.withValues(alpha: 0.15));
    canvas.drawCircle(center, size.width * 0.40, ringPaint..color = AppColors.green.withValues(alpha: 0.08));

    // Dashed road lines
    final roads = [
      [center, Offset(size.width * 0.35, size.height * 0.38)],
      [center, Offset(size.width * 0.30, size.height * 0.65)],
      [center, Offset(size.width * 0.57, size.height * 0.32)],
      [center, Offset(size.width * 0.22, size.height * 0.28)],
      [center, Offset(size.width * 0.65, size.height * 0.63)],
    ];
    final roadPaint = Paint()
      ..color = AppColors.green.withValues(alpha: 0.20)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;
    for (final r in roads) {
      canvas.drawLine(r[0], r[1], roadPaint);
    }
  }

  @override
  bool shouldRepaint(_MapPainter old) => old.activeCrop != activeCrop;
}

class _CropFilter extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _CropFilter({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final crops = [('Soybean', '🌱', 'सोयाबीन'), ('Cotton', '🌿', 'कापूस'), ('Turmeric', '🌾', 'हळद')];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          ...crops.map((c) {
            final isActive = state.activeCrop == c.$1;
            return GestureDetector(
              onTap: () => state.setActiveCrop(c.$1),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: const EdgeInsets.only(right: 8),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: isActive ? AppColors.green : (isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text('${c.$2} ${state.isMarathi ? c.$3 : c.$1}',
                  style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600,
                    color: isActive ? Colors.white : (isDark ? AppColors.darkTextSecondary : AppColors.textMuted))),
              ),
            );
          }),
          GestureDetector(
            onTap: () {},
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text('📊 All', style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600,
                color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
            ),
          ),
        ],
      ),
    );
  }
}
