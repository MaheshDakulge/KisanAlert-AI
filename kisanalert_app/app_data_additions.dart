// ══════════════════════════════════════════════════════════════════
// KisanAlert v2.0 — Day 2 UX Reference
// Status: ALL INTEGRATED — this file is documentation only
//
// All code below is already live in:
//   lib/data/app_data.dart
//   lib/state/app_state.dart
//   lib/main.dart
//   lib/screens/home_screen.dart
// ══════════════════════════════════════════════════════════════════

// ── MODELS (live in lib/data/app_data.dart) ────────────────────────

// Updated CropData with BLUE signal support
// alertLevel: RED | BLUE | GREEN | AMBER
class CropData {
  final String name;
  final double price;
  final double crashScore;
  final double riseScore;       // Rise probability (0.0–1.0)
  final bool trendIsRising;     // true = BLUE signal path
  final String alertLevel;
  final String message;
  final double msp;

  CropData({
    required this.name,
    required this.price,
    required this.crashScore,
    this.riseScore = 0.0,
    this.trendIsRising = false,
    required this.alertLevel,
    required this.message,
    required this.msp,
  });
}

// Single actual price point (past 7 days)
class ForecastPoint {
  final String date;
  final double price;
  final bool isActual;
  ForecastPoint({required this.date, required this.price, required this.isActual});
}

// Single AI-predicted price point (next 10 days)
class ForecastPredicted {
  final String date;
  final double predictedPrice;
  final double confidence;
  ForecastPredicted({
    required this.date,
    required this.predictedPrice,
    required this.confidence,
  });
}

// Full 10-day LSTM forecast payload from GET /api/v1/forecast/multi-day
class ForecastData {
  final double currentPrice;
  final String currentDate;
  final List<ForecastPoint> past7Days;      // solid green line on chart
  final List<ForecastPredicted> next10Days; // dashed blue line on chart
  final double day3Predicted;
  final double day3ChangePct;
  final double day10Predicted;
  final double day10ChangePct;
  final String trend; // 'rising' | 'falling' | 'stable'

  ForecastData({
    required this.currentPrice,
    required this.currentDate,
    required this.past7Days,
    required this.next10Days,
    required this.day3Predicted,
    required this.day3ChangePct,
    required this.day10Predicted,
    required this.day10ChangePct,
    required this.trend,
  });

  factory ForecastData.fromJson(Map<String, dynamic> j) {
    return ForecastData(
      currentPrice: (j['current_price'] as num).toDouble(),
      currentDate: j['current_date'] ?? '',
      past7Days: ((j['past_7_days'] as List?) ?? [])
          .map((p) => ForecastPoint(
                date: p['date'],
                price: (p['price'] as num).toDouble(),
                isActual: true,
              ))
          .toList(),
      next10Days: ((j['next_10_days'] as List?) ?? [])
          .map((p) => ForecastPredicted(
                date: p['date'],
                predictedPrice: (p['predicted_price'] as num).toDouble(),
                confidence: (p['confidence'] as num).toDouble(),
              ))
          .toList(),
      day3Predicted: (j['day_3_predicted'] as num?)?.toDouble() ?? 0,
      day3ChangePct: (j['day_3_change_pct'] as num?)?.toDouble() ?? 0,
      day10Predicted: (j['day_10_predicted'] as num?)?.toDouble() ?? 0,
      day10ChangePct: (j['day_10_change_pct'] as num?)?.toDouble() ?? 0,
      trend: j['trend'] ?? 'stable',
    );
  }
}

// Accuracy stats from GET /api/v1/accuracy?days=30
// Displayed as trust badge on home screen
class AccuracyStats {
  final int total;
  final int correct;
  final double accuracy; // 0.0–1.0

  AccuracyStats({
    required this.total,
    required this.correct,
    required this.accuracy,
  });

