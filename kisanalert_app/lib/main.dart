import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'theme/app_theme.dart';
import 'state/app_state.dart';
import 'data/app_data.dart';
import 'screens/home_screen.dart';
import 'screens/mandi_screen.dart';
import 'screens/predict_screen.dart';
import 'screens/weather_screen.dart';
import 'screens/profile_screen.dart';
import 'modals/modals.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  runApp(const KisanAlertApp());
}

class KisanAlertApp extends StatefulWidget {
  const KisanAlertApp({super.key});

  @override
  State<KisanAlertApp> createState() => _KisanAlertAppState();
}

class _KisanAlertAppState extends State<KisanAlertApp> {
  final AppState _appState = AppState();

  @override
  void initState() {
    super.initState();
    _appState.addListener(() => setState(() {}));
    _appState.startAutoRefresh();
  }

  @override
  void dispose() {
    _appState.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'KisanAlert',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: _appState.isDark ? ThemeMode.dark : ThemeMode.light,
      home: AppShell(state: _appState),
    );
  }
}

class AppShell extends StatefulWidget {
  final AppState state;
  const AppShell({super.key, required this.state});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  Offset _fabPosition = Offset.zero;
  bool _fabInitialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_fabInitialized) {
      final size = MediaQuery.of(context).size;
      _fabPosition = Offset(size.width - 80, size.height - 140);
      _fabInitialized = true;
    }
  }

  void _openVoice() {
    showDialog(
      context: context,
      barrierColor: Colors.transparent,
      builder: (_) => VoiceModal(
        isDark: widget.state.isDark,
        isMarathi: widget.state.isMarathi,
        activeCrop: widget.state.activeCrop,
        onClose: () => Navigator.of(context).pop(),
      ),
    );
  }

  void _openMandi(MandiData m) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => MandiDetailSheet(
        mandi: m,
        isDark: widget.state.isDark,
        isMarathi: widget.state.isMarathi,
        activeCrop: widget.state.activeCrop,
        onClose: () => Navigator.of(context).pop(),
      ),
    );
  }

  void _openSignal(Signal s) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => SignalModal(
        signal: s,
        isDark: widget.state.isDark,
        isMarathi: widget.state.isMarathi,
        onClose: () => Navigator.of(context).pop(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.state.isDark;
    final bg = isDark ? AppColors.darkPageBg : AppColors.pageBg;

    final pages = [
      HomeScreen(state: widget.state, onOpenVoice: _openVoice, onOpenMandi: _openMandi, onOpenSignal: _openSignal),
      MandiScreen(state: widget.state, onOpenMandi: _openMandi),
      PredictScreen(state: widget.state),
      WeatherScreen(state: widget.state),
      ProfileScreen(state: widget.state, onOpenVoice: _openVoice),
    ];

    final now = DateTime.now();
    final monthsEn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    final dateString = '${now.day} ${monthsEn[now.month - 1]} ${now.year}';

    final pageTitles = [
      [widget.state.isMarathi ? 'KisanAlert' : 'KisanAlert', widget.state.isMarathi ? 'नांदेड · $dateString' : 'Nanded · $dateString'],
      [widget.state.isMarathi ? 'मंडी मॅप' : 'Mandi Map', widget.state.isMarathi ? 'मराठवाडा · 7 जिल्हे' : 'Marathwada · 7 Districts'],
      [widget.state.isMarathi ? 'AI अंदाज' : 'AI Prediction', widget.state.isMarathi ? '3 मॉडेल्स · Live Data' : '3 Models · Live Data'],
      [widget.state.isMarathi ? 'हवामान → नफा' : 'Weather → Profit', widget.state.isMarathi ? 'नांदेड · 18.39°N 77.31°E' : 'Nanded · 18.39°N 77.31°E'],
      [widget.state.isMarathi ? 'प्रोफाइल' : 'Profile', ''],
    ];

    return Stack(
      children: [
        Scaffold(
          backgroundColor: bg,
          body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // Status bar simulation
            _StatusBar(isDark: isDark),
            // Top app bar
            _TopAppBar(
              title: pageTitles[widget.state.activeTab][0],
              subtitle: pageTitles[widget.state.activeTab][1],
              state: widget.state,
              isDark: isDark,
            ),
            // Loading progress line
            _ProgressLine(isDark: isDark),
            // Page content
            Expanded(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 250),
                transitionBuilder: (child, anim) => FadeTransition(
                  opacity: anim,
                  child: SlideTransition(
                    position: Tween<Offset>(begin: const Offset(0, 0.03), end: Offset.zero).animate(
                      CurvedAnimation(parent: anim, curve: Curves.easeOut),
                    ),
                    child: child,
                  ),
                ),
                child: KeyedSubtree(
                  key: ValueKey(widget.state.activeTab),
                  child: pages[widget.state.activeTab],
                ),
              ),
            ),
          ],
        ),
      ),
      // Bottom nav
      bottomNavigationBar: _BottomNav(state: widget.state, isDark: isDark),
    ),
        Positioned(
          left: _fabPosition.dx,
          top: _fabPosition.dy,
          child: GestureDetector(
            onPanUpdate: (details) {
              setState(() {
                _fabPosition += details.delta;
              });
            },
            child: _GreenFAB(onTap: _openVoice),
          ),
        ),
      ],
    );
  }
}

