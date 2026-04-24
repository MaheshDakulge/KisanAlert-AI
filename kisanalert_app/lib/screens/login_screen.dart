import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../state/app_state.dart';
import '../data/auth_service.dart';
import '../theme/app_theme.dart';

class LoginScreen extends StatefulWidget {
  final AppState state;
  const LoginScreen({super.key, required this.state});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _nameCtrl    = TextEditingController();
  final _phoneCtrl   = TextEditingController();
  final _villageCtrl = TextEditingController();
  final _acresCtrl   = TextEditingController();
  String _district   = 'Nanded';
  List<String> _selectedCrops = ['Soybean'];
  bool _isLoading = false;
  bool _isGoogleLoading = false;

  late AnimationController _fadeCtrl;
  late Animation<double> _fade;

  final _marathwadaDistricts = [
    'Nanded', 'Latur', 'Osmanabad', 'Hingoli',
    'Parbhani', 'Beed', 'Jalna', 'Aurangabad',
  ];

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 900));
    _fade = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    _fadeCtrl.forward();
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _villageCtrl.dispose();
    _acresCtrl.dispose();
    super.dispose();
  }

  Future<void> _submitPhone() async {
    if (_nameCtrl.text.trim().isEmpty || _phoneCtrl.text.trim().length < 10) {
      _showSnack('Please enter your name and a 10-digit mobile number');
      return;
    }
    setState(() => _isLoading = true);
    final id = await AuthService.login(_phoneCtrl.text.trim(), _nameCtrl.text.trim());
    await widget.state.login(
      id ?? 'offline_${_phoneCtrl.text}',
      _nameCtrl.text.trim(),
      _phoneCtrl.text.trim(),
      village: _villageCtrl.text.trim(),
      district: _district,
      acres: _acresCtrl.text.trim(),
      primaryCrop: _selectedCrops.join(', '),
    );
    if (mounted) setState(() => _isLoading = false);
  }

  Future<void> _submitGoogle() async {
    setState(() => _isGoogleLoading = true);
    // Google Sign-In — graceful fallback for demo / unsigned builds
    try {
      await widget.state.login(
        'google_demo_user',
        _nameCtrl.text.trim().isNotEmpty ? _nameCtrl.text.trim() : 'Google Farmer',
        _phoneCtrl.text.trim(),
        village: _villageCtrl.text.trim(),
        district: _district,
        acres: _acresCtrl.text.trim(),
        primaryCrop: _selectedCrops.join(', '),
      );
    } catch (_) {
      _showSnack('Google Sign-In unavailable — using demo mode');
      await widget.state.login(
        'demo_google_user', 'Demo Farmer', '',
        district: _district, primaryCrop: _selectedCrops.join(', '),
      );
    }
    if (mounted) setState(() => _isGoogleLoading = false);
  }

  void _showSnack(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: AppColors.greenVivid));
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final bg = isDark ? AppColors.darkPageBg : const Color(0xFFF0F7F0);
    final surface = isDark ? AppColors.darkSurface : Colors.white;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return Scaffold(
      backgroundColor: bg,
      body: FadeTransition(
        opacity: _fade,
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 56),

              // ── Logo ──────────────────────────────────────────────────────
              Center(
                child: Container(
                  width: 110, height: 110,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(color: AppColors.green.withValues(alpha: 0.25),
                          blurRadius: 24, spreadRadius: 4),
                    ],
                  ),
                  child: ClipOval(
                    child: Image.asset(
                      'assets/images/logo.jpg',
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // ── App title ─────────────────────────────────────────────────
              Text('KisanAlert',
                style: GoogleFonts.spaceGrotesk(
                  fontSize: 32, fontWeight: FontWeight.w800,
                  color: AppColors.greenVivid,
                )),
              Text('AI-Powered Crop Price Alerts',
                style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
              const SizedBox(height: 6),

              // ── Powered by Google badge ───────────────────────────────────
              _GooglePoweredBadge(),
              const SizedBox(height: 32),

              // ── Form card ─────────────────────────────────────────────────
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: surface,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(color: Colors.black.withValues(alpha: isDark ? 0.3 : 0.07),
                        blurRadius: 20, offset: const Offset(0, 6)),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Your Profile',
                      style: GoogleFonts.spaceGrotesk(
                        fontSize: 18, fontWeight: FontWeight.w700, color: textPrimary)),
                    Text('We personalise alerts for your farm',
                      style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
                    const SizedBox(height: 20),

                    // Name
                    _Field(ctrl: _nameCtrl, label: '👤 Full Name *',
                      hint: 'e.g. Mahesh Dakulge', isDark: isDark, keyboardType: TextInputType.name),
                    const SizedBox(height: 14),

                    // Phone
                    _Field(ctrl: _phoneCtrl, label: '📱 Mobile Number *',
                      hint: '10-digit number', isDark: isDark,
                      keyboardType: TextInputType.phone, maxLength: 10),
                    const SizedBox(height: 14),

                    // Village
                    _Field(ctrl: _villageCtrl, label: '🏘️ Village / Town',
                      hint: 'e.g. Biloli, Mukhed...', isDark: isDark),
                    const SizedBox(height: 14),

                    // District dropdown
                    Text('📍 District',
                      style: GoogleFonts.workSans(fontSize: 13,
                        fontWeight: FontWeight.w600, color: textPrimary)),
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        border: Border.all(color: AppColors.green.withValues(alpha: 0.4)),
                        borderRadius: BorderRadius.circular(12),
                        color: isDark ? AppColors.darkSurfaceRaised : const Color(0xFFF8FFF8),
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: _district,
                          isExpanded: true,
                          dropdownColor: isDark ? AppColors.darkSurface : Colors.white,
                          style: GoogleFonts.workSans(
                            fontSize: 14, color: textPrimary),
                          items: _marathwadaDistricts.map((d) => DropdownMenuItem(
                            value: d,
                            child: Text(d),
                          )).toList(),
                          onChanged: (v) => setState(() => _district = v!),
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Acres
                    _Field(ctrl: _acresCtrl, label: '🌾 Farm Size (acres)',
                      hint: 'e.g. 5', isDark: isDark,
                      keyboardType: TextInputType.number),
                    const SizedBox(height: 14),

                    // Primary crop
                    Text('🌱 Primary Crop',
                      style: GoogleFonts.workSans(fontSize: 13,
                        fontWeight: FontWeight.w600, color: textPrimary)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        ('Soybean', '🌱', 'सोयाबीन'),
                        ('Cotton',  '🌿', 'कापूस'),
                        ('Turmeric','🌾', 'हळद'),
                      ].map((c) {
                        final isActive = _selectedCrops.contains(c.$1);
                        return Expanded(
                          child: GestureDetector(
                            onTap: () => setState(() {
                              if (_selectedCrops.contains(c.$1)) {
                                if (_selectedCrops.length > 1) _selectedCrops.remove(c.$1);
                              } else {
                                _selectedCrops.add(c.$1);
                              }
                            }),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 180),
                              margin: const EdgeInsets.symmetric(horizontal: 3),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                color: isActive ? AppColors.green : Colors.transparent,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: isActive
                                      ? AppColors.green
                                      : AppColors.green.withValues(alpha: 0.3)),
                              ),
                              child: Column(children: [
                                Text(c.$2, style: const TextStyle(fontSize: 20)),
                                const SizedBox(height: 2),
                                Text(c.$1,
                                  style: GoogleFonts.workSans(
                                    fontSize: 10, fontWeight: FontWeight.w600,
                                    color: isActive ? Colors.white : textMuted)),
                              ]),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // ── Google Sign-In button ──────────────────────────────────────
              _GoogleSignInButton(
                isLoading: _isGoogleLoading,
                onTap: _isLoading ? null : _submitGoogle,
              ),
              const SizedBox(height: 12),

              // ── Phone / Continue button ────────────────────────────────────
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.greenVivid,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(14)),
                    elevation: 0,
                  ),
                  onPressed: (_isLoading || _isGoogleLoading) ? null : _submitPhone,
                  child: _isLoading
                      ? const SizedBox(height: 22, width: 22,
                          child: CircularProgressIndicator(
                              color: Colors.white, strokeWidth: 2))
                      : Text('Continue with Phone →',
                          style: GoogleFonts.spaceGrotesk(
                            fontSize: 16, fontWeight: FontWeight.w700,
                            color: Colors.white)),
                ),
              ),
              const SizedBox(height: 20),

              // ── Google tech stack footer ───────────────────────────────────
              _GoogleTechRow(),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Field helper ─────────────────────────────────────────────────────────────
class _Field extends StatelessWidget {
  final TextEditingController ctrl;
  final String label, hint;
  final bool isDark;
  final TextInputType? keyboardType;
  final int? maxLength;
  const _Field({required this.ctrl, required this.label, required this.hint,
    required this.isDark, this.keyboardType, this.maxLength});

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
          style: GoogleFonts.workSans(
            fontSize: 13, fontWeight: FontWeight.w600, color: textPrimary)),
        const SizedBox(height: 6),
        TextField(
          controller: ctrl,
          keyboardType: keyboardType,
          maxLength: maxLength,
          style: GoogleFonts.workSans(fontSize: 14, color: textPrimary),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: GoogleFonts.workSans(
              color: textPrimary.withValues(alpha: 0.35), fontSize: 13),
            counterText: '',
            filled: true,
            fillColor: isDark
                ? AppColors.darkSurfaceRaised
                : const Color(0xFFF8FFF8),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                  color: AppColors.green.withValues(alpha: 0.4))),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                  color: AppColors.green.withValues(alpha: 0.3))),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: const BorderSide(color: AppColors.greenVivid, width: 2)),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          ),
        ),
      ],
    );
  }
}

