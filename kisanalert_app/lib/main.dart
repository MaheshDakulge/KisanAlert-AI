import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'firebase_options.dart';
import 'theme/app_theme.dart';
import 'state/app_state.dart';
import 'data/app_data.dart';
import 'screens/home_screen.dart';
import 'screens/mandi_screen.dart';
import 'screens/predict_screen.dart';
import 'screens/weather_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/login_screen.dart';
import 'modals/modals.dart';

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Initialize Firebase if needed for background handling
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
print("Handling a background message: ${message.messageId}");
}

final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin = FlutterLocalNotificationsPlugin();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // ⭐ Google Firebase initialization
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );

    // Initialize Local Notifications
    const AndroidInitializationSettings initializationSettingsAndroid = AndroidInitializationSettings('@mipmap/ic_launcher');
    const InitializationSettings initializationSettings = InitializationSettings(android: initializationSettingsAndroid);
    await flutterLocalNotificationsPlugin.initialize(initializationSettings);

    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  } catch (_) {
    // Firebase not configured yet — app still runs without FCM
  }
  SystemChrome.setPreferredOrientations([DeviceOrientation.portraitUp]);
  // Hide the status bar (time, battery, etc.) for a cleaner demo experience
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.manual, overlays: [SystemUiOverlay.bottom]);
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
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.manual, overlays: [SystemUiOverlay.bottom]);
    _appState.addListener(() => setState(() {}));
    _appState.startAutoRefresh();
    _setupFCMListener();
  }

  /// ⭐ FCM DATA_REFRESH — backend broadcasts this after every 5 PM pipeline run.
  /// Flutter silently calls fetchData() so all screens update automatically.
  void _setupFCMListener() async {
    try {
      FirebaseMessaging messaging = FirebaseMessaging.instance;

      // Request notification permissions (required for Android 13+ and iOS)
      await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      await messaging.subscribeToTopic('market_alerts');
      // Foreground messages
      FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        RemoteNotification? notification = message.notification;
        AndroidNotification? android = message.notification?.android;

        if (notification != null && android != null) {
          flutterLocalNotificationsPlugin.show(
            notification.hashCode,
            notification.title,
            notification.body,
            const NotificationDetails(
              android: AndroidNotificationDetails(
                'market_alerts_channel',
                'Market Alerts',
                importance: Importance.max,
                priority: Priority.high,
                showWhen: true,
                enableVibration: true,
                playSound: true,
              ),
            ),
          );
        }

        if (message.data['type'] == 'DATA_REFRESH') {
          _appState.fetchData();
        }
      });
      // Notification tap when app is in background
      FirebaseMessaging.onMessageOpenedApp.listen((_) {
        _appState.fetchData();
      });
    } catch (_) {
      // Firebase not set up — falls back to hourly timer in startAutoRefresh()
    }
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
      // Load from state if exists, otherwise default to bottom-right
      _fabPosition = Offset(
        widget.state.fabX ?? (size.width - 80),
        widget.state.fabY ?? (size.height - 140),
      );
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

    // ── Cold-start splash: show while server is waking up ──────────────────────
    if (widget.state.isWakingUp) {
      return _WakeUpSplash(isDark: isDark, status: widget.state.loadingStatus);
    }

    if (!widget.state.isLoggedIn) {
      return LoginScreen(state: widget.state);
    }

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
                final size = MediaQuery.of(context).size;
                _fabPosition += details.delta;
                // Clamp to screen bounds
                _fabPosition = Offset(
                  _fabPosition.dx.clamp(0.0, size.width - 62),
                  _fabPosition.dy.clamp(0.0, size.height - 130),
                );
              });
            },
            onPanEnd: (_) {
              widget.state.updateFabPosition(_fabPosition.dx, _fabPosition.dy);
            },
            child: _GreenFAB(onTap: _openVoice),
          ),
        ),
      ],
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
          // ── Notification Bell (tappable) ──────────────────────────────
          GestureDetector(
            onTap: () {
              state.markAllRead();
              showModalBottomSheet(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                builder: (_) => _NotificationPanel(state: state, isDark: isDark),
              );
            },
            child: Container(
              width: 40, height: 40,
              decoration: BoxDecoration(
                color: isDark ? AppColors.darkSurfaceRaised : AppColors.surfaceRaised,
                shape: BoxShape.circle,
              ),
              child: Stack(
                children: [
                  Center(child: Icon(Icons.notifications_outlined, size: 20,
                    color: state.unreadCount > 0 ? AppColors.greenVivid : AppColors.textMuted)),
                  if (state.unreadCount > 0)
                    Positioned(
                      top: 6, right: 6,
                      child: Container(
                        width: 14, height: 14,
                        decoration: const BoxDecoration(
                          color: AppColors.red, shape: BoxShape.circle),
                        child: Center(
                          child: Text(
                            state.unreadCount > 9 ? '9+' : '${state.unreadCount}',
                            style: const TextStyle(
                              color: Colors.white, fontSize: 8,
                              fontWeight: FontWeight.w800),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
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

// ── Notification Panel ────────────────────────────────────────────────────────
class _NotificationPanel extends StatelessWidget {
  final AppState state;
  final bool isDark;
  const _NotificationPanel({required this.state, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final bg = isDark ? AppColors.darkSurface : Colors.white;
    final textPrimary = isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted = isDark ? AppColors.darkTextSecondary : AppColors.textMuted;
    final notifs = state.notifications;

    return DraggableScrollableSheet(
      initialChildSize: 0.6,
      minChildSize: 0.4,
      maxChildSize: 0.92,
      builder: (_, scrollCtrl) => Container(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          boxShadow: [BoxShadow(
              color: Colors.black.withValues(alpha: 0.15), blurRadius: 24)],
        ),
        child: Column(
          children: [
            // Handle bar
            Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40, height: 4,
              decoration: BoxDecoration(
                color: textMuted.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(2)),
            ),
            // Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                children: [
                  Icon(Icons.notifications_active_rounded,
                      color: AppColors.greenVivid, size: 22),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('Market Alerts',
                      style: GoogleFonts.spaceGrotesk(
                          fontSize: 18, fontWeight: FontWeight.w800,
                          color: textPrimary)),
                  ),
                  if (notifs.isNotEmpty)
                    GestureDetector(
                      onTap: () { state.markAllRead(); Navigator.pop(context); },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: AppColors.greenVivid.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(999)),
                        child: Text('Mark all read',
                          style: GoogleFonts.workSans(
                              fontSize: 12, fontWeight: FontWeight.w600,
                              color: AppColors.greenVivid)),
                      ),
                    ),
                ],
              ),
            ),
            const Divider(height: 1),
            // List
            Expanded(
              child: notifs.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Text('🔔', style: TextStyle(fontSize: 48)),
                          const SizedBox(height: 12),
                          Text('No alerts yet',
                            style: GoogleFonts.workSans(
                                fontSize: 16, color: textMuted)),
                          Text('Alerts appear after market data loads',
                            style: GoogleFonts.workSans(
                                fontSize: 12, color: textMuted)),
                        ],
                      ),
                    )
                  : ListView.separated(
                      controller: scrollCtrl,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                      itemCount: notifs.length,
                      separatorBuilder: (_, __) =>
                          const Divider(height: 1, indent: 56),
                      itemBuilder: (_, i) {
                        final n = notifs[i];
                        return ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 4, vertical: 4),
                          leading: Container(
                            width: 42, height: 42,
                            decoration: BoxDecoration(
                              color: AppColors.greenVivid.withValues(alpha: 0.1),
                              shape: BoxShape.circle),
                            child: Center(
                              child: Text(n.emoji,
                                  style: const TextStyle(fontSize: 20))),
                          ),
                          title: Text(n.title,
                            style: GoogleFonts.spaceGrotesk(
                              fontSize: 13, fontWeight: FontWeight.w700,
                              color: n.isRead
                                  ? textMuted
                                  : textPrimary)),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(n.body,
                                style: GoogleFonts.workSans(
                                    fontSize: 12, color: textMuted)),
                              Text(n.timeAgo,
                                style: GoogleFonts.workSans(
                                    fontSize: 10,
                                    color: AppColors.greenVivid)),
                            ],
                          ),
                          trailing: n.isRead
                              ? null
                              : Container(
                                  width: 8, height: 8,
                                  decoration: const BoxDecoration(
                                      color: AppColors.greenVivid,
                                      shape: BoxShape.circle)),
                        );
                      },
                    ),
            ),
            // Powered by Google footer
            Container(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Alerts powered by ',
                    style: GoogleFonts.roboto(
                        fontSize: 11, color: textMuted)),
                  Text('G', style: GoogleFonts.roboto(
                      fontSize: 12, fontWeight: FontWeight.w700,
                      color: const Color(0xFF4285F4))),
                  Text('o', style: GoogleFonts.roboto(
                      fontSize: 12, fontWeight: FontWeight.w700,
                      color: const Color(0xFFEA4335))),
                  Text('o', style: GoogleFonts.roboto(
                      fontSize: 12, fontWeight: FontWeight.w700,
                      color: const Color(0xFFFBBC05))),
                  Text('g', style: GoogleFonts.roboto(
                      fontSize: 12, fontWeight: FontWeight.w700,
                      color: const Color(0xFF4285F4))),
                  Text('l', style: GoogleFonts.roboto(
                      fontSize: 12, fontWeight: FontWeight.w700,
                      color: const Color(0xFF34A853))),
                  Text('e', style: GoogleFonts.roboto(
                      fontSize: 12, fontWeight: FontWeight.w700,
                      color: const Color(0xFFEA4335))),
                  Text(' Gemini AI',
                    style: GoogleFonts.roboto(
                        fontSize: 11, color: textMuted)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Wake-Up Splash — real logo + Google branding ─────────────────────────────
class _WakeUpSplash extends StatefulWidget {
  final bool isDark;
  final String status;
  const _WakeUpSplash({required this.isDark, required this.status});

  @override
  State<_WakeUpSplash> createState() => _WakeUpSplashState();
}

class _WakeUpSplashState extends State<_WakeUpSplash>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _pulse;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1400))
      ..repeat(reverse: true);
    _pulse = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final bg = widget.isDark ? AppColors.darkPageBg : const Color(0xFFF0F7F0);
    final textPrimary =
        widget.isDark ? AppColors.darkTextPrimary : AppColors.textPrimary;
    final textMuted =
        widget.isDark ? AppColors.darkTextSecondary : AppColors.textMuted;

    return Scaffold(
      backgroundColor: bg,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // ── Real KisanAlert Logo ─────────────────────────────────────
              AnimatedBuilder(
                animation: _pulse,
                builder: (_, child) => Transform.scale(
                    scale: 1.0 + _pulse.value * 0.06, child: child),
                child: Container(
                  width: 120, height: 120,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.green.withValues(alpha: 0.3),
                        blurRadius: 30, spreadRadius: 6),
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
              const SizedBox(height: 24),

              // ── App name ─────────────────────────────────────────────────
              Text('KisanAlert',
                style: GoogleFonts.spaceGrotesk(
                  fontSize: 34, fontWeight: FontWeight.w800,
                  color: AppColors.greenVivid)),
              Text('AI-Powered Crop Price Alerts',
                style: GoogleFonts.workSans(fontSize: 13, color: textMuted)),
              const SizedBox(height: 12),

              // ── Powered by Google ─────────────────────────────────────────
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: widget.isDark
                      ? Colors.white.withValues(alpha: 0.08)
                      : const Color(0xFFF1F3F4),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(color: const Color(0xFFDADADA))),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text('Powered by ',
                    style: GoogleFonts.roboto(
                        fontSize: 11, color: const Color(0xFF5F6368))),
                  ...['G','o','o','g','l','e'].asMap().entries.map((e) {
                    const cols = [
                      Color(0xFF4285F4), Color(0xFFEA4335), Color(0xFFFBBC05),
                      Color(0xFF4285F4), Color(0xFF34A853), Color(0xFFEA4335)];
                    return Text(e.value,
                      style: GoogleFonts.roboto(
                        fontSize: 12, fontWeight: FontWeight.w700,
                        color: cols[e.key]));
                  }),
                ]),
              ),
              const SizedBox(height: 36),

              // ── Animated dots ─────────────────────────────────────────────
              AnimatedBuilder(
                animation: _ctrl,
                builder: (_, __) => Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(3, (i) {
                    final delay = i / 3;
                    final v = ((_ctrl.value - delay) % 1.0 + 1.0) % 1.0;
                    final op = (v < 0.5 ? v * 2 : (1 - v) * 2).clamp(0.2, 1.0);
                    return Container(
                      margin: const EdgeInsets.symmetric(horizontal: 5),
                      width: 10, height: 10,
                      decoration: BoxDecoration(
                        color: AppColors.greenVivid.withValues(alpha: op),
                        shape: BoxShape.circle),
                    );
                  }),
                ),
              ),
              const SizedBox(height: 18),

              Text(widget.status,
                textAlign: TextAlign.center,
                style: GoogleFonts.workSans(
                    fontSize: 14, fontWeight: FontWeight.w600,
                    color: textPrimary)),
              const SizedBox(height: 6),
              Text('Free server tier — first load ~30 sec',
                style: GoogleFonts.workSans(fontSize: 11, color: textMuted)),
              const SizedBox(height: 32),

              // ── Google tech stack badges ──────────────────────────────────
              Wrap(
                spacing: 8, runSpacing: 8,
                alignment: WrapAlignment.center,
                children: [
                  ('Gemini AI', '🤖', const Color(0xFF4285F4)),
                  ('Maps SDK', '🗺️', const Color(0xFF34A853)),
                  ('Firebase', '🔥', const Color(0xFFEA4335)),
                  ('Cloud Run', '☁️', const Color(0xFFFBBC05)),
                ].map((t) => Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: t.$3.withValues(alpha: 0.09),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(
                        color: t.$3.withValues(alpha: 0.25))),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text(t.$2, style: const TextStyle(fontSize: 12)),
                    const SizedBox(width: 4),
                    Text(t.$1,
                      style: GoogleFonts.roboto(
                        fontSize: 11, fontWeight: FontWeight.w600,
                        color: t.$3)),
                  ]),
                )).toList(),
              ),
              const SizedBox(height: 16),
              Text('Google Solution Challenge 2026',
                style: GoogleFonts.roboto(
                    fontSize: 11, color: textMuted,
                    fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      ),
    );
  }
}

