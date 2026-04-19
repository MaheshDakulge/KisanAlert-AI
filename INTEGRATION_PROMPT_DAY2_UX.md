# 🔧 KisanAlert Day 2 UX — Master Integration Prompt

Copy EVERYTHING below the ═══ markers into Antigravity.

═══════════════════════════════════════════════════════════════════

You are a senior engineer integrating the farmer-first home redesign
for KisanAlert v2.0 (Google Solution Challenge 2026).

═══════════════════════════════════════════════════════════════════
PROJECT ROOTS
═══════════════════════════════════════════════════════════════════

Backend : C:\FlutterDev\projects\Agri\kisanalert
Flutter : C:\FlutterDev\projects\Agri\kisanalert\kisanalert_app

═══════════════════════════════════════════════════════════════════
NEW FILES AVAILABLE (in kisanalert/ project root)
═══════════════════════════════════════════════════════════════════

  1. multi_day_forecast.py       → src/forecasting/multi_day_forecast.py
  2. gemini_voice.py             → src/voice/gemini_voice.py
  3. home_screen_v2.dart         → kisanalert_app/lib/screens/home_screen.dart (REPLACE)
  4. app_data_additions.dart     → reference for edits (do not copy whole)

═══════════════════════════════════════════════════════════════════
TASK LIST — EXECUTE IN ORDER
═══════════════════════════════════════════════════════════════════

TASK 1: Backup
───────────────
Create backups/2026-04-18_day2_ux/ and copy:
  - kisanalert_app/lib/screens/home_screen.dart
  - kisanalert_app/lib/data/app_data.dart
  - kisanalert_app/lib/state/app_state.dart
  - api.py

TASK 2: Install Backend Files
─────────────────────────────
- Create directory: src/forecasting/ (with __init__.py)
- Move multi_day_forecast.py → src/forecasting/multi_day_forecast.py
- Create directory: src/voice/ (with __init__.py)
- Move gemini_voice.py → src/voice/gemini_voice.py

TASK 3: Update api.py — Add 2 New Endpoints
───────────────────────────────────────────
At the top of api.py, add:

    from src.forecasting.multi_day_forecast import register_forecast_endpoint
    from src.voice.gemini_voice import register_gemini_endpoint

At the bottom of api.py (after all existing endpoints but before uvicorn run):

    register_forecast_endpoint(app)
    register_gemini_endpoint(app)

If there's already a /voice/query endpoint, REMOVE the old one first.

TASK 4: Update .env
───────────────────
Add this line to .env (if not already present):

    GEMINI_API_KEY=

Note: leave blank for now. User will fill in their key later.
The voice endpoint has a smart fallback so app still works without it.

TASK 5: Install google-generativeai
────────────────────────────────────
Run in terminal:
    pip install google-generativeai

Add to requirements.txt:
    google-generativeai>=0.3.0

TASK 6: Update Flutter — CropData Model
────────────────────────────────────────
File: kisanalert_app/lib/data/app_data.dart

Replace the existing CropData class with:

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

TASK 7: Flutter — Add Forecast + Accuracy Models
──────────────────────────────────────────────────
File: kisanalert_app/lib/data/app_data.dart

After CropData class, BEFORE ApiService class, add:

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

TASK 8: Flutter — Add ApiService Methods
─────────────────────────────────────────
File: kisanalert_app/lib/data/app_data.dart

Inside ApiService class, add these two methods:

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
          final res = await http.get(
            Uri.parse('$_baseUrl/accuracy?days=$days'),
          ).timeout(const Duration(seconds: 5));
          if (res.statusCode == 200) {
            return AccuracyStats.fromJson(json.decode(res.body));
          }
        } catch (_) {}
        return null;
      }

TASK 9: Flutter — Update AppState
──────────────────────────────────
File: kisanalert_app/lib/state/app_state.dart

At the top, add import:
    import 'dart:async';

Inside AppState class, add these fields + getters (after currentStories):

      ForecastData? _forecast;
      ForecastData? get forecast => _forecast;

      AccuracyStats? _accuracyStats;
      AccuracyStats? get accuracyStats => _accuracyStats;

      Timer? _weatherTimer;

Update fetchData() — in the section that creates CropData, ALSO parse
the new rise_score and trend_is_rising fields:

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