  factory AccuracyStats.fromJson(Map<String, dynamic> j) {
    final stats = j['stats'] ?? j;
    return AccuracyStats(
      total: (stats['total'] as num?)?.toInt() ?? 0,
      correct: (stats['correct'] as num?)?.toInt() ?? 0,
      accuracy: (stats['accuracy'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

// ── API METHODS (live in lib/data/app_data.dart → ApiService) ──────

/*
  // GET /api/v1/forecast/multi-day?commodity={commodity}
  static Future<ForecastData?> getMultiDayForecast(String commodity) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/forecast/multi-day?commodity=$commodity'),
      ).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        return ForecastData.fromJson(json.decode(res.body));
      }
    } catch (_) {}
    return null;
  }

  // GET /api/v1/accuracy?days=30
  static Future<AccuracyStats?> getAccuracyStats({int days = 30}) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/accuracy?days=$days'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return AccuracyStats.fromJson(json.decode(res.body));
      }
    } catch (_) {}
    return null;
  }

  // POST /api/v1/voice/query  {query, commodity}
  static Future<String?> getVoiceAnswer(String query, String commodity) async {
    try {
      final res = await http.post(
        Uri.parse('$_baseUrl/voice/query'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'query': query, 'commodity': commodity}),
      ).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) {
        return json.decode(res.body)['marathi_response'];
      }
    } catch (_) {}
    return null;
  }
*/

// ── APPSTATE ADDITIONS (live in lib/state/app_state.dart) ──────────

/*
  import 'dart:async';

  // Fields (added after currentStories):
  ForecastData? _forecast;
  ForecastData? get forecast => _forecast;

  AccuracyStats? _accuracyStats;
  AccuracyStats? get accuracyStats => _accuracyStats;

  Timer? _weatherTimer;

  // In fetchData() — CropData creation now includes BLUE fields:
  _currentCrop = CropData(
    name: _activeCrop,
    price: (alertData['price'] as num).toDouble(),
    crashScore: (alertData['crash_score'] as num).toDouble(),
    riseScore: (alertData['rise_score'] as num?)?.toDouble() ?? 0.0,
    trendIsRising: alertData['trend_is_rising'] ?? false,
    alertLevel: alertData['alert_level'] ?? 'AMBER',
    message: alertData['message'] ?? '',
    msp: _activeCrop == 'Soybean' ? 4892 : (_activeCrop == 'Cotton' ? 7121 : 12000),
  );

  // At end of fetchData() try block:
  _forecast = await ApiService.getMultiDayForecast(_activeCrop);
  _accuracyStats = await ApiService.getAccuracyStats(days: 30);

  // In catch block:
  _forecast = null;
  _accuracyStats = null;

  // Auto-refresh every 1 hour (called from main.dart initState):
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
*/

// ── MAIN.DART CHANGE (live in lib/main.dart) ───────────────────────

/*
  @override
  void initState() {
    super.initState();
    _appState.addListener(() => setState(() {}));
    _appState.startAutoRefresh(); // ← added for 1-hour auto-refresh
  }
*/

// ══════════════════════════════════════════════════════════════════
// NEW BACKEND ENDPOINTS
// ══════════════════════════════════════════════════════════════════
//
//   GET  /api/v1/forecast/multi-day?commodity=Soybean
//        Returns ForecastData JSON with past 7 + next 10 days
//        Source: kisanalert/src/forecasting/multi_day_forecast.py
//
//   POST /api/v1/voice/query
//        Body: { "query": "MSP किती आहे?", "commodity": "Soybean" }
//        Returns: { "marathi_response": "...", "english_response": "..." }
//        Source: kisanalert/src/voice/gemini_voice.py
//        Needs: GEMINI_API_KEY in .env (falls back to rules if missing)
//
//   GET  /api/v1/alerts/latest?commodity=Soybean&district=Nanded
//        Now also returns: rise_score (float), trend_is_rising (bool)
//
// ══════════════════════════════════════════════════════════════════
// INTEGRATION STATUS: ✅ Complete as of 2026-04-19
// flutter analyze: No issues found
// ══════════════════════════════════════════════════════════════════
