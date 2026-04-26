import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../data/app_data.dart';
import '../widgets/shared_widgets.dart';
import 'package:flutter/foundation.dart';
import 'package:record/record.dart';
import 'package:http/http.dart' as http;
import 'dart:io';

// ───────────────────────────────────────────────────────────────────
// MODAL 1 — Voice AI Full-Screen Overlay
// ───────────────────────────────────────────────────────────────────
class VoiceModal extends StatefulWidget {
  final bool isDark;
  final bool isMarathi;
  final String activeCrop;
  final VoidCallback onClose;

  const VoiceModal({
    super.key,
    required this.isDark,
    required this.isMarathi,
    required this.activeCrop,
    required this.onClose,
  });

  @override
  State<VoiceModal> createState() => _VoiceModalState();
}

class _VoiceModalState extends State<VoiceModal> with TickerProviderStateMixin {
  String _state = 'idle'; // idle, listening, responding
  String? _answer;
  late AnimationController _rippleCtrl;

  final AudioRecorder _recorder = AudioRecorder();
  bool _isRecording = false;
  String _statusText = '';

  final _answers = {
    'आज सर्वोत्तम मंडी कुठे?': 'आज सोयाबीनसाठी उस्मानाबाद सर्वोत्तम आहे — ₹5,200 मिळतो, नांदेडपेक्षा ₹398 जास्त. ट्रक खर्च ₹900 धरला तरी फायदा होतो.',
    'सोयाबीन कधी विकायचे?': 'सध्या RED अलर्ट आहे. कृपया मंगळवारपर्यंत थांबा — ₹5,600 पर्यंत जाण्याची शक्यता आहे.',
    'MSP किती आहे?': 'सोयाबीन MSP: ₹4,892. आजचा भाव ₹5,352 — MSP पेक्षा ₹460 जास्त. सध्या सुरक्षित क्षेत्रात आहात.',
    'पाऊस कधी येणार?': 'आज रात्री नांदेडला 22mm पाऊस. उद्या हलका. गुरुवार ते रविवार स्वच्छ आकाश.',
    'NAFED साठा का पडतो?': 'NAFED सरकारच्या वतीने साठा सोडतो. याने पुरवठा वाढतो, भाव पडतो.',
  };

