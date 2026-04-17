# -*- coding: utf-8 -*-
"""
PHASE 6 — Alert Engine
Converts crash probability score → GREEN / AMBER / RED alert
with Marathi message. Logs every alert.
"""

import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Ensure logs directory exists
config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

# File handler for alert log
_alert_handler = logging.FileHandler(config.LOG_ALERTS_FILE, encoding="utf-8")
_alert_handler.setLevel(logging.INFO)
_alert_logger = logging.getLogger("kisanalert.alerts")
_alert_logger.addHandler(_alert_handler)
_alert_logger.setLevel(logging.INFO)

ALERT_ICONS = {
    "GREEN": "🟢",
    "AMBER": "🟡",
    "RED"  : "🔴",
}


def _get_red_threshold() -> float:
    """Resolve RED threshold from tuned artifact with config fallback."""
    try:
        if config.TUNED_THRESHOLD_PATH.exists():
            return float(config.TUNED_THRESHOLD_PATH.read_text(encoding="utf-8").strip())
    except Exception as exc:
        log.warning("Unable to read tuned threshold, using config fallback: %s", exc)
    return float(config.ALERT_RED_MIN)


def score_to_alert(crash_score: float) -> dict:
    """
    Convert crash probability (0–1) to a structured alert dict.

    Thresholds:
      score < ALERT_GREEN_MAX  → GREEN
      score >= tuned_or_default_red_threshold → RED
      otherwise                → AMBER

    Boundary rules:
      score == ALERT_GREEN_MAX → AMBER  (not GREEN)
      score == red_threshold   → RED    (not AMBER)
    """
    score = float(crash_score)  # ensure Python native float

    red_threshold = _get_red_threshold()

    if score < config.ALERT_GREEN_MAX:
        level = "GREEN"
    elif score >= red_threshold:
        level = "RED"
    else:
        level = "AMBER"

    message = config.ALERT_MESSAGES[level]

    alert = {
        "alert_level"    : level,
        "icon"           : ALERT_ICONS[level],
        "marathi_message": message,
        "crash_score"    : round(score, 4),
        "timestamp"      : datetime.now().isoformat(),
    }
    return alert


def log_alert(alert: dict) -> None:
    """Append alert to alerts.log as a JSON line."""
    _alert_logger.info(json.dumps(alert, ensure_ascii=False))


def generate_alert(
    crash_score: float,
    date: str = None,
    price: float = None,
    district: str = config.TARGET_DISTRICT,
    commodity: str = config.TARGET_COMMODITY,
    override_level: str = None,
    override_reason: str = None,
    rain_mm: float = 0.0,
    temp_max_c: float = 30.0
) -> dict:
    """
    Public entry point for Phase 6, 10 & 13.
    Takes a crash score, optional macros and weather context, generates and logs the alert dict.
    """
    alert = score_to_alert(crash_score)

    # ── Macro Rule Engine Override ──
    if override_level:
        alert["alert_level"] = override_level
        alert["icon"] = ALERT_ICONS.get(override_level, "🔴")
        if override_reason:
            alert["marathi_message"] += f" (चेतावणी: {override_reason})"
            
    # ── Phase 13: Gemini AI Dynamic Message ──
    from src.alerts.gemini_marathi import generate_marathi_explanation
    dynamic_msg = generate_marathi_explanation(
        commodity=commodity,
        district=district,
        price_today=price,
        crash_score=crash_score,
        alert_level=alert["alert_level"],
        rain_mm=rain_mm,
        temp_max_c=temp_max_c,
        macro_reason=override_reason
    )
    if dynamic_msg:
        alert["marathi_message"] = dynamic_msg
            
    # Enrich with context if provided
    if date:
        alert["date"] = str(date)
    if price is not None:
        alert["price_today"] = float(price)
    alert["district"]  = district
    alert["commodity"] = commodity

    log_alert(alert)

    log.info(
        "%s Alert Level: %s  |  Score: %.2f  |  %s",
        alert["icon"], alert["alert_level"], alert["crash_score"], alert["marathi_message"]
    )
    return alert


def print_alert(alert: dict) -> None:
    """Pretty-print the alert to console."""
    icon = alert.get("icon", "")
    print("\n" + "═" * 50)
    print(f"  {icon}  KisanAlert — {alert.get('alert_level', '')} ALERT")
    print("═" * 50)
    if "date"       in alert: print(f"  📅 Date        : {alert['date']}")
    if "commodity"  in alert: print(f"  🌾 Crop        : {alert['commodity']}")
    if "district"   in alert: print(f"  📍 District    : {alert['district']}")
    if "price_today" in alert: print(f"  💰 Price Today : ₹{alert['price_today']:,.0f}/qtl")
    print(f"  📊 Crash Score : {alert['crash_score']:.2f}")
    print(f"  ⚡ Alert Level : {icon} {alert['alert_level']}")
    print(f"  💬 Message     : {alert['marathi_message']}")
    print("═" * 50)


# ── Standalone test + verification of all threshold boundaries ─────────────────
if __name__ == "__main__":
    test_cases = [
        (0.10, "GREEN"),   # well below GREEN threshold
        (0.20, "GREEN"),   # mid GREEN
        (0.34, "GREEN"),   # just below ALERT_GREEN_MAX
        (0.35, "AMBER"),   # boundary: should be AMBER not GREEN
        (0.50, "AMBER"),   # mid AMBER
        (0.64, "AMBER"),   # just below ALERT_RED_MIN
        (0.65, "RED"),     # boundary: should be RED not AMBER
        (0.80, "RED"),     # clear RED
        (1.00, "RED"),     # maximum
    ]

    all_passed = True
    print("\n🧪 Alert Engine Test")
    print("─" * 40)
    for score, expected in test_cases:
        alert = score_to_alert(score)
        actual = alert["alert_level"]
        passed = actual == expected
        status = "✅" if passed else "❌"
        print(f"  {status} score={score:.2f}  expected={expected}  got={actual}")
        if not passed:
            all_passed = False

    print("─" * 40)
    print("All tests passed ✅" if all_passed else "❌ Some tests FAILED")

    # Show a sample alert
    sample = generate_alert(0.72, date="2024-10-15", price=4620)
    print_alert(sample)
    print(f"\nAlert logged to: {config.LOG_ALERTS_FILE}")