// ── Status Bar ──────────────────────────────────────────────────────
class _StatusBar extends StatelessWidget {
  final bool isDark;
  const _StatusBar({required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text('9:41', style: GoogleFonts.spaceGrotesk(fontSize: 13, fontWeight: FontWeight.w700, color: textColor)),
          Row(children: [
            Icon(Icons.signal_cellular_4_bar, size: 14, color: textColor),
            const SizedBox(width: 4),
            Text('4G', style: GoogleFonts.spaceGrotesk(fontSize: 11, color: textColor)),
            const SizedBox(width: 6),
            Icon(Icons.wifi, size: 14, color: textColor),
            const SizedBox(width: 6),
            Icon(Icons.battery_full, size: 14, color: textColor),
            const SizedBox(width: 2),
            Text('100%', style: GoogleFonts.spaceGrotesk(fontSize: 11, color: textColor)),
          ]),
        ],
      ),
    );
  }
}

// ── Top App Bar ─────────────────────────────────────────────────────
class _TopAppBar extends StatelessWidget {
  final String title, subtitle;
  final AppState state;
  final bool isDark;

  const _TopAppBar({required this.title, required this.subtitle, required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: (isDark ? AppColors.darkSurface : AppColors.surface).withValues(alpha:0.85),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha:isDark ? 0.2 : 0.04), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Row(
        children: [
          // Logo / Title
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.spaceGrotesk(
                    fontSize: 20, fontWeight: FontWeight.w800,
                    color: state.activeTab == 0 ? AppColors.greenVivid : textPrimary,
                  ),
                ),
                if (subtitle.isNotEmpty)
                  Text(subtitle, style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
              ],
            ),
          ),
          // Language toggle
          GestureDetector(
            onTap: state.toggleLanguage,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Row(children: [
                Text('मराठी',
                  style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w700,
                    color: state.isMarathi ? AppColors.green : textMuted)),
                Text(' | ', style: GoogleFonts.workSans(fontSize: 12, color: textMuted)),
                Text('EN',
                  style: GoogleFonts.workSans(fontSize: 12, fontWeight: FontWeight.w700,
                    color: !state.isMarathi ? AppColors.green : textMuted)),
              ]),
            ),
          ),
          const SizedBox(width: 8),
          // Theme toggle
          GestureDetector(
            onTap: state.toggleTheme,
            child: Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
                shape: BoxShape.circle,
              ),
              child: Icon(isDark ? Icons.light_mode : Icons.dark_mode, size: 18,
                color: isDark ? AppColors.darkAmberLight : AppColors.textMuted),
            ),
          ),
          const SizedBox(width: 8),
          // Notification bell
          Container(
            width: 40, height: 40,
            decoration: BoxDecoration(
              color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
              shape: BoxShape.circle,
            ),
            child: Stack(
              children: [
                const Center(child: Icon(Icons.notifications_outlined, size: 20, color: AppColors.textMuted)),
                Positioned(top: 8, right: 8,
                  child: Container(width: 8, height: 8,
                    decoration: const BoxDecoration(color: AppColors.red, shape: BoxShape.circle))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Progress Line ────────────────────────────────────────────────────
class _ProgressLine extends StatefulWidget {
  final bool isDark;
  const _ProgressLine({required this.isDark});

  @override
  State<_ProgressLine> createState() => _ProgressLineState();
}

class _ProgressLineState extends State<_ProgressLine> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 2000));
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
    _ctrl.forward();
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, _) => Opacity(
        opacity: 1 - _anim.value,
        child: LinearProgressIndicator(
          value: _anim.value,
          minHeight: 2,
          backgroundColor: Colors.transparent,
          valueColor: const AlwaysStoppedAnimation(AppColors.greenVivid),
        ),
      ),
    );
  }
}

