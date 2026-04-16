import 'package:flutter/foundation.dart';
import '../data/app_data.dart';
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

  CropData? _currentCrop;
  CropData? get currentCrop => _currentCrop;

  List<MandiData> _currentMandis = [];
  List<MandiData> get currentMandis => _currentMandis;

  List<Signal> _currentSignals = [];
  List<Signal> get currentSignals => _currentSignals;

  List<ForecastDay> _currentForecast = [];
  List<ForecastDay> get currentForecast => _currentForecast;

  final List<CommunityStory> _currentStories = [];
  List<CommunityStory> get currentStories => _currentStories;

  AppState() {
    fetchData();
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
      final alertData = await ApiService.getLatestAlert(_activeCrop, 'Nanded');
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
        _currentCrop = CropData(name: _activeCrop, price: 0, crashScore: 0, alertLevel: 'GREEN', message: 'No live alert data.', msp: 0);
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
          _currentMandis.first = MandiData(
            name: _currentMandis.first.name,
            distanceKm: _currentMandis.first.distanceKm,
            soybeanPrice: _currentMandis.first.soybeanPrice,
            cottonPrice: _currentMandis.first.cottonPrice,
            turmericPrice: _currentMandis.first.turmericPrice,
            signal: _currentMandis.first.signal,
            weather: _currentMandis.first.weather,
            advice: _currentMandis.first.advice,
            isBest: true,
          );
        }
      } else {
        _currentMandis = [];
      }

      // ── Signals (derived from latest alert fields) ──────────────────────
      final alertForSignals = await ApiService.getLatestAlert(_activeCrop, 'Nanded');
      if (alertForSignals != null) {
        _currentSignals = [
          Signal(
            label: 'Crash Score ${((alertForSignals['crash_score'] as num).toDouble() * 100).toStringAsFixed(0)}%',
            level: alertForSignals['alert_level'] ?? 'AMBER',
            explanation: alertForSignals['message'] ?? '',
            marathi: alertForSignals['message'] ?? '',
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

    } catch (e) {
      _currentCrop = CropData(name: _activeCrop, price: 0, crashScore: 0, alertLevel: 'GREEN', message: 'Network error — check backend.', msp: 0);
      _currentMandis = [];
      _currentSignals = [];
      _currentForecast = [];
    } finally {
      _isLoading = false;
      notifyListeners();
    }
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
}