// ── Google Sign-In Button ─────────────────────────────────────────────────────
class _GoogleSignInButton extends StatelessWidget {
  final bool isLoading;
  final VoidCallback? onTap;
  const _GoogleSignInButton({required this.isLoading, this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFDADADA)),
          boxShadow: [
            BoxShadow(color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 10, offset: const Offset(0, 3)),
          ],
        ),
        child: isLoading
            ? const Center(child: SizedBox(height: 22, width: 22,
                child: CircularProgressIndicator(strokeWidth: 2)))
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Google G icon using coloured text
                  Text('G',
                    style: GoogleFonts.roboto(
                      fontSize: 20, fontWeight: FontWeight.w700,
                      foreground: Paint()
                        ..shader = const LinearGradient(
                          colors: [
                            Color(0xFF4285F4),
                            Color(0xFFEA4335),
                            Color(0xFFFBBC05),
                            Color(0xFF34A853),
                          ],
                        ).createShader(const Rect.fromLTWH(0,0,24,24)),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text('Continue with Google',
                    style: GoogleFonts.roboto(
                      fontSize: 15, fontWeight: FontWeight.w500,
                      color: const Color(0xFF3C4043))),
                ],
              ),
      ),
    );
  }
}

// ── Powered by Google Badge ───────────────────────────────────────────────────
class _GooglePoweredBadge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F3F4),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: const Color(0xFFDADADA)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Powered by ',
            style: GoogleFonts.roboto(fontSize: 12, color: const Color(0xFF5F6368))),
          _GoogleText(size: 13),
        ],
      ),
    );
  }
}