// ── Bottom Navigation ────────────────────────────────────────────────
class _BottomNav extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _BottomNav({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final navItems = [
      ('🏠', state.isMarathi ? 'घर' : 'Home'),
      ('🗺️', state.isMarathi ? 'मंडी' : 'Mandis'),
      ('📊', state.isMarathi ? 'अंदाज' : 'Predict'),
      ('🌦️', state.isMarathi ? 'हवामान' : 'Weather'),
      ('👤', state.isMarathi ? 'प्रोफाइल' : 'Profile'),
    ];
    final bg = isDark ? AppColors.darkSurface.withValues(alpha:0.95) : AppColors.surface.withValues(alpha:0.95);
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;

    return Container(
      decoration: BoxDecoration(
        color: bg,
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha:isDark ? 0.3 : 0.08), blurRadius: 16, offset: const Offset(0, -4))],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 68,
          child: Row(
            children: navItems.asMap().entries.map((e) {
              final isActive = state.activeTab == e.key;
              // Skip FAB slot (tab 4 shifts right for FAB)
              return Expanded(
                child: GestureDetector(
                  onTap: () => state.setActiveTab(e.key),
                  behavior: HitTestBehavior.opaque,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: isActive ? 40 : 0,
                        height: 2,
                        decoration: BoxDecoration(
                          color: AppColors.greenVivid,
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(e.value.$1, style: TextStyle(fontSize: isActive ? 22 : 20)),
                      const SizedBox(height: 2),
                      Text(e.value.$2,
                        style: GoogleFonts.workSans(
                          fontSize: 10, fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
                          color: isActive ? AppColors.greenVivid : textPrimary.withValues(alpha:0.5),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}

// ── Green FAB ────────────────────────────────────────────────────────
class _GreenFAB extends StatefulWidget {
  final VoidCallback onTap;
  const _GreenFAB({required this.onTap});

  @override
  State<_GreenFAB> createState() => _GreenFABState();
}

class _GreenFABState extends State<_GreenFAB> with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 1500))..repeat(reverse: true);
    _scale = Tween(begin: 1.0, end: 1.06).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _scale,
      builder: (_, child) => Transform.scale(scale: _scale.value, child: child),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 62,
          height: 62,
          margin: const EdgeInsets.only(bottom: 20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.green, AppColors.greenVivid],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            shape: BoxShape.circle,
            boxShadow: [BoxShadow(color: AppColors.green.withValues(alpha:0.45), blurRadius: 20, spreadRadius: 2, offset: const Offset(0, 8))],
          ),
          child: const Icon(Icons.mic, color: Colors.white, size: 28),
        ),
      ),
    );
  }
}