At the end of fetchData() try block (before catch), add:

      _forecast = await ApiService.getMultiDayForecast(_activeCrop);
      _accuracyStats = await ApiService.getAccuracyStats(days: 30);

In catch block, set to null:
      _forecast = null;
      _accuracyStats = null;

Add this method to AppState:

      void startAutoRefresh() {
        _weatherTimer?.cancel();
        _weatherTimer = Timer.periodic(const Duration(hours: 1), (_) {
          fetchData();
        });
      }

Override dispose:

      @override
      void dispose() {
        _weatherTimer?.cancel();
        super.dispose();
      }

TASK 10: Flutter — Replace home_screen.dart
────────────────────────────────────────────
File: kisanalert_app/lib/screens/home_screen.dart

COMPLETELY REPLACE with the contents of home_screen_v2.dart.

TASK 11: Flutter — Trigger Auto-Refresh in main.dart
─────────────────────────────────────────────────────
File: kisanalert_app/lib/main.dart

In _KisanAlertAppState.initState(), after _appState.addListener(...), add:
    _appState.startAutoRefresh();

TASK 12: Update api.py /alerts/latest
──────────────────────────────────────
Make sure the /alerts/latest endpoint returns rise_score and trend_is_rising.

If the current endpoint returns a dict, add these fields from the alert:
    "rise_score": alert.get("rise_score"),
    "trend_is_rising": alert.get("trend_is_rising", False),

TASK 13: Flutter Run & Test
───────────────────────────
Run in kisanalert_app directory:
    flutter pub get
    flutter analyze

Fix any errors it surfaces. Most common issue: missing imports.

Required imports in home_screen.dart:
    import 'package:fl_chart/fl_chart.dart';
    import 'package:google_fonts/google_fonts.dart';
    import '../theme/app_theme.dart';
    import '../state/app_state.dart';
    import '../data/app_data.dart';
    import '../widgets/shared_widgets.dart';

TASK 14: Verify Pipeline Still Works
─────────────────────────────────────
Run in kisanalert directory:
    python run_pipeline.py

Expected output must still show a successful alert.

TASK 15: Test New Endpoints
────────────────────────────
Start API:
    uvicorn api:app --reload

Test in another terminal:
    curl http://localhost:8000/api/v1/forecast/multi-day?commodity=Soybean
    curl -X POST http://localhost:8000/api/v1/voice/query \
         -H "Content-Type: application/json" \
         -d "{\"query\":\"MSP किती आहे?\"}"

Both should return JSON (no 500 errors).

═══════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════

1. DO NOT delete .env file
2. DO NOT modify raw data files
3. DO NOT remove existing screens (mandi, weather, predict, profile)
4. After each task, print: "✓ Task N complete"
5. If any task fails, STOP and report the exact error

═══════════════════════════════════════════════════════════════════
FINAL SUMMARY
═══════════════════════════════════════════════════════════════════

Print:

    ═════════════════════════════════════════════════
    ✅ Day 2 UX Integration Complete
    ═════════════════════════════════════════════════

    Backend endpoints added:
      GET  /api/v1/forecast/multi-day   — 10-day LSTM forecast
      POST /api/v1/voice/query          — Gemini Marathi voice Q&A

    Flutter changes:
      home_screen.dart         REPLACED (3-section farmer-first design)
      app_data.dart            UPDATED (CropData + 3 new models)
      app_state.dart           UPDATED (forecast + accuracy + auto-refresh)
      main.dart                UPDATED (auto-refresh trigger)

    Features added:
      ✓ BLUE signal displayed on home with "Hold" message
      ✓ Past 7 days (solid green) + Next 10 days (dashed blue) chart
      ✓ Simplified from 15 widgets to 4 sections
      ✓ Trust badge showing live accuracy
      ✓ Auto-refresh every 1 hour
      ✓ Real Gemini-powered voice (falls back to smart rules)

    To enable Gemini:
      1. Get free key: https://aistudio.google.com/app/apikey
      2. Add to .env: GEMINI_API_KEY=your_key
      3. Restart API

═══════════════════════════════════════════════════════════════════
END OF PROMPT
═══════════════════════════════════════════════════════════════════
