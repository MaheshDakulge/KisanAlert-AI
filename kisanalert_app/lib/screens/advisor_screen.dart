// lib/screens/advisor_screen.dart
// ⭐ STAR FEATURE: Gemini AI Advisor — Powered by Gemini 2.0 Flash
// Full-screen AI briefing + Marathi chat for farmers

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/app_theme.dart';
import '../state/app_state.dart';
import '../data/app_data.dart';

class AdvisorScreen extends StatefulWidget {
  final AppState state;
  const AdvisorScreen({super.key, required this.state});

  @override
  State<AdvisorScreen> createState() => _AdvisorScreenState();
}

class _AdvisorScreenState extends State<AdvisorScreen> with SingleTickerProviderStateMixin {
  Map<String, dynamic>? _advisory;
  bool _loading = true;
  String? _error;

  // Chat state
  final TextEditingController _chatCtrl = TextEditingController();
  final ScrollController _chatScroll = ScrollController();
  final List<_ChatMsg> _messages = [];
  bool _chatLoading = false;

  late AnimationController _pulseCtrl;
  late Animation<double> _pulse;

  // Pre-set question chips
  final List<String> _chips = [
    'सोयाबीन विकू का?',
    'MSP किती आहे?',
    'NCDEX काय म्हणते?',
    '४८ तासात काय होईल?',
    'जवळची मंडी कुठे?',
  ];

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1600))..repeat(reverse: true);
    _pulse = Tween(begin: 0.97, end: 1.03).animate(CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut));
    _loadAdvisory();
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    _chatCtrl.dispose();
    _chatScroll.dispose();
    super.dispose();
  }

  Future<void> _loadAdvisory() async {
    setState(() { _loading = true; _error = null; });
    final data = await ApiService.getGeminiAdvisory(widget.state.activeCrop);
    if (mounted) {
      setState(() {
        _advisory = data;
        _loading = false;
        if (data == null) _error = 'Unable to load advisory. Check connection.';
      });
    }
  }

  Future<void> _sendChat(String query) async {
    if (query.trim().isEmpty) return;
    _chatCtrl.clear();
    setState(() {
      _messages.add(_ChatMsg(text: query, isUser: true));
      _chatLoading = true;
    });
    _scrollToBottom();

    final ans = await ApiService.getVoiceAnswer(query, widget.state.activeCrop);
    if (mounted) {
      setState(() {
        _messages.add(_ChatMsg(
          text: ans ?? 'माफ करा, उत्तर मिळाले नाही. पुन्हा प्रयत्न करा.',
          isUser: false,
        ));
        _chatLoading = false;
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_chatScroll.hasClients) {
        _chatScroll.animateTo(_chatScroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  @override
  void didUpdateWidget(AdvisorScreen old) {
    super.didUpdateWidget(old);
    if (old.state.activeCrop != widget.state.activeCrop) {
      _messages.clear();
      _loadAdvisory();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final isMarathi = widget.state.isMarathi;
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return Column(
      children: [
        Expanded(
          child: _loading
              ? _buildLoading(isDark, isMarathi)
              : _error != null
                  ? _buildError(isDark, isMarathi)
                  : _buildContent(isDark, isMarathi, surface, textPrimary, textMuted),
        ),
        _buildChatInput(isDark, isMarathi, textMuted),
      ],
    );
  }

  Widget _buildLoading(bool isDark, bool isMarathi) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AnimatedBuilder(
            animation: _pulse,
            builder: (_, child) => Transform.scale(scale: _pulse.value, child: child),
            child: Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF4285F4), Color(0xFF0F9D58)]),
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: const Color(0xFF4285F4).withValues(alpha: 0.4), blurRadius: 20, spreadRadius: 4)],
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 36),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            isMarathi ? 'Gemini AI विश्लेषण करत आहे...' : 'Gemini AI analyzing market...',
            style: GoogleFonts.spaceGrotesk(fontSize: 15, fontWeight: FontWeight.w600,
                color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary),
          ),
          const SizedBox(height: 8),
          Text(
            isMarathi ? 'NCDEX + Agmarknet + AI मॉडेल' : 'NCDEX + Agmarknet + AI Model',
            style: GoogleFonts.workSans(fontSize: 12, color: isDark ? AppColors.darkTextSecondary : AppColors.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _buildError(bool isDark, bool isMarathi) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text('⚠️', style: TextStyle(fontSize: 48)),
          const SizedBox(height: 12),
          Text(_error ?? '', style: GoogleFonts.workSans(color: AppColors.amber)),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _loadAdvisory,
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.green),
            child: Text(isMarathi ? 'पुन्हा प्रयत्न करा' : 'Retry',
                style: const TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(bool isDark, bool isMarathi, Color surface, Color textPrimary, Color textMuted) {
    final adv = _advisory!;
    final level = (adv['alert_level'] ?? 'AMBER') as String;
    final emoji = (adv['signal_emoji'] ?? '⚠️') as String;
    final source = (adv['source'] ?? 'gemini') as String;
    final price = (adv['price'] as num?)?.toDouble() ?? 0.0;
    final isGemini = source.contains('gemini');
    final levelColor = _levelColor(level, isDark);

    return RefreshIndicator(
      color: AppColors.green,
      onRefresh: _loadAdvisory,
      child: ListView(
        controller: _chatScroll,
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
        children: [
          // ── Gemini Powered Badge ──────────────────────────────────
          Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF4285F4), Color(0xFF0F9D58), Color(0xFFF4B400)]),
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.auto_awesome, color: Colors.white, size: 14),
                  const SizedBox(width: 6),
                  Text(
                    isGemini ? 'Powered by Google Gemini 2.0 Flash' : 'KisanAlert AI Advisor',
                    style: GoogleFonts.workSans(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.white),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),

          // ── Signal Hero Card ──────────────────────────────────────
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurfaceRaised : AppColors.surface,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: levelColor, width: 2.5),
              boxShadow: [BoxShadow(color: levelColor.withValues(alpha: 0.2), blurRadius: 20, offset: const Offset(0, 4))],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Text(emoji, style: const TextStyle(fontSize: 32)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isMarathi ? 'आजचा AI सल्ला' : 'Today\'s AI Advisory',
                        style: GoogleFonts.workSans(fontSize: 11, color: textMuted),
                      ),
                      Text(
                        _levelLabel(level, isMarathi),
                        style: GoogleFonts.spaceGrotesk(fontSize: 22, fontWeight: FontWeight.w800, color: levelColor),
                      ),
                    ],
                  )),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: levelColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
                    child: Text('₹${price.toStringAsFixed(0)}',
                        style: GoogleFonts.jetBrainsMono(fontSize: 16, fontWeight: FontWeight.w800, color: levelColor)),
                  ),
                ]),
                const SizedBox(height: 14),
                Text(
                  adv['decision'] ?? '',
                  style: GoogleFonts.workSans(fontSize: 16, fontWeight: FontWeight.w600, color: textPrimary, height: 1.5),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // ── 3 Briefing Cards ──────────────────────────────────────
          _BriefingCard(
            icon: '📊',
            title: isMarathi ? 'बाजाराचा कल' : 'Market Trend',
            body: adv['trend'] ?? '',
            color: AppColors.blue,
            isDark: isDark,
          ),
          const SizedBox(height: 10),
          _BriefingCard(
            icon: '📈',
            title: isMarathi ? 'NCDEX वायदे vs स्थानिक' : 'NCDEX Futures vs Local Mandi',
            body: adv['ncdex'] ?? '',
            color: AppColors.amber,
            isDark: isDark,
          ),
          const SizedBox(height: 10),
          _BriefingCard(
            icon: '💰',
            title: isMarathi ? 'नफ्याचा सल्ला' : 'Profit Tip',
            body: adv['profit_tip'] ?? '',
            color: AppColors.green,
            isDark: isDark,
          ),
          const SizedBox(height: 20),

          // ── Quick Question Chips ──────────────────────────────────
          Text(
            isMarathi ? 'पटकन विचारा:' : 'Quick questions:',
            style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: textMuted),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _chips.map((chip) => GestureDetector(
              onTap: () => _sendChat(chip),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.green.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: AppColors.green.withValues(alpha: 0.4)),
                ),
                child: Text(chip, style: GoogleFonts.workSans(fontSize: 13, color: AppColors.green, fontWeight: FontWeight.w600)),
              ),
            )).toList(),
          ),
          const SizedBox(height: 20),

          // ── Chat History ──────────────────────────────────────────
          if (_messages.isNotEmpty) ...[
            Text(
              isMarathi ? 'संवाद:' : 'Conversation:',
              style: GoogleFonts.workSans(fontSize: 13, fontWeight: FontWeight.w600, color: textMuted),
            ),
            const SizedBox(height: 8),
            ..._messages.map((m) => _ChatBubble(msg: m, isDark: isDark)),
            if (_chatLoading)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(children: [
                  Container(
                    width: 8, height: 8,
                    decoration: const BoxDecoration(color: AppColors.green, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    isMarathi ? 'Gemini उत्तर देत आहे...' : 'Gemini is thinking...',
                    style: GoogleFonts.workSans(fontSize: 12, color: AppColors.green),
                  ),
                ]),
              ),
          ],
          const SizedBox(height: 80),
        ],
      ),
    );
  }

  Widget _buildChatInput(bool isDark, bool isMarathi, Color textMuted) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    return Container(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 10,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      decoration: BoxDecoration(
        color: surface,
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 12, offset: const Offset(0, -4))],
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceRaised,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.green.withValues(alpha: 0.3)),
              ),
              child: TextField(
                controller: _chatCtrl,
                style: GoogleFonts.workSans(fontSize: 14, color: isDark ? AppColors.darkTextPrimary : AppColors.textPrimary),
                decoration: InputDecoration(
                  hintText: isMarathi ? 'प्रश्न विचारा (मराठी / English)...' : 'Ask anything in Marathi or English...',
                  hintStyle: GoogleFonts.workSans(fontSize: 13, color: textMuted),
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.symmetric(vertical: 12),
                ),
                onSubmitted: _sendChat,
                textInputAction: TextInputAction.send,
              ),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: () => _sendChat(_chatCtrl.text),
            child: Container(
              width: 46, height: 46,
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [AppColors.green, AppColors.greenVivid]),
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: AppColors.green.withValues(alpha: 0.4), blurRadius: 12, offset: const Offset(0, 4))],
              ),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }

  Color _levelColor(String level, bool isDark) {
    switch (level) {
      case 'RED': return isDark ? AppColors.darkRedLight : AppColors.red;
      case 'BLUE': return isDark ? const Color(0xFF60A5FA) : const Color(0xFF1D4ED8);
      case 'GREEN': return isDark ? AppColors.darkGreenLight : AppColors.green;
      default: return isDark ? AppColors.darkAmberLight : AppColors.amber;
    }
  }

  String _levelLabel(String level, bool isMarathi) {
    if (isMarathi) {
      switch (level) {
        case 'RED': return '🚨 आजच विक्री करा!';
        case 'BLUE': return '💎 थांबा!';
        case 'GREEN': return '✅ आजच विका!';
        default: return '⚠️ तुमची निवड';
      }
    } else {
      switch (level) {
        case 'RED': return '🚨 DO NOT SELL';
        case 'BLUE': return '💎 HOLD — Price Rising';
        case 'GREEN': return '✅ SELL TODAY — Peak';
        default: return '⚠️ YOUR CHOICE';
      }
    }
  }
}

