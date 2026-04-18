# -*- coding: utf-8 -*-
"""
PHASE 6 (v2) — 4-Signal Alert Engine 🔴🔵🟢🟡

Upgrade from 3-signal to 4-signal system.
Combines crash predictor + rise predictor + price-peak detector
into a single actionable alert for farmers.

Signals:
  🔴 RED   — Crash predicted → "Don't sell, crash coming"
  🔵 BLUE  — Rise predicted  → "Hold, price rising"
  🟢 GREEN — At 30-day peak  → "Sell today, best price"
  🟡 AMBER — Stable/uncertain → "Farmer's choice"

Author: Mahesh Dakulge
Date:   2026-04-18 (Day 2)
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

# Model paths
CRASH_MODEL_PATH = "models/saved/xgb_v3_best.json"
RISE_MODEL_PATH = "models/saved/xgb_blue_signal.json"

# Alert thresholds
CRASH_THRESHOLD = 0.65          # crash_score > this → RED
STRONG_RISE_THRESHOLD = 0.60    # rise_score > this → BLUE
PEAK_THRESHOLD = 0.97           # current price >= 97% of 30-day max → GREEN
LOW_RISK_CEILING = 0.35         # below this = safe


# ═══════════════════════════════════════════════════════════════════
# MARATHI MESSAGES
# ═══════════════════════════════════════════════════════════════════

MESSAGES = {
    "RED": {
        "marathi": "⚠️ सावधान! {days} दिवसात भाव पडण्याचा अंदाज. आजच विक्री थांबवा!",
        "english": "⚠️ Warning! Price crash predicted in {days} days. Stop selling today!",
        "action": "विकू नका / Don't sell",
    },
    "BLUE": {
        "marathi": "💎 थांबा! {days} दिवसात भाव वाढणार. आज विकणे टाळा.",
        "english": "💎 Hold! Price will rise in {days} days. Avoid selling today.",
        "action": "थांबा / Hold",
    },
    "GREEN": {
        "marathi": "✅ आजच विका! {days} दिवसांतील सर्वोच्च भाव आहे.",
        "english": "✅ Sell today! This is the highest price in {days} days.",
        "action": "विका / Sell",
    },
    "AMBER": {
        "marathi": "🟡 भाव स्थिर आहे. आपल्या गरजेनुसार निर्णय घ्या.",
        "english": "🟡 Price is stable. Decide based on your needs.",
        "action": "तुमची निवड / Your choice",
    },
}


# ═══════════════════════════════════════════════════════════════════
# MODEL LOADING (singleton pattern — load once, reuse)
# ═══════════════════════════════════════════════════════════════════

_crash_model: Optional[xgb.XGBClassifier] = None
_rise_model: Optional[xgb.XGBClassifier] = None


def load_models() -> tuple[xgb.XGBClassifier, Optional[xgb.XGBClassifier]]:
    """Load crash + rise models (rise is optional — falls back to 3-signal)."""
    global _crash_model, _rise_model

    if _crash_model is None:
        if not Path(CRASH_MODEL_PATH).exists():
            raise FileNotFoundError(
                f"Crash model missing at {CRASH_MODEL_PATH}. Run fix_auc_v2.py first."
            )
        _crash_model = xgb.XGBClassifier()
        _crash_model.load_model(CRASH_MODEL_PATH)
        log.info("Loaded crash model: %s", CRASH_MODEL_PATH)

    if _rise_model is None:
        if Path(RISE_MODEL_PATH).exists():
            _rise_model = xgb.XGBClassifier()
            _rise_model.load_model(RISE_MODEL_PATH)
            log.info("Loaded rise model: %s", RISE_MODEL_PATH)
        else:
            log.warning(
                "Rise model not found at %s — BLUE signal disabled. "
                "Run train_blue_model.py to enable.",
                RISE_MODEL_PATH,
            )

    return _crash_model, _rise_model


# ═══════════════════════════════════════════════════════════════════
# SIGNAL LOGIC
# ═══════════════════════════════════════════════════════════════════

def classify_signal(
    crash_score: float,
    rise_score: Optional[float],
    current_price: float,
    price_30d_max: float,
) -> str:
    """
    Decide which of the 4 signals to fire.

    Priority order (first match wins):
      1. RED   — crash predicted AND not at peak
      2. GREEN — at or near 30-day peak (sell while high)
      3. BLUE  — rise predicted AND not crashing
      4. AMBER — everything else

    Args:
        crash_score: output from crash model (0-1)
        rise_score:  output from rise model (0-1), or None if unavailable
        current_price: today's modal price
        price_30d_max: rolling 30-day max

    Returns:
        One of "RED", "BLUE", "GREEN", "AMBER"
    """
    at_peak = current_price >= PEAK_THRESHOLD * price_30d_max

    if crash_score >= CRASH_THRESHOLD:
        return "RED"

    if at_peak and crash_score < LOW_RISK_CEILING:
        return "GREEN"

    if (
        rise_score is not None
        and rise_score >= STRONG_RISE_THRESHOLD
        and crash_score < LOW_RISK_CEILING
    ):
        return "BLUE"

    return "AMBER"


# ═══════════════════════════════════════════════════════════════════
# MAIN ALERT GENERATION
# ═══════════════════════════════════════════════════════════════════

def generate_alert(
    features_row: pd.DataFrame,
    current_price: float,
    price_30d_max: float,
    crop: str = "Soybean",
    district: str = "Nanded",
    window_days: int = 7,
) -> dict:
    """
    Generate a 4-signal alert for one day of data.

    Args:
        features_row: single-row DataFrame matching model input features
        current_price: modal_price for today
        price_30d_max: max price over past 30 days
        crop: crop name (for message)
        district: district name (for message)
        window_days: forecast horizon for message

    Returns:
        dict with keys: date, crop, district, modal_price, crash_score,
                        rise_score, alert_level, action_marathi,
                        message_marathi, message_english, timestamp
    """
    crash_model, rise_model = load_models()

    crash_score = float(crash_model.predict_proba(features_row)[0, 1])

    rise_score = None
    if rise_model is not None:
        try:
            rise_score = float(rise_model.predict_proba(features_row)[0, 1])
        except Exception as e:
            log.warning("Rise model prediction failed: %s", e)

    signal = classify_signal(crash_score, rise_score, current_price, price_30d_max)

    msg_template = MESSAGES[signal]

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "crop": crop,
        "district": district,
        "modal_price": round(float(current_price), 2),
        "price_30d_max": round(float(price_30d_max), 2),
        "crash_score": round(crash_score, 4),
        "rise_score": round(rise_score, 4) if rise_score is not None else None,
        "alert_level": signal,
        "action": msg_template["action"],
        "message_marathi": msg_template["marathi"].format(days=window_days),
        "message_english": msg_template["english"].format(days=window_days),
        "timestamp": datetime.now().isoformat(),
        "model_version": "v2_4signal",
    }


# ═══════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n" + "═" * 68)
    print("  🎯 Testing 4-Signal Alert Engine")
    print("═" * 68 + "\n")

    test_cases = [
        ("RED (crash)",       0.80, 0.20, 4500, 5200),
        ("BLUE (rise)",       0.20, 0.75, 4500, 5200),
        ("GREEN (at peak)",   0.15, 0.25, 5100, 5200),
        ("AMBER (stable)",    0.40, 0.40, 4800, 5200),
        ("AMBER (rise+risk)", 0.45, 0.70, 4800, 5200),
    ]

    for label, crash, rise, price, peak in test_cases:
        signal = classify_signal(crash, rise, price, peak)
        msg = MESSAGES[signal]
        at_peak_pct = 100 * price / peak
        print(f"  {label:22s} → crash={crash:.2f} rise={rise:.2f} "
              f"peak={at_peak_pct:.0f}% → {signal}")
        print(f"    Action: {msg['action']}")
        print(f"    {msg['marathi'].format(days=7)}")
        print()

    print("✓ Alert engine test complete!")
    print()
