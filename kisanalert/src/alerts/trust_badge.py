# -*- coding: utf-8 -*-
"""
PHASE 8 — Trust Badge (Accuracy History Tracker)

Logs every prediction we make, then when the actual price is known 7-10
days later, retroactively checks if the prediction was correct.

Provides farmers with a running "scorecard":
  Last 30 days: 8/10 correct (80%)
  Last 90 days: 24/30 correct (80%)

Also provides judges with a live accuracy dashboard for the demo.

Storage: Simple JSONL file at data/cache/predictions_log.jsonl
Each line = one prediction record with fields:
  timestamp, crop, district, signal, crash_score, rise_score,
  modal_price_at_prediction, actual_price_7d_later, was_correct, verified

Usage:
    from src.alerts.trust_badge import log_prediction, verify_predictions, get_accuracy_stats

    # After generating an alert:
    log_prediction(alert, current_price=5250, current_date=datetime.now())

    # Daily cron job (or on app startup):
    verify_predictions(price_history_df)

    # Show in API / Flutter UI:
    stats = get_accuracy_stats(days=30)
    # → {"total": 10, "correct": 8, "accuracy": 0.80, ...}

Author: Mahesh Dakulge
Date:   2026-04-18 (Day 2)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)


CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PREDICTIONS_LOG = CACHE_DIR / "predictions_log.jsonl"

VERIFY_WINDOW_DAYS = 7

SIGNIFICANT_PRICE_CHANGE_PCT = 3.0


# ═══════════════════════════════════════════════════════════════════
# LOGGING A NEW PREDICTION
# ═══════════════════════════════════════════════════════════════════


def log_prediction(
    alert: dict,
    current_price: float,
    current_date: Optional[datetime] = None,
) -> None:
    """
    Append a new prediction to the log (to be verified later).

    Call this every time generate_alert() fires.
    """
    current_date = current_date or datetime.now()

    record = {
        "timestamp": current_date.isoformat(),
        "prediction_date": current_date.strftime("%Y-%m-%d"),
        "crop": alert.get("crop", "Soybean"),
        "district": alert.get("district", "Nanded"),
        "signal": alert.get("alert_level", "AMBER"),
        "crash_score": alert.get("crash_score"),
        "rise_score": alert.get("rise_score"),
        "modal_price_at_prediction": round(float(current_price), 2),
        "forecast_days": alert.get("forecast_days", VERIFY_WINDOW_DAYS),
        "verified": False,
        "actual_price_later": None,
        "actual_change_pct": None,
        "was_correct": None,
    }

    try:
        with open(PREDICTIONS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        log.info("Logged prediction: %s signal for %s", record["signal"], record["crop"])
    except Exception as e:
        log.error("Could not log prediction: %s", e)


# ═══════════════════════════════════════════════════════════════════
# VERIFYING PAST PREDICTIONS
# ═══════════════════════════════════════════════════════════════════


def _load_all_predictions() -> list[dict]:
    """Read every prediction record from the JSONL log."""
    if not PREDICTIONS_LOG.exists():
        return []

    records = []
    with open(PREDICTIONS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return records


def _save_all_predictions(records: list[dict]) -> None:
    """Rewrite the full log (used after verification updates)."""
    with open(PREDICTIONS_LOG, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")


def _check_correctness(signal: str, change_pct: float) -> bool:
    """
    Ground truth for whether a signal was correct.

    RED correct if price dropped significantly.
    BLUE correct if price rose significantly.
    GREEN correct if price stayed high or dropped after (i.e. selling was smart).
    AMBER correct if price moved little (stable).
    """
    if signal == "RED":
        return change_pct <= -SIGNIFICANT_PRICE_CHANGE_PCT
    if signal == "BLUE":
        return change_pct >= SIGNIFICANT_PRICE_CHANGE_PCT
    if signal == "GREEN":
        return change_pct <= 2.0
    if signal == "AMBER":
        return abs(change_pct) < SIGNIFICANT_PRICE_CHANGE_PCT
    return False


def verify_predictions(price_history: pd.DataFrame) -> dict:
    """
    Walk through unverified predictions, match against actual prices,
    and mark them correct/incorrect.

    Args:
        price_history: DataFrame with columns [date, modal_price]

    Returns:
        summary dict with counts of newly verified records
    """
    records = _load_all_predictions()
    if not records:
        return {"total": 0, "newly_verified": 0}

    prices = price_history.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    price_lookup = dict(zip(prices["date"].dt.date, prices["modal_price"]))

    newly_verified = 0
    now = datetime.now()

    for rec in records:
        if rec.get("verified"):
            continue

        pred_ts = datetime.fromisoformat(rec["timestamp"])
        verify_date = pred_ts + timedelta(days=rec.get("forecast_days", VERIFY_WINDOW_DAYS))

        if verify_date > now:
            continue

        start = verify_date.date()
        end = (verify_date + timedelta(days=2)).date()
        actual_price = None
        for lookup_date in pd.date_range(start, end):
            key = lookup_date.date()
            if key in price_lookup:
                actual_price = float(price_lookup[key])
                break

        if actual_price is None:
            continue

        start_price = rec["modal_price_at_prediction"]
        change_pct = 100.0 * (actual_price - start_price) / start_price

        was_correct = _check_correctness(rec["signal"], change_pct)

        rec["verified"] = True
        rec["actual_price_later"] = round(actual_price, 2)
        rec["actual_change_pct"] = round(change_pct, 2)
        rec["was_correct"] = was_correct

        newly_verified += 1
        log.info(
            "Verified %s prediction from %s: %s (change %.1f%%)",
            rec["signal"],
            rec["prediction_date"],
            "✓" if was_correct else "✗",
            change_pct,
        )

    if newly_verified > 0:
        _save_all_predictions(records)

    return {
        "total": len(records),
        "newly_verified": newly_verified,
        "verified_so_far": sum(1 for r in records if r.get("verified")),
    }


# ═══════════════════════════════════════════════════════════════════
# ACCURACY STATS
# ═══════════════════════════════════════════════════════════════════


def get_accuracy_stats(days: int = 30, crop: Optional[str] = None) -> dict:
    """
    Compute accuracy over the last N days for display in app / judges' demo.

    Args:
        days: look-back window
        crop: optional crop filter ("Soybean", "Cotton", etc.)

    Returns:
        dict with overall + per-signal breakdown
    """
    records = _load_all_predictions()
    cutoff = datetime.now() - timedelta(days=days)

    recent = [
        r for r in records
        if r.get("verified")
        and datetime.fromisoformat(r["timestamp"]) >= cutoff
        and (crop is None or r.get("crop") == crop)
    ]

    if not recent:
        return {
            "window_days": days,
            "crop": crop,
            "total": 0,
            "correct": 0,
            "accuracy": None,
            "per_signal": {},
            "message": "Not enough verified predictions yet",
        }

    total = len(recent)
    correct = sum(1 for r in recent if r.get("was_correct"))
    accuracy = correct / total if total > 0 else 0.0

    per_signal = {}
    for signal in ["RED", "BLUE", "GREEN", "AMBER"]:
        sig_records = [r for r in recent if r.get("signal") == signal]
        if sig_records:
            sig_correct = sum(1 for r in sig_records if r.get("was_correct"))
            per_signal[signal] = {
                "total": len(sig_records),
                "correct": sig_correct,
                "accuracy": round(sig_correct / len(sig_records), 3),
            }

    return {
        "window_days": days,
        "crop": crop,
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 3),
        "per_signal": per_signal,
    }


def get_recent_predictions(limit: int = 10, verified_only: bool = True) -> list[dict]:
    """Return the most recent N predictions (newest first) for display."""
    records = _load_all_predictions()
    if verified_only:
        records = [r for r in records if r.get("verified")]
    records.sort(key=lambda r: r["timestamp"], reverse=True)
    return records[:limit]


# ═══════════════════════════════════════════════════════════════════
# DISPLAY HELPERS
# ═══════════════════════════════════════════════════════════════════


def format_trust_badge_marathi(stats: dict) -> str:
    """Generate Marathi trust badge text for the Flutter app."""
    if stats["total"] == 0:
        return "🌱 लवकरच सुरू होईल — प्रथम अंदाज तयार होत आहेत"

    correct = stats["correct"]
    total = stats["total"]
    accuracy = stats["accuracy"]

    if accuracy >= 0.80:
        badge = "⭐⭐⭐⭐⭐"
        quality = "उत्कृष्ट"
    elif accuracy >= 0.70:
        badge = "⭐⭐⭐⭐"
        quality = "चांगले"
    elif accuracy >= 0.60:
        badge = "⭐⭐⭐"
        quality = "समाधानकारक"
    else:
        badge = "⭐⭐"
        quality = "शिकत आहोत"

    return (
        f"{badge} {quality}\n"
        f"गेल्या {stats['window_days']} दिवसात: {correct}/{total} अंदाज बरोबर "
        f"({int(accuracy * 100)}% अचूक)"
    )


def format_trust_badge_english(stats: dict) -> str:
    """Generate English trust badge text."""
    if stats["total"] == 0:
        return "🌱 Starting soon — first predictions being verified"

    correct = stats["correct"]
    total = stats["total"]
    accuracy = stats["accuracy"]
    stars = "⭐" * max(2, int(accuracy * 5))

    return (
        f"{stars}\n"
        f"Last {stats['window_days']} days: {correct}/{total} correct "
        f"({int(accuracy * 100)}% accuracy)"
    )


# ═══════════════════════════════════════════════════════════════════
# STANDALONE DEMO
# ═══════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    print("\n" + "═" * 68)
    print("  🏆 Testing Trust Badge System")
    print("═" * 68 + "\n")

    print("TEST 1: Logging fake predictions for demo...")
    fake_data = [
        ("RED",   5200, -5.2, True, 8),
        ("RED",   5100, -1.8, False, 7),
        ("GREEN", 5400, +0.5, True, 6),
        ("BLUE",  4800, +4.1, True, 5),
        ("AMBER", 5000, +1.2, True, 4),
        ("RED",   5300, -6.8, True, 3),
        ("BLUE",  4700, -2.1, False, 2),
        ("GREEN", 5500, -0.8, True, 1),
    ]

    records = []
    for signal, start_price, change_pct, correct, days_ago in fake_data:
        pred_ts = datetime.now() - timedelta(days=days_ago)
        actual_price = start_price * (1 + change_pct / 100)
        records.append({
            "timestamp": pred_ts.isoformat(),
            "prediction_date": pred_ts.strftime("%Y-%m-%d"),
            "crop": "Soybean",
            "district": "Nanded",
            "signal": signal,
            "crash_score": 0.8 if signal == "RED" else 0.2,
            "rise_score": 0.7 if signal == "BLUE" else 0.3,
            "modal_price_at_prediction": start_price,
            "forecast_days": 7,
            "verified": True,
            "actual_price_later": round(actual_price, 2),
            "actual_change_pct": change_pct,
            "was_correct": correct,
        })

    _save_all_predictions(records)
    print(f"  ✓ Logged {len(records)} fake predictions to {PREDICTIONS_LOG}")
    print()

    print("TEST 2: Computing accuracy stats (last 30 days)...")
    stats = get_accuracy_stats(days=30)
    print(f"  Total: {stats['total']}")
    print(f"  Correct: {stats['correct']}")
    print(f"  Accuracy: {stats['accuracy']*100:.0f}%")
    print(f"  Per signal:")
    for sig, data in stats["per_signal"].items():
        print(f"    {sig}: {data['correct']}/{data['total']} ({data['accuracy']*100:.0f}%)")
    print()

    print("TEST 3: Marathi trust badge")
    print("─" * 50)
    print(format_trust_badge_marathi(stats))
    print("─" * 50)
    print()

    print("TEST 4: English trust badge")
    print("─" * 50)
    print(format_trust_badge_english(stats))
    print("─" * 50)
    print()

    print("TEST 5: Recent predictions (for app history view)")
    recent = get_recent_predictions(limit=5)
    for r in recent:
        check = "✓" if r.get("was_correct") else "✗"
        print(f"  {check} {r['prediction_date']}  {r['signal']:6s}  "
              f"₹{r['modal_price_at_prediction']:.0f} → ₹{r['actual_price_later']:.0f}  "
              f"({r['actual_change_pct']:+.1f}%)")
    print()

    print("✓ Trust badge test complete!")
    print()