// ── Briefing Card ──────────────────────────────────────────────────────────────
class _BriefingCard extends StatelessWidget {
  final String icon;
  final String title;
  final String body;
  final Color color;
  final bool isDark;

  const _BriefingCard({
    required this.icon,
    required this.title,
    required this.body,
    required this.color,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final surface = isDark ? AppColors.darkSurfaceRaised : AppColors.surface;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(icon, style: const TextStyle(fontSize: 18)),
            const SizedBox(width: 8),
            Text(title, style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700, color: color)),
          ]),
          const SizedBox(height: 10),
          Text(body,
              style: GoogleFonts.workSans(fontSize: 14, color: textPrimary, height: 1.6)),
        ],
      ),
    );
  }
}

// ── Chat Bubble ────────────────────────────────────────────────────────────────
class _ChatMsg {
  final String text;
  final bool isUser;
  _ChatMsg({required this.text, required this.isUser});
}

class _ChatBubble extends StatelessWidget {
  final _ChatMsg msg;
  final bool isDark;
  const _ChatBubble({required this.msg, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final isUser = msg.isUser;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
        decoration: BoxDecoration(
          color: isUser
              ? AppColors.green
              : (isDark ? AppColors.darkSurfaceHigh : AppColors.surfaceRaised),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
        ),
        child: Text(
          msg.text,
          style: GoogleFonts.workSans(
            fontSize: 13,
            color: isUser ? Colors.white : (isDark ? AppColors.darkTextPrimary : AppColors.textPrimary),
            height: 1.5,
          ),
        ),
      ),
    );
  }
}
