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
  final String alertLevel;
  final String message;
  final double msp;

  CropData({
    required this.name,
    required this.price,
    required this.crashScore,
    required this.alertLevel,
    required this.message,
    required this.msp,
  });
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
}
