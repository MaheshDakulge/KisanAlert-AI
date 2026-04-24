import 'package:flutter/foundation.dart';
import '../data/app_data.dart';
import '../db_helper.dart';
import 'dart:async';
class AppState extends ChangeNotifier {
  // Language
  bool _isMarathi = true;
  bool get isMarathi => _isMarathi;
  void toggleLanguage() {
    _isMarathi = !_isMarathi;
    notifyListeners();
  }

  // Theme
  bool _isDark = false;
  bool get isDark => _isDark;
  void toggleTheme() {
    _isDark = !_isDark;
    notifyListeners();
  }

  // Active crop
  String _activeCrop = 'Soybean';
  String get activeCrop => _activeCrop;

  bool _isLoading = true;
  bool get isLoading => _isLoading;

  // ── Wake-up / loading status ────────────────────────────────────────────────
  bool _isWakingUp = false;
  bool get isWakingUp => _isWakingUp;
  String _loadingStatus = 'Connecting to server...';
  String get loadingStatus => _loadingStatus;

  CropData? _currentCrop;
  CropData? get currentCrop => _currentCrop;

  List<MandiData> _currentMandis = [];
  List<MandiData> get currentMandis => _currentMandis;

  List<Signal> _currentSignals = [];
  List<Signal> get currentSignals => _currentSignals;

  List<ForecastDay> _currentForecast = [];
  List<ForecastDay> get currentForecast => _currentForecast;

  List<CommunityStory> _currentStories = [];
  List<CommunityStory> get currentStories => _currentStories;

  List<dynamic> _yearHistory = [];
  List<dynamic> get yearHistory => _yearHistory;

  ForecastData? _forecast;
  ForecastData? get forecast => _forecast;

  AccuracyStats? _accuracyStats;
  AccuracyStats? get accuracyStats => _accuracyStats;

  Map<String, dynamic>? _farmerStats;
  Map<String, dynamic>? get farmerStats => _farmerStats;

  Timer? _weatherTimer;

  AppState() {
    _init();
  }

  Future<void> _init() async {
    // Step 1: Ping server to wake it up (handles Render cold start)
    _isWakingUp = true;
    _loadingStatus = isMarathi
        ? 'सर्व्हर सुरू होत आहे... (~३० सेकंद)'
        : 'Server waking up... (~30 sec)';
    notifyListeners();

    final alive = await ApiService.wakeUp();

    _isWakingUp = false;
    _loadingStatus = alive
        ? (isMarathi ? 'डेटा लोड होत आहे...' : 'Loading data...')
        : (isMarathi ? 'ऑफलाइन मोड' : 'Offline mode');
    notifyListeners();

    // Step 2: Load all data
    await fetchData();
  }

  void setActiveCrop(String crop) {
    if (_activeCrop == crop) return;
    _activeCrop = crop;
    notifyListeners();
    fetchData();
  }