// ── Google Tech Stack Row ─────────────────────────────────────────────────────
class _GoogleTechRow extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final techs = [
      ('Gemini AI', '🤖', const Color(0xFF4285F4)),
      ('Maps SDK', '🗺️', const Color(0xFF34A853)),
      ('Firebase', '🔥', const Color(0xFFEA4335)),
      ('Cloud Run', '☁️', const Color(0xFFFBBC05)),
    ];
    return Column(
      children: [
        Text('Built on Google Cloud for Solution Challenge 2026',
          textAlign: TextAlign.center,
          style: GoogleFonts.workSans(fontSize: 11, color: const Color(0xFF80868B))),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8, runSpacing: 8,
          alignment: WrapAlignment.center,
          children: techs.map((t) => Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: t.$3.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(999),
              border: Border.all(color: t.$3.withValues(alpha: 0.25)),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Text(t.$2, style: const TextStyle(fontSize: 12)),
              const SizedBox(width: 4),
              Text(t.$1,
                style: GoogleFonts.roboto(
                  fontSize: 11, fontWeight: FontWeight.w600, color: t.$3)),
            ]),
          )).toList(),
        ),
      ],
    );
  }
}

// ── Google coloured text ──────────────────────────────────────────────────────
class _GoogleText extends StatelessWidget {
  final double size;
  const _GoogleText({required this.size});
  @override
  Widget build(BuildContext context) {
    const letters = ['G', 'o', 'o', 'g', 'l', 'e'];
    const colors = [
      Color(0xFF4285F4), Color(0xFFEA4335), Color(0xFFFBBC05),
      Color(0xFF4285F4), Color(0xFF34A853), Color(0xFFEA4335),
    ];
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(letters.length, (i) => Text(letters[i],
        style: GoogleFonts.roboto(
          fontSize: size, fontWeight: FontWeight.w700, color: colors[i]))),
    );
  }
}
