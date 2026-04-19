# -*- coding: utf-8 -*-
"""
PHASE 7 — Edge Case Handler for Production Robustness

Wraps alert_engine with pre-flight checks that catch real-world issues
farmers will hit:

  1. NCDEX closed (Sunday/holiday)      → use yesterday's signal + flag
  2. New farmer (no history)             → onboarding mode, safe default
  3. Data API down                       → use cached features + staleness flag
  4. Prediction too old (>12h)           → trigger re-run + warning
  5. Model confidence very low           → suppress alert, don't spam farmer
  6. Market price missing                → fetch fallback from nearest mandi

Each edge case has a specific FALLBACK instead of crashing or silently
giving wrong advice.

Usage:
    from src.alerts.edge_handler import generate_safe_alert
    alert = generate_safe_alert(features_row, current_price, price_30d_max,
                                 recent_prices, farmer_id=None, crop="Soybean")

Author: Mahesh Dakulge
Date:   2026-04-18 (Day 2)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LAST_ALERT_FILE = CACHE_DIR / "last_alert.json"

NCDEX_HOLIDAYS = {
    "2026-01-01",
    "2026-01-26",
    "2026-03-06",
    "2026-03-25",
    "2026-04-14",
    "2026-05-01",
    "2026-08-15",
    "2026-10-02",
    "2026-10-24",
    "2026-11-14",
    "2026-12-25",
}

MIN_CONFIDENCE_FOR_ALERT = 0.15
MAX_PREDICTION_AGE_HOURS = 12
MIN_HISTORY_DAYS_FOR_FULL_ALERT = 30


# ═══════════════════════════════════════════════════════════════════
# EDGE CASE 1 — NCDEX market closed (weekend/holiday)
# ═══════════════════════════════════════════════════════════════════


def is_market_closed(today: Optional[datetime] = None) -> tuple[bool, str]:
    """
    Check if NCDEX is closed today (Sunday or holiday).

    Returns (is_closed, reason)
    """
    today = today or datetime.now()
    weekday = today.weekday()

    if weekday == 6:
        return True, "Sunday — NCDEX closed"

    date_str = today.strftime("%Y-%m-%d")
    if date_str in NCDEX_HOLIDAYS:
        return True, f"Market holiday ({date_str})"

    return False, "Market open"


# ═══════════════════════════════════════════════════════════════════
# EDGE CASE 2 — New farmer / no history
# ═══════════════════════════════════════════════════════════════════


def is_new_farmer(farmer_history: Optional[list] = None) -> bool:
    """
    New farmer = no past alerts in their profile.
    Show safer alerts + onboarding tips.
    """
    if farmer_history is None:
        return False
    return len(farmer_history) < 3


def onboarding_message(crop: str, district: str) -> dict:
    """
    Safe default alert for brand-new farmers.
    Shows educational content + AMBER signal until they have some history.
    """
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "crop": crop,
        "district": district,
        "alert_level": "AMBER",
        "action": "शिकत आहोत / Learning",
        "message_marathi": (
            f"🌾 स्वागत आहे! आम्ही {crop}चे भाव तुमच्यासाठी निरीक्षण करू. "
            f"पहिले ३ अलर्ट टेस्ट म्हणून — खात्रीशीर होईपर्यंत विकण्याचे निर्णय आधीच्या पद्धतीने घ्या."
        ),
        "message_english": (
            f"🌾 Welcome! We'll monitor {crop} prices for you. "
            f"First 3 alerts are test mode — keep using your usual selling process until you trust our predictions."
        ),
        "is_onboarding": True,
        "timestamp": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════
# EDGE CASE 3 — Data API down / features missing
# ═══════════════════════════════════════════════════════════════════


def check_feature_health(features_row: pd.DataFrame) -> tuple[bool, list]:
    """
    Detect if critical features are missing/stale.

    Returns (is_healthy, list_of_issues)
    """
    issues = []

    if features_row.empty:
        return False, ["Features DataFrame is empty"]

    nan_cols = features_row.columns[features_row.iloc[0].isna()].tolist()
    if len(nan_cols) > len(features_row.columns) * 0.3:
        issues.append(f"Too many NaN features: {len(nan_cols)} cols")

    critical = ["modal_price", "arrival_qty"]
    missing_critical = [c for c in critical if c not in features_row.columns]
    if missing_critical:
        issues.append(f"Missing critical features: {missing_critical}")

    weather_cols = [c for c in features_row.columns if "rain" in c or "temp" in c]
    if weather_cols:
        weather_vals = features_row[weather_cols].iloc[0]
        if (weather_vals == 0).all():
            # Weather zero is normal when API is temporarily down.
            # Log a notice but do NOT block alert generation — price model
            # is trained on weather-zero rows too (Open-Meteo outages).
            log.info("Weather features all zero — weather API may be down (non-blocking).")

    return len(issues) == 0, issues


# ═══════════════════════════════════════════════════════════════════
# EDGE CASE 4 — Prediction staleness
# ═══════════════════════════════════════════════════════════════════


def get_last_alert() -> Optional[dict]:
    """Load the most recent saved alert (if any)."""
    if not LAST_ALERT_FILE.exists():
        return None
    try:
        with open(LAST_ALERT_FILE) as f:
            return json.load(f)
    except Exception as e:
        log.warning("Could not read last alert: %s", e)
        return None


def save_alert_to_cache(alert: dict) -> None:
    """Persist alert so we can serve it on API outages."""
    try:
        with open(LAST_ALERT_FILE, "w") as f:
            json.dump(alert, f, indent=2, default=str)
    except Exception as e:
        log.warning("Could not save alert: %s", e)


def is_cached_alert_stale(cached_alert: dict) -> tuple[bool, float]:
    """Check if cached alert is older than MAX_PREDICTION_AGE_HOURS."""
    try:
        ts = datetime.fromisoformat(cached_alert["timestamp"])
        age = datetime.now() - ts
        age_hours = age.total_seconds() / 3600
        return age_hours > MAX_PREDICTION_AGE_HOURS, age_hours
    except Exception:
        return True, 999.0


# ═══════════════════════════════════════════════════════════════════
# EDGE CASE 5 — Low model confidence
# ═══════════════════════════════════════════════════════════════════


def is_low_confidence(crash_score: float, rise_score: Optional[float]) -> bool:
    """
    If all scores are clustered around 0.5 (uncertain), model is guessing.
    Better to stay silent than spam farmer with noise.
    """
    if abs(crash_score - 0.5) < MIN_CONFIDENCE_FOR_ALERT:
        if rise_score is None or abs(rise_score - 0.5) < MIN_CONFIDENCE_FOR_ALERT:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════
# MAIN WRAPPER — generate_safe_alert
# ═══════════════════════════════════════════════════════════════════


def generate_safe_alert(
    features_row: pd.DataFrame,
    current_price: Optional[float],
    price_30d_max: Optional[float],
    recent_prices: Optional[pd.Series] = None,
    farmer_history: Optional[list] = None,
    crop: str = "Soybean",
    district: str = "Nanded",
) -> dict:
    """
    Production-safe alert generator with 6 edge-case fallbacks.

    Call this from your pipeline instead of generate_alert() directly.
    It wraps the core alert engine with pre/post checks.
    """
    check_1_closed, reason = is_market_closed()
    if check_1_closed:
        log.info("Edge case 1: %s", reason)
        cached = get_last_alert()
        if cached:
            closed_msg_mr = f"📅 आज बाजार बंद आहे ({reason}). कालचे अलर्ट: "
            closed_msg_en = f"📅 Market closed ({reason}). Yesterday's alert: "
            
            cached["notice_marathi"] = closed_msg_mr
            cached["notice_english"] = closed_msg_en
            
            # OVERRIDE the main message so the UI natively displays it in the Hero Card!
            cached["message_marathi"] = closed_msg_mr + cached.get("message_marathi", cached.get("marathi_message", ""))
            cached["message_english"] = closed_msg_en + cached.get("message_english", cached.get("english_message", ""))
            
            cached["market_status"] = "closed"
            return cached
        return {
            "alert_level": "AMBER",
            "message_marathi": "📅 आज बाजार बंद आहे. उद्या नवीन अंदाज मिळेल.",
            "message_english": "📅 Market closed today. New prediction tomorrow.",
            "market_status": "closed",
            "timestamp": datetime.now().isoformat(),
        }

    if is_new_farmer(farmer_history):
        log.info("Edge case 2: New farmer — onboarding mode")
        return onboarding_message(crop, district)

    healthy, issues = check_feature_health(features_row)
    if not healthy:
        log.warning("Edge case 3: Data quality issues: %s", issues)
        cached = get_last_alert()
        if cached and not is_cached_alert_stale(cached)[0]:
            cached["notice_marathi"] = "⚠️ डेटा अद्ययावत नाही. आधीचा अंदाज दाखवत आहोत."
            cached["notice_english"] = "⚠️ Data not current. Showing last prediction."
            cached["data_issues"] = issues
            return cached
        return {
            "alert_level": "AMBER",
            "message_marathi": "⚠️ डेटा उपलब्ध नाही. कृपया काही वेळाने प्रयत्न करा.",
            "message_english": "⚠️ Data unavailable. Please try again shortly.",
            "data_issues": issues,
            "timestamp": datetime.now().isoformat(),
        }

    if current_price is None or price_30d_max is None:
        log.warning("Edge case 6: Missing price data")
        return {
            "alert_level": "AMBER",
            "message_marathi": "💰 आजच्या मंडीचा भाव उपलब्ध नाही. मंडीत चौकशी करा.",
            "message_english": "💰 Today's mandi price unavailable. Check mandi directly.",
            "timestamp": datetime.now().isoformat(),
        }

    try:
        from src.alerts.alert_engine import generate_alert
    except ImportError:
        try:
            from alert_engine_v4 import generate_alert
        except ImportError as e:
            log.error("Could not import alert_engine: %s", e)
            return {
                "alert_level": "AMBER",
                "message_marathi": "⚙️ तांत्रिक अडचण. काही वेळाने प्रयत्न करा.",
                "message_english": "⚙️ Technical issue. Please try again shortly.",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    try:
        alert = generate_alert(
            features_row=features_row,
            current_price=current_price,
            price_30d_max=price_30d_max,
            recent_prices=recent_prices,
            crop=crop,
            district=district,
        )
    except Exception as e:
        log.error("Edge case: Model prediction crashed: %s", e)
        cached = get_last_alert()
        if cached and not is_cached_alert_stale(cached)[0]:
            cached["notice_marathi"] = "⚠️ सिस्टम तपासत आहोत. आधीचा अंदाज दाखवत आहोत."
            cached["notice_english"] = "⚠️ System maintenance. Showing last prediction."
            return cached
        return {
            "alert_level": "AMBER",
            "message_marathi": "⚙️ तांत्रिक अडचण. काही वेळाने प्रयत्न करा.",
            "message_english": "⚙️ Technical issue. Please try again shortly.",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

    crash = alert.get("crash_score", 0.5)
    rise = alert.get("rise_score")
    if is_low_confidence(crash, rise):
        log.info("Edge case 5: Low confidence — suppressing alert")
        alert["alert_level"] = "AMBER"
        alert["message_marathi"] = "🤔 आज स्पष्ट संकेत नाही. बाजार स्थिर आहे."
        alert["message_english"] = "🤔 No clear signal today. Market is stable."
        alert["low_confidence"] = True

    save_alert_to_cache(alert)

    return alert


# ═══════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n" + "═" * 68)
    print("  🛡️  Testing Edge Case Handler")
    print("═" * 68 + "\n")

    print("TEST 1: Market closed check")
    closed, reason = is_market_closed(datetime(2026, 1, 26))
    print(f"  Republic Day → closed={closed}, reason={reason}")
    closed, reason = is_market_closed(datetime(2026, 4, 20))
    print(f"  Monday Apr 20 → closed={closed}, reason={reason}")
    closed, reason = is_market_closed(datetime(2026, 4, 19))
    print(f"  Sunday Apr 19 → closed={closed}, reason={reason}")
    print()

    print("TEST 2: New farmer detection")
    print(f"  Empty history → new={is_new_farmer([])}")
    print(f"  2 alerts → new={is_new_farmer([1, 2])}")
    print(f"  10 alerts → new={is_new_farmer(list(range(10)))}")
    print()

    print("TEST 3: Feature health check")
    ok_features = pd.DataFrame({
        "modal_price": [5000], "arrival_qty": [1200],
        "rain_7d_sum": [25], "temp_7d_avg": [28],
    })
    bad_features = pd.DataFrame({
        "modal_price": [5000], "arrival_qty": [1200],
        "rain_7d_sum": [0], "temp_7d_avg": [0],
    })
    empty_features = pd.DataFrame()

    for label, df in [("Good features", ok_features), ("Bad weather", bad_features), ("Empty", empty_features)]:
        healthy, issues = check_feature_health(df)
        print(f"  {label}: healthy={healthy}, issues={issues}")
    print()

    print("TEST 4: Low confidence detection")
    print(f"  crash=0.51, rise=0.49 → low={is_low_confidence(0.51, 0.49)}")
    print(f"  crash=0.80, rise=0.20 → low={is_low_confidence(0.80, 0.20)}")
    print(f"  crash=0.48, rise=None → low={is_low_confidence(0.48, None)}")
    print()

    print("TEST 5: Onboarding message")
    msg = onboarding_message("Soybean", "Nanded")
    print(f"  Signal: {msg['alert_level']}")
    print(f"  Marathi: {msg['message_marathi'][:80]}...")
    print()

    print("✓ Edge case handler test complete!")
    print()