  Future<void> fetchData() async {
    _isLoading = true;
    notifyListeners();

    try {
      var alertData = await ApiService.getLatestAlert(_activeCrop, 'Nanded');
      
      // Offline caching logic
      if (alertData != null) {
        // Cache the successful fetch
        alertData['created_at'] = DateTime.now().toIso8601String();
        await DatabaseHelper().cacheAlerts([alertData]);
      } else {
        // Fetch from cache if API failed
        final cached = await DatabaseHelper().getCachedAlerts();
        if (cached.isNotEmpty) {
          final matched = cached.where((a) => a['commodity'] == _activeCrop).toList();
          if (matched.isNotEmpty) {
            alertData = matched.first;
            // Append offline notice to message
            alertData['message'] = "[OFFLINE CACHE] " + (alertData['message'] ?? "");
          }
        }
      }

      if (alertData != null) {
        _currentCrop = CropData(
          name: _activeCrop,
          price: (alertData['price'] as num).toDouble(),
          crashScore: (alertData['crash_score'] as num).toDouble(),
          alertLevel: alertData['alert_level'] ?? 'AMBER',
          message: alertData['message'] ?? '',
          msp: _activeCrop == 'Soybean' ? 4892 : (_activeCrop == 'Cotton' ? 7121 : 12000),
        );
      } else {
        _currentCrop = CropData(name: _activeCrop, price: 0, crashScore: 0, alertLevel: 'GREEN', message: 'No live or cached data.', msp: 0);
      }

      final mandisData = await ApiService.getMandisCompare(_activeCrop);
      if (mandisData.isNotEmpty) {
        _currentMandis = mandisData.map((m) => MandiData(
          name: m['district'] ?? 'Unknown',
          distanceKm: _getDistance(m['district'] ?? ''),
          soybeanPrice: (m['price'] as num).toDouble(),
          cottonPrice: (m['price'] as num).toDouble(),
          turmericPrice: (m['price'] as num).toDouble(),
          signal: m['alert_level'] ?? 'GREEN',
          weather: '☀️ Clear', // Fallback for missing api field
          advice: m['message'] ?? 'No advice',
          isBest: false,
        )).toList();

        if (_currentMandis.isNotEmpty) {
          final best = _currentMandis[0];
          _currentMandis[0] = MandiData(
            name: best.name,
            distanceKm: best.distanceKm,
            soybeanPrice: best.soybeanPrice,
            cottonPrice: best.cottonPrice,
            turmericPrice: best.turmericPrice,
            signal: best.signal,
            weather: best.weather,
            advice: best.advice,
            isBest: true,
          );
        }
      } else {
        _currentMandis = [];
      }

      // ── Signals (derived from latest alert fields) ──────────────────────
      if (alertData != null) {
        _currentSignals = [
          Signal(
            label: 'Crash Score ${((alertData['crash_score'] as num).toDouble() * 100).toStringAsFixed(0)}%',
            level: alertData['alert_level'] ?? 'AMBER',
            explanation: alertData['message'] ?? '',
            marathi: alertData['message'] ?? '',
          ),
        ];
      } else {
        _currentSignals = [];
      }

      // ── Forecast days (from history endpoint) ─────────────────────────────
      final history = await ApiService.getAlertHistory(_activeCrop, limit: 7);
      if (history.isNotEmpty) {
        final days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        final daysMr = ['र', 'सो', 'मं', 'बु', 'गु', 'शु', 'श'];
        _currentForecast = history.reversed.toList().asMap().entries.map((e) {
          final h = e.value;
          final price = (h['price'] as num).toDouble();
          final score = (h['crash_score'] as num).toDouble();
          final risk = score >= 0.7 ? 'RED' : score >= 0.45 ? 'AMBER' : 'GREEN';
          final dateStr = h['date'] as String? ?? '';
          String dayLabel = 'Day';
          String dayLabelMr = 'दि';
          if (dateStr.isNotEmpty) {
            try {
              final dt = DateTime.parse(dateStr);
              dayLabel = days[dt.weekday % 7];
              dayLabelMr = daysMr[dt.weekday % 7];
            } catch (_) {}
          }
          final dir = e.key == 0 ? 'stable' : (price >= (history.reversed.toList()[e.key - 1]['price'] as num) ? 'up' : 'down');
          return ForecastDay(dayEn: dayLabel, dayMr: dayLabelMr, price: price, direction: dir, risk: risk);
        }).toList();
      } else {
        _currentForecast = [];
      }

      // ── Year History (for chart) ──────────────────────────────────────────
      _yearHistory = await ApiService.getAlertHistory(_activeCrop, limit: 365);

      // ── Community Stories (Chopal) ──────────────────────────────────────────
      final stories = await ApiService.getCommunityStories(_activeCrop);
      if (stories.isNotEmpty) {
        _currentStories = stories.map((s) => CommunityStory(
          initials: s['initials'] ?? '??',
          avatarColor: s['avatarColor'] ?? 'green',
          nameEn: s['nameEn'] ?? 'Anonymous',
          distanceKm: s['distanceKm'] ?? '0km',
          messageMr: s['messageMr'] ?? '',
          messageEn: s['messageEn'] ?? '',
          isVerified: s['isVerified'] ?? false,
          verifiedDate: s['verifiedDate'] ?? '',
          crop: s['crop'] ?? _activeCrop,
          saved: s['saved'] ?? '',
        )).toList();
      } else {
        _currentStories = [];
      }
      _forecast = await ApiService.getMultiDayForecast(_activeCrop);
      
      // ALIGN FORECAST WITH LIVE PRICE
      // The forecast uses the last known DB price, but the live price might differ slightly.
      // We align the forecast base to the live price so the UI percentage and chart trend perfectly match!
      if (_forecast != null && _currentCrop != null && _currentCrop!.price > 0) {
        final double diff = _currentCrop!.price - _forecast!.currentPrice;
        
        final alignedFutureDays = _forecast!.next10Days.map((f) => ForecastPredicted(
          date: f.date,
          predictedPrice: f.predictedPrice + diff,
          confidence: f.confidence,
        )).toList();

        final alignedPastDays = _forecast!.past7Days.map((p) => ForecastPoint(
          date: p.date,
          price: p.price,
          isActual: p.isActual,
        )).toList();
        
        // Ensure the last past point perfectly matches the live price
        if (alignedPastDays.isNotEmpty) {
          alignedPastDays.last = ForecastPoint(
            date: alignedPastDays.last.date,
            price: _currentCrop!.price,
            isActual: true,
          );
        }

        final newDay10Price = _forecast!.day10Predicted + diff;
        final newDay3Price = _forecast!.day3Predicted + diff;
        
        _forecast = ForecastData(
          currentPrice: _currentCrop!.price,
          currentDate: _forecast!.currentDate,
          past7Days: alignedPastDays,
          next10Days: alignedFutureDays,
          day3Predicted: newDay3Price,
          day3ChangePct: ((newDay3Price - _currentCrop!.price) / _currentCrop!.price) * 100,
          day10Predicted: newDay10Price,
          day10ChangePct: ((newDay10Price - _currentCrop!.price) / _currentCrop!.price) * 100,
          trend: _forecast!.trend,
        );
      }

      _accuracyStats = await ApiService.getAccuracyStats(days: 30);
      _farmerStats   = await ApiService.getFarmerStats();

      // ── Generate notifications after every successful data fetch ─────────
      if (_currentCrop != null && _currentCrop!.price > 0) {
        final price = _currentCrop!.price.toStringAsFixed(0);
        final level = _currentCrop!.alertLevel;

        addNotification(AppNotification(
          emoji: '📊',
          title: '$_activeCrop price updated',
          body: '₹$price/qtl — powered by Gemini AI + live Agmarknet data',
        ));

        if (level == 'RED') {
          addNotification(AppNotification(
            emoji: '🚨',
            title: 'Price Crash Alert — $_activeCrop',
            body: 'Do not sell today. Crash probability is high.',
          ));
        } else if (level == 'GREEN') {
          addNotification(AppNotification(
            emoji: '✅',
            title: 'Good time to sell — $_activeCrop',
            body: 'Market signal is GREEN at ₹$price/qtl.',
          ));
        }

        if (_forecast != null) {
          addNotification(AppNotification(
            emoji: '🔮',
            title: '10-day forecast ready',
            body: '$_activeCrop: ${_forecast!.trend} trend — Gemini prediction updated.',
          ));
        }
      }

    } catch (e) {
      _currentCrop = CropData(name: _activeCrop, price: 0, crashScore: 0, alertLevel: 'GREEN', message: 'Network error — check backend.', msp: 0);
      _currentMandis = [];
      _currentSignals = [];
      _currentForecast = [];
      _yearHistory = [];
      _currentStories = [];
      _forecast = null;
      _accuracyStats = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void startAutoRefresh() {
    _weatherTimer?.cancel();
    _weatherTimer = Timer.periodic(const Duration(hours: 1), (_) {
      fetchData();
    });
  }

  @override
  void dispose() {
    _weatherTimer?.cancel();
    super.dispose();
  }

  int _getDistance(String district) {
    if (district == 'Latur') return 75;
    if (district == 'Osmanabad') return 92;
    if (district == 'Beed') return 140;
    if (district == 'Hingoli') return 110;
    if (district == 'Jalna') return 155;
    if (district == 'Nanded') return 0;
    if (district == 'Parbhani') return 95;
    return 100;
  }

  // Active tab
  int _activeTab = 0;
  int get activeTab => _activeTab;
  void setActiveTab(int tab) {
    _activeTab = tab;
    notifyListeners();
  }

  String t(String mr, String en) => _isMarathi ? mr : en;

  // ── Farmer session ──────────────────────────────────────────────────────────
  String? farmerId;
  String? farmerName;
  String? farmerPhone;
  String? farmerVillage;
  String? farmerDistrict;
  String? farmerAcres;
  String? farmerPrimaryCrop;

  Future<void> login(String id, String name, String phone, {
    String village = '',
    String district = 'Nanded',
    String acres = '',
    String primaryCrop = 'Soybean',
  }) async {
    farmerId         = id;
    farmerName       = name;
    farmerPhone      = phone;
    farmerVillage    = village.isNotEmpty ? village : null;
    farmerDistrict   = district;
    farmerAcres      = acres.isNotEmpty ? acres : null;
    farmerPrimaryCrop = primaryCrop;
    // Switch active crop to the farmer's primary crop
    _activeCrop = primaryCrop;
    notifyListeners();
    await fetchData();
  }

  bool get isLoggedIn => farmerId != null && farmerId!.isNotEmpty;

  // ── Notifications ────────────────────────────────────────────────────────────
  final List<AppNotification> _notifications = [];
  List<AppNotification> get notifications => List.unmodifiable(_notifications);
  int get unreadCount => _notifications.where((n) => !n.isRead).length;

  void addNotification(AppNotification n) {
    _notifications.insert(0, n); // newest first
    if (_notifications.length > 50) _notifications.removeLast(); // cap at 50
    notifyListeners();
  }

  void markAllRead() {
    for (final n in _notifications) { n.isRead = true; }
    notifyListeners();
  }
}

// ── Notification Model ───────────────────────────────────────────────────────
class AppNotification {
  final String emoji;
  final String title;
  final String body;
  final DateTime createdAt;
  bool isRead;

  AppNotification({
    required this.emoji,
    required this.title,
    required this.body,
    DateTime? createdAt,
    this.isRead = false,
  }) : createdAt = createdAt ?? DateTime.now();

  String get timeAgo {
    final diff = DateTime.now().difference(createdAt);
    if (diff.inSeconds < 60) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }
}
