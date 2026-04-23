import 'dart:convert';
import 'package:http/http.dart' as http;

// Use --dart-define=API_URL=https://your-cloud-run-url.run.app/api/v1 to override
const String _baseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://127.0.0.1:8000/api/v1', // 127.0.0.1 maps to host via ADB reverse for physical devices
);

// ── Data Models ────────────────────────────────────────────────────────────────

class CropData {
  final String name;
  final double price;
  final double crashScore;
  final double riseScore;
  final bool trendIsRising;
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

class ForecastPoint {
  final String date;
  final double price;
  final bool isActual;
  ForecastPoint({required this.date, required this.price, required this.isActual});
}

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

class ForecastData {
  final double currentPrice;
  final String currentDate;
  final List<ForecastPoint> past7Days;
  final List<ForecastPredicted> next10Days;
  final double day3Predicted;
  final double day3ChangePct;
  final double day10Predicted;
  final double day10ChangePct;
  final String trend;

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

class AccuracyStats {
  final int total;
  final int correct;
  final double accuracy;
  AccuracyStats({required this.total, required this.correct, required this.accuracy});

  factory AccuracyStats.fromJson(Map<String, dynamic> j) {
    final stats = j['stats'] ?? j;
    return AccuracyStats(
      total: (stats['total'] as num?)?.toInt() ?? 0,
      correct: (stats['correct'] as num?)?.toInt() ?? 0,
      accuracy: (stats['accuracy'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class MandiData {
  final String name;
  final int distanceKm;
  final double soybeanPrice;
  final double cottonPrice;
  final double turmericPrice;
  final String signal; // GREEN, AMBER, RED
  final String weather;
  final String advice;
  final bool isBest;

  MandiData({
    required this.name,
    required this.distanceKm,
    required this.soybeanPrice,
    required this.cottonPrice,
    required this.turmericPrice,
    required this.signal,
    required this.weather,
    required this.advice,
    this.isBest = false,
  });

  double priceForCrop(String crop) {
    switch (crop) {
      case 'Cotton': return cottonPrice;
      case 'Turmeric': return turmericPrice;
      default: return soybeanPrice;
    }
  }
}

class Signal {
  final String label;
  final String level; // RED, AMBER, GREEN
  final String explanation;
  final String marathi;
  Signal({required this.label, required this.level, required this.explanation, required this.marathi});
}

class ForecastDay {
  final String dayEn;
  final String dayMr;
  final double price;
  final String direction; // up, down, stable
  final String risk; // RED, AMBER, GREEN, BEST
  ForecastDay({required this.dayEn, required this.dayMr, required this.price, required this.direction, required this.risk});
}

class CommunityStory {
  final String initials;
  final String avatarColor; // green, amber, blue
  final String nameEn;
  final String distanceKm;
  final String messageMr;
  final String messageEn;
  final bool isVerified;
  final String verifiedDate;
  final String crop;
  final String saved;
  CommunityStory({
    required this.initials,
    required this.avatarColor,
    required this.nameEn,
    required this.distanceKm,
    required this.messageMr,
    required this.messageEn,
    required this.isVerified,
    required this.verifiedDate,
    required this.crop,
    required this.saved,
  });
}



// ── Static Data ────────────────────────────────────────────────────────────────



final List<Signal> activeSignals = [];

final List<ForecastDay> forecastDays = [];

final List<CommunityStory> communityStories = [];

// ── API Service ────────────────────────────────────────────────────────────────

class ApiService {
  static Future<Map<String, dynamic>?> getLatestAlert(String commodity, String district) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/alerts/latest?commodity=$commodity&district=$district'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return null;
  }

  static Future<List<dynamic>> getMandisCompare(String commodity) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/mandis/compare?commodity=$commodity'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return [];
  }

  static Future<List<dynamic>> getAlertHistory(String commodity, {int limit = 7}) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/alerts/history?commodity=$commodity&district=Nanded&limit=$limit'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return [];
  }

  static Future<Map<String, dynamic>?> getWeather(String district) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/weather/current?district=$district'),
      ).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return null;
  }

  static Future<List<dynamic>> getCommunityStories(String commodity) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/community/stories?commodity=$commodity'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return [];
  }

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

  static Future<Map<String, dynamic>?> getAccuracy(String commodity) async {
    try {
      final rootUrl = _baseUrl.replaceAll('/api/v1', '');
      final res = await http.get(
        Uri.parse('$rootUrl/accuracy?crop=$commodity&days=180'),
      ).timeout(const Duration(seconds: 8));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return null;
  }

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

  static Future<AccuracyStats?> getAccuracyStats({int days = 30}) async {
    try {
      final rootUrl = _baseUrl.replaceAll('/api/v1', '');
      final res = await http.get(
        Uri.parse('$rootUrl/accuracy?days=$days'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return AccuracyStats.fromJson(json.decode(res.body));
      }
    } catch (_) {}
    return null;
  }

  /// Fetches the Gemini-powered structured daily briefing for the Advisor screen.
  /// Returns: {trend, decision, ncdex, profit_tip, signal_emoji, alert_level, price, source}
  static Future<Map<String, dynamic>?> getGeminiAdvisory(String commodity) async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/gemini/advisory?commodity=$commodity&district=Nanded'),
      ).timeout(const Duration(seconds: 20));
      if (res.statusCode == 200) {
        return json.decode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  /// Returns real-time farmer impact stats for the Profile screen.
  static Future<Map<String, dynamic>?> getFarmerStats() async {
    try {
      final res = await http.get(
        Uri.parse('$_baseUrl/farmer/stats'),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) return json.decode(res.body);
    } catch (_) {}
    return null;
  }
}
