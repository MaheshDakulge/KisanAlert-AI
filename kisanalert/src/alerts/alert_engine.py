# -*- coding: utf-8 -*-
"""
PHASE 6 (v4) — Final 4-Signal Alert Engine 🔴🔵🟢🟡

Production-ready with both models at strong AUC:
  - Crash model: 0.7632 test AUC
  - Rise model:  0.6972 test AUC

BLUE threshold LOWERED from 0.70 → 0.60 since rise model is
now credible. Trend-rising filter retained as safety rail.

Signal logic (priority order):
  1. RED   — crash_score ≥ 0.65
  2. GREEN — at 30-day peak AND low crash
  3. BLUE  — rise_score ≥ 0.60 AND trend rising AND low crash
  4. AMBER — default

Author: Mahesh Dakulge
Date:   2026-04-18 (Day 2 — BLUE boosted)
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


RISE_MODEL_PATH = "models/saved/xgb_blue_signal.json"


def _get_crash_model_path() -> str:
    """
    Returns the correct crop-specific crash model path (absolute).
    Priority:
      1. xgb_v1_{crop}.json  (crop-specific trained model)
      2. xgb_v3_best.json    (Soybean-only fallback)
    """
    import sys
    from pathlib import Path
    # Resolve models dir relative to this file: alert_engine.py → src/alerts/ → kisanalert/ → models/saved/
    base_dir = Path(__file__).resolve().parents[2]
    models_dir = base_dir / "models" / "saved"
    sys.path.insert(0, str(base_dir))
    try:
        import config
        crop = config.TARGET_COMMODITY.lower()
        crop_path = models_dir / f"xgb_v1_{crop}.json"
        if crop_path.exists():
            return str(crop_path)
        # Soybean fallback to v3 best
        if crop == "soybean":
            v3 = models_dir / "xgb_v3_best.json"
            if v3.exists():
                return str(v3)
    except Exception:
        pass
    return str(models_dir / "xgb_v3_best.json")

# Trust-adjusted thresholds
CRASH_THRESHOLD = 0.65          # crash > this → RED
BLUE_THRESHOLD = 0.60           # rise > this AND trend rising → BLUE
BLUE_SAFE_CRASH_CEIL = 0.35     # must have low crash risk for BLUE
PEAK_THRESHOLD = 0.97           # at 97% of 30d max → GREEN
LOW_RISK_CEILING = 0.35

# Forecast horizons (matches training windows)
CRASH_WINDOW_DAYS = 7
RISE_WINDOW_DAYS = 10


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
        "english": "✅ Sell today! Highest price in {days} days.",
        "action": "विका / Sell",
    },
    "AMBER": {
        "marathi": "🟡 भाव स्थिर आहे. आपल्या गरजेनुसार निर्णय घ्या.",
        "english": "🟡 Price is stable. Decide based on your needs.",
        "action": "तुमची निवड / Your choice",
    },
}


_crash_model: Optional[xgb.XGBClassifier] = None
_crash_model_path_loaded: str = ""
_rise_model: Optional[xgb.XGBClassifier] = None


def load_models() -> tuple[xgb.XGBClassifier, Optional[xgb.XGBClassifier]]:
    """Load both models. Rise model is optional (falls back to 3-signal).
    
    Crash model is resolved dynamically per-crop so Cotton/Turmeric/Soybean
    each get their own trained model instead of sharing xgb_v3_best.json.
    """
    global _crash_model, _crash_model_path_loaded, _rise_model

    # Resolve correct path for the current crop
    crash_model_path = _get_crash_model_path()

    # Reload crash model if crop has changed since last call
    if _crash_model is None or crash_model_path != _crash_model_path_loaded:
        if not Path(crash_model_path).exists():
            raise FileNotFoundError(
                f"Crash model missing at {crash_model_path}. Run training first."
            )
        _crash_model = xgb.XGBClassifier()
        _crash_model.load_model(crash_model_path)
        _crash_model_path_loaded = crash_model_path
        log.info("Loaded crash model: %s", crash_model_path)

    if _rise_model is None:
        if Path(RISE_MODEL_PATH).exists():
            _rise_model = xgb.XGBClassifier()
            _rise_model.load_model(RISE_MODEL_PATH)
            log.info("Loaded rise model (AUC 0.70): %s", RISE_MODEL_PATH)
        else:
            log.warning(
                "Rise model not found at %s — BLUE signal disabled.",
                RISE_MODEL_PATH,
            )

    return _crash_model, _rise_model


def classify_signal(
    crash_score: float,
    rise_score: Optional[float],
    current_price: float,
    price_30d_max: float,
    trend_is_rising: bool = False,
) -> str:
    """
    Decide which of the 4 signals to fire.

    Priority (first match wins):
      1. RED   — crash_score >= 0.65
      2. GREEN — at 30-day peak AND low crash risk
      3. BLUE  — rise_score >= 0.60 AND trend rising AND low crash risk
      4. AMBER — everything else
    """
    at_peak = current_price >= PEAK_THRESHOLD * price_30d_max

    if crash_score >= CRASH_THRESHOLD:
        return "RED"

    if at_peak and crash_score < LOW_RISK_CEILING:
        return "GREEN"

    blue_fires = (
        rise_score is not None
        and rise_score >= BLUE_THRESHOLD
        and crash_score < BLUE_SAFE_CRASH_CEIL
        and trend_is_rising
    )
    if blue_fires:
        return "BLUE"

    return "AMBER"


def compute_trend_is_rising(recent_prices: pd.Series) -> bool:
    """7-day MA > 14-day MA = upward trend."""
    if len(recent_prices) < 14:
        return False
    return recent_prices.tail(7).mean() > recent_prices.tail(14).mean()


def pick_window_days(signal: str) -> int:
    """Return forecast window that matches model training."""
    if signal == "RED":
        return CRASH_WINDOW_DAYS
    if signal == "BLUE":
        return RISE_WINDOW_DAYS
    return CRASH_WINDOW_DAYS


def generate_alert(
    features_row: pd.DataFrame,
    current_price: float,
    price_30d_max: float,
    recent_prices: Optional[pd.Series] = None,
    crop: str = "Soybean",
    district: str = "Nanded",
) -> dict:
    """
    Generate a 4-signal alert for one day of data.
    
    Returns a dict with full prediction details + Marathi message.
    """
    crash_model, rise_model = load_models()

    # 1. Crash model prediction (filter features)
    crash_feats = crash_model.get_booster().feature_names
    if crash_feats is not None:
        X_crash = features_row.reindex(columns=list(crash_feats), fill_value=0.0)
    else:
        X_crash = features_row
    
    crash_score = float(crash_model.predict_proba(X_crash)[0, 1])

    # 2. Rise model prediction (filter features)
    rise_score = None
    if rise_model is not None:
        try:
            rise_feats = rise_model.get_booster().feature_names
            if rise_feats is not None:
                X_rise = features_row.reindex(columns=list(rise_feats), fill_value=0.0)
            else:
                X_rise = features_row
            rise_score = float(rise_model.predict_proba(X_rise)[0, 1])
        except Exception as e:
            log.warning("Rise model prediction failed: %s", e)

    trend_rising = False
    if recent_prices is not None and len(recent_prices) >= 14:
        trend_rising = compute_trend_is_rising(recent_prices)

    signal = classify_signal(
        crash_score=crash_score,
        rise_score=rise_score,
        current_price=current_price,
        price_30d_max=price_30d_max,
        trend_is_rising=trend_rising,
    )

    window_days = pick_window_days(signal)
    msg_template = MESSAGES[signal]

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "crop": crop,
        "district": district,
        "modal_price": round(float(current_price), 2),
        "price_30d_max": round(float(price_30d_max), 2),
        "pct_of_peak": round(100 * current_price / price_30d_max, 1),
        "crash_score": round(crash_score, 4),
        "rise_score": round(rise_score, 4) if rise_score is not None else None,
        "trend_is_rising": trend_rising,
        "alert_level": signal,
        "forecast_days": window_days,
        "action": msg_template["action"],
        "message_marathi": msg_template["marathi"].format(days=window_days),
        "message_english": msg_template["english"].format(days=window_days),
        "timestamp": datetime.now().isoformat(),
        "model_version": "v4_final4signal",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n" + "═" * 68)
    print("  🎯 Testing FINAL 4-Signal Alert Engine (v4)")
    print("  Crash AUC 0.76 · Rise AUC 0.70")
    print("═" * 68 + "\n")

    # (label, crash, rise, price, peak, trend_rising)
    test_cases = [
        ("RED (strong crash)",         0.80, 0.20, 4500, 5200, False),
        ("RED overrides GREEN",        0.80, 0.20, 5100, 5200, False),
        ("BLUE (strong rise+trend)",   0.15, 0.70, 4500, 5200, True),
        ("BLUE triggers at 0.60",      0.20, 0.62, 4500, 5200, True),
        ("BLUE fails (weak rise)",     0.15, 0.55, 4500, 5200, True),
        ("BLUE fails (no trend)",      0.15, 0.75, 4500, 5200, False),
        ("GREEN (at peak)",            0.15, 0.25, 5100, 5200, False),
        ("AMBER (stable)",             0.40, 0.45, 4800, 5200, False),
        ("AMBER (mixed signals)",      0.45, 0.70, 4800, 5200, True),
    ]

    for label, crash, rise, price, peak, trend in test_cases:
        signal = classify_signal(crash, rise, price, peak, trend)
        msg = MESSAGES[signal]
        at_peak_pct = 100 * price / peak
        trend_str = "↑ rising" if trend else "↓ flat"
        window = pick_window_days(signal)
        print(f"  {label:30s}")
        print(f"    crash={crash:.2f}  rise={rise:.2f}  peak={at_peak_pct:.0f}%  trend={trend_str}")
        print(f"    → {signal}  ({msg['action']})")
        print(f"    {msg['marathi'].format(days=window)}")
        print()

    print("✓ v4 Alert engine test complete!")
    print()