  @override
  void initState() {
    super.initState();
    _rippleCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500))..repeat();
    _initSpeech();
  }

  void _initSpeech() async {
    // Permission handled during recording start
  }

  @override
  void dispose() {
    _rippleCtrl.dispose();
    super.dispose();
  }

  void _startRecording() async {
    try {
      if (await _recorder.hasPermission()) {
        // Use default config, record package handles platform-specific defaults
        const config = RecordConfig();
        
        await _recorder.start(config, path: '');
        
        setState(() {
          _state = 'listening';
          _isRecording = true;
          _answer = null;
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(widget.isMarathi ? 'कृपया मायक्रोफोन परवानगी द्या' : 'Please allow microphone access')),
          );
        }
      }
    } catch (e) {
      print("Start recording failed: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(widget.isMarathi ? 'रेकॉर्डिंग सुरू करता आले नाही' : 'Could not start recording')),
        );
      }
    }
  }

  void _stopRecording() async {
    try {
      final path = await _recorder.stop();
      setState(() { 
        _state = 'responding'; 
        _isRecording = false;
      });

      if (path != null) {
        Uint8List audioBytes;
        if (kIsWeb) {
          // On web, path is a blob URL
          final response = await http.get(Uri.parse(path));
          audioBytes = response.bodyBytes;
        } else {
          // On mobile, path is a local file path
          audioBytes = await File(path).readAsBytes();
        }
        
        _uploadAudio(audioBytes);
      } else {
        setState(() { _state = 'idle'; });
      }
    } catch (e) {
      print("Stop recording failed: $e");
      setState(() { _state = 'idle'; });
    }
  }

  void _uploadAudio(Uint8List bytes) async {
    try {
      final response = await ApiService.uploadVoiceAudio(
        bytes, 
        kIsWeb ? "voice.webm" : "voice.m4a",
        widget.activeCrop,
        "Nanded" // Defaulting as per point 2 ignore
      );
      
      if (mounted) {
        setState(() {
          _answer = response ?? (widget.isMarathi ? "क्षमस्व, मला उत्तर मिळाले नाही." : "Sorry, I couldn't get an answer.");
          _state = 'idle';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _answer = widget.isMarathi ? "काहीतरी चूक झाली. पुन्हा प्रयत्न करा." : "Something went wrong. Try again.";
          _state = 'idle';
        });
      }
    }
  }

  void _processQuery(String query) async {
    setState(() { _state = 'responding'; _answer = null; });
    
    try {
      final response = await ApiService.getVoiceAnswer(query, widget.activeCrop);
      if (mounted) {
        setState(() {
          _answer = response ?? (widget.isMarathi ? "क्षमस्व, मला उत्तर मिळाले नाही." : "Sorry, I couldn't get an answer.");
          _state = 'idle';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _answer = widget.isMarathi ? "काहीतरी चूक झाली. पुन्हा प्रयत्न करा." : "Something went wrong. Try again.";
          _state = 'idle';
        });
      }
    }
  }

  void _askQuestion(String q) {
    _processQuery(q);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final isMarathi = widget.isMarathi;
    final bg = isDark ? AppColors.darkPageBg.withValues(alpha: 0.97) : const Color(0xFF101010).withValues(alpha: 0.95);
    final textPrimary = Colors.white;
    final textMuted = Colors.white.withValues(alpha: 0.6);

    return Material(
      color: Colors.transparent,
      child: GestureDetector(
        onVerticalDragEnd: (d) { if (d.velocity.pixelsPerSecond.dy > 400) widget.onClose(); },
        child: Container(
          color: bg,
          child: SafeArea(
            child: Column(
              children: [
                // Close bar
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(isMarathi ? 'आवाज AI' : 'Voice AI',
                        style: GoogleFonts.spaceGrotesk(fontSize: 20, fontWeight: FontWeight.w700, color: textPrimary)),
                      GestureDetector(
                        onTap: widget.onClose,
                        child: Container(
                          width: 40, height: 40,
                          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.15), shape: BoxShape.circle),
                          child: const Icon(Icons.close, color: Colors.white),
                        ),
                      ),
                    ],
                  ),
                ),

                Expanded(
                  child: SingleChildScrollView(
                    child: Column(
                      children: [
                        const SizedBox(height: 20),
                        // State indicator
                        Text(
                          _state == 'listening'
                              ? (isMarathi ? 'ऐकत आहे...' : 'Listening...')
                              : _state == 'responding'
                                  ? (isMarathi ? 'उत्तर देत आहे...' : 'Responding...')
                                  : (isMarathi ? 'बोला... / Speak Marathi...' : 'Speak Marathi...'),
                          style: GoogleFonts.workSans(fontSize: 18, fontWeight: FontWeight.w500, color: textPrimary),
                        ),
                        if (_state == 'idle')
                          Text(isMarathi ? 'बटण दाबा आणि प्रश्न विचारा' : 'Hold button and ask your question',
                            style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
                        const SizedBox(height: 40),

                        // Mic button
                        GestureDetector(
                          onTap: _state == 'idle' ? _startRecording : _stopRecording,
                          child: AnimatedBuilder(
                            animation: _rippleCtrl,
                            builder: (_, child) {
                              final isActive = _state == 'listening';
                              return SizedBox(
                                width: 180, height: 180,
                                child: Stack(alignment: Alignment.center, children: [
                                  if (isActive) ...[
                                    for (int i = 0; i < 3; i++)
                                      Opacity(
                                        opacity: ((1 - (_rippleCtrl.value + i * 0.33) % 1.0)) * 0.4,
                                        child: Container(
                                          width: 140 + ((_rippleCtrl.value + i * 0.33) % 1.0) * 60,
                                          height: 140 + ((_rippleCtrl.value + i * 0.33) % 1.0) * 60,
                                          decoration: BoxDecoration(
                                            shape: BoxShape.circle,
                                            color: AppColors.greenVivid.withValues(alpha: 0.3),
                                          ),
                                        ),
                                      ),
                                  ],
                                  Container(
                                    width: 140, height: 140,
                                    decoration: BoxDecoration(
                                      gradient: LinearGradient(
                                        colors: isActive
                                            ? [AppColors.greenVivid, AppColors.greenLight]
                                            : [AppColors.green, AppColors.greenVivid],
                                      ),
                                      shape: BoxShape.circle,
                                      boxShadow: [BoxShadow(color: AppColors.green.withValues(alpha: 0.4), blurRadius: 30, spreadRadius: 5)],
                                    ),
                                    child: Icon(
                                      isActive ? Icons.graphic_eq : Icons.mic,
                                      color: Colors.white,
                                      size: 56,
                                    ),
                                  ),
                                ]),
                              );
                            },
                          ),
                        ),
                        if (_state == 'listening')
                          Padding(
                            padding: const EdgeInsets.only(top: 10),
                            child: Text(
                              isMarathi ? 'आवाज रेकॉर्ड होत आहे...' : 'Recording your voice...',
                              style: GoogleFonts.workSans(color: AppColors.greenVivid, fontSize: 16, fontStyle: FontStyle.italic),
                            ),
                          ),
                        const SizedBox(height: 32),

                        // Sample questions
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 20),
                          child: Wrap(
                            spacing: 8, runSpacing: 8, alignment: WrapAlignment.center,
                            children: [
                              'आज सर्वोत्तम मंडी कुठे?',
                              'सोयाबीन कधी विकायचे?',
                              'MSP किती आहे?',
                              'पाऊस कधी येणार?',
                              'NAFED साठा का पडतो?',
                            ].map((q) => GestureDetector(
                              onTap: () => _askQuestion(q),
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.10),
                                  borderRadius: BorderRadius.circular(999),
                                  border: Border.all(color: Colors.white.withValues(alpha: 0.20)),
                                ),
                                child: Text(q, style: GoogleFonts.workSans(fontSize: 13, color: textPrimary)),
                              ),
                            )).toList(),
                          ),
                        ),

                        // Response card
                        if (_answer != null) ...[
                          const SizedBox(height: 24),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 20),
                            child: AnimatedSwitcher(
                              duration: const Duration(milliseconds: 400),
                              child: Container(
                                key: ValueKey(_answer),
                                padding: const EdgeInsets.all(20),
                                decoration: BoxDecoration(
                                  color: Colors.white.withValues(alpha: 0.10),
                                  borderRadius: BorderRadius.circular(16),
                                  border: const Border(left: BorderSide(color: AppColors.greenVivid, width: 3)),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(children: [
                                      Text('✦ Gemini AI', style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.purplePale)),
                                    ]),
                                    const SizedBox(height: 10),
                                    Text(_answer!, style: GoogleFonts.workSans(fontSize: 17, fontWeight: FontWeight.w500, color: textPrimary, height: 1.6)),
                                    const SizedBox(height: 12),
                                    GestureDetector(
                                      onTap: () => setState(() { _answer = null; }),
                                      child: Text(isMarathi ? 'आणखी विचारा →' : 'Ask another →',
                                        style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.greenLight)),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                        if (_state == 'responding') ...[
                          const SizedBox(height: 24),
                          const CircularProgressIndicator(color: AppColors.greenVivid, strokeWidth: 2),
                        ],
                        const SizedBox(height: 40),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ───────────────────────────────────────────────────────────────────
// MODAL 2 — Mandi Detail Bottom Sheet
// ───────────────────────────────────────────────────────────────────
class MandiDetailSheet extends StatelessWidget {
  final MandiData mandi;
  final bool isDark;
  final bool isMarathi;
  final String activeCrop;
  final VoidCallback onClose;

  const MandiDetailSheet({
    super.key,
    required this.mandi,
    required this.isDark,
    required this.isMarathi,
    required this.activeCrop,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final price = mandi.priceForCrop(activeCrop);
    final nandedPrice = activeCrop == 'Cotton' ? 7845.0 : activeCrop == 'Turmeric' ? 12000.0 : 5352.0;
    final transport = mandi.distanceKm * 10.0;
    final netGain = price - nandedPrice - transport;

    return Container(
      height: MediaQuery.of(context).size.height * 0.80,
      decoration: BoxDecoration(
        color: surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Handle
          const SizedBox(height: 12),
          Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh, borderRadius: BorderRadius.circular(999)))),
          const SizedBox(height: 16),

          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(mandi.name, style: GoogleFonts.spaceGrotesk(fontSize: 24, fontWeight: FontWeight.w700, color: textPrimary)),
                      Text('${mandi.distanceKm}km ${isMarathi ? "नांदेडपासून" : "from Nanded"}',
                        style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
                    ],
                  ),
                ),
                SizedBox(
                  width: 100,
                  child: AlertBadge(
                    level: mandi.signal,
                    label: mandi.signal == 'BLUE' ? 'HOLD' : mandi.signal,
                    isDark: isDark,
                  ),
                ),
                const SizedBox(width: 12),
                GestureDetector(onTap: onClose, child: Icon(Icons.close, color: textMuted)),
              ],
            ),
          ),
          const SizedBox(height: 20),

          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                children: [
                  // Data tiles grid
                  GridView.count(
                    crossAxisCount: 2, shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisSpacing: 8, mainAxisSpacing: 8,
                    childAspectRatio: 2.0,
                    children: [
                      _DataTile(isMarathi ? 'आजचा भाव' : '$activeCrop today', '₹${price.toStringAsFixed(0)}/qtl', isDark),
                      _DataTile(isMarathi ? 'MSP तुलना' : 'vs MSP', '+₹${(price - (activeCrop == "Cotton" ? 7121 : activeCrop == "Turmeric" ? 12000 : 4892)).toStringAsFixed(0)} ✅', isDark),
                      _DataTile(isMarathi ? 'आजची आवक' : 'Arrivals today', '1,240 qtl (सामान्य)', isDark),
                      _DataTile(isMarathi ? 'अंतर' : 'Distance', '${mandi.distanceKm}km · ~${(mandi.distanceKm / 60).toStringAsFixed(1)}hr', isDark),
                      _DataTile(isMarathi ? 'हवामान' : 'Weather', mandi.weather, isDark),
                      _DataTile(isMarathi ? 'Lead-lag' : 'Lead-lag signal', '✓ No wave incoming', isDark),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Decision card
                  AgronomistCard(
                    isDark: isDark,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        AlertBadge(
                          level: mandi.signal,
                          label: mandi.signal == 'GREEN'
                              ? (isMarathi ? '✅ GREEN — इथे विकणे सर्वोत्तम' : '✅ GREEN — Best day to sell here')
                              : mandi.signal == 'BLUE'
                                  ? (isMarathi ? '🔵 BLUE — थांबा, भाव वाढणार' : '🔵 BLUE — Hold & wait')
                                  : mandi.signal == 'RED'
                                      ? (isMarathi ? '🚨 RED — टाळा' : '🚨 RED — Avoid')
                                      : (isMarathi ? '⚠️ AMBER — भाव स्थिर' : '⚠️ AMBER — Farmer\'s choice'),
                          isDark: isDark,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          isMarathi
                              ? 'आज सोयाबीन ${mandi.name} ला विका! नांदेडपेक्षा ₹${(price - nandedPrice).abs().toStringAsFixed(0)} ${price > nandedPrice ? "जास्त" : "कमी"} भाव आहे.'
                              : 'Sell at ${mandi.name} today. ₹${(price - nandedPrice).abs().toStringAsFixed(0)} ${price > nandedPrice ? "more" : "less"} than Nanded.',
                          style: GoogleFonts.workSans(fontSize: 16, fontWeight: FontWeight.w500,
                            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary, height: 1.5),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Transport calculator
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(isMarathi ? 'वाहतूक खर्च' : 'Transport Calculator',
                          style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700,
                            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary)),
                        const SizedBox(height: 8),
                        Text(isMarathi ? '~₹${transport.toStringAsFixed(0)} (२० क्विंटल ट्रक)' : '~₹${transport.toStringAsFixed(0)} for 20 quintals truck',
                          style: GoogleFonts.workSans(fontSize: 13, color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
                        const SizedBox(height: 4),
                        Text(
                          netGain >= 0
                              ? '+₹${netGain.toStringAsFixed(0)} ${isMarathi ? "प्रति क्विंटल निव्वळ नफा" : "per quintal net after truck"}'
                              : '-₹${(-netGain).toStringAsFixed(0)} ${isMarathi ? "तोटा (दूर जाण्यात अर्थ नाही)" : "loss (not worth going)"}',
                          style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w700,
                            color: netGain >= 0 ? AppColors.green : AppColors.red),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Action buttons
                  GestureDetector(
                    onTap: () {},
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(colors: [AppColors.green, AppColors.greenVivid]),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(isMarathi ? '🗺️ Google Maps वर दिशा मिळवा' : '🗺️ Get Directions (Google Maps)',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white)),
                    ),
                  ),
                  const SizedBox(height: 10),
                  GestureDetector(
                    onTap: () {},
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      decoration: BoxDecoration(
                        border: Border.all(color: AppColors.greenVivid),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(isMarathi ? '📤 ही माहिती शेअर करा' : '📤 Share this info',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.green)),
                    ),
                  ),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DataTile extends StatelessWidget {
  final String label, value;
  final bool isDark;
  const _DataTile(this.label, this.value, this.isDark);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(label, style: GoogleFonts.workSans(fontSize: 11,
            color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted)),
          const SizedBox(height: 2),
          Text(value, style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600,
            color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary), overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

// ───────────────────────────────────────────────────────────────────
// MODAL 3 — Signal Explanation Bottom Sheet
// ───────────────────────────────────────────────────────────────────
class SignalModal extends StatelessWidget {
  final Signal signal;
  final bool isDark;
  final bool isMarathi;
  final VoidCallback onClose;

  const SignalModal({
    super.key,
    required this.signal,
    required this.isDark,
    required this.isMarathi,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(child: Container(width: 40, height: 4,
            decoration: BoxDecoration(color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh, borderRadius: BorderRadius.circular(999)))),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(child: Text(signal.label,
                style: GoogleFonts.spaceGrotesk(fontSize: 18, fontWeight: FontWeight.w700, color: textPrimary))),
              GestureDetector(onTap: onClose, child: Icon(Icons.close, color: textMuted)),
            ],
          ),
          const SizedBox(height: 12),
          SignalChip(label: signal.level, level: signal.level, isDark: isDark),
          const SizedBox(height: 16),
          Text(isMarathi ? signal.marathi : signal.explanation,
            style: GoogleFonts.workSans(fontSize: 16, fontWeight: FontWeight.w500, height: 1.6,
              color: textPrimary)),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              isMarathi
                  ? 'ऐतिहासिक: हे संकेत सप्टेंबर 2025 मध्ये आले होते → 2 दिवसांनी भाव पडला'
                  : 'Historical: This signal fired Sep 2025 → price crashed 2 days later',
              style: GoogleFonts.workSans(fontSize: 13, color: textMuted),
            ),
          ),
          const SizedBox(height: 20),
          GestureDetector(
            onTap: onClose,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 14),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(isMarathi ? 'बंद करा' : 'Close', textAlign: TextAlign.center,
                style: GoogleFonts.workSans(fontSize: 14, fontWeight: FontWeight.w600, color: textPrimary)),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}
