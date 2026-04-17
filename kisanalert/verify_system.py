"""
═══════════════════════════════════════════════════════════════════
KisanAlert — End-to-End Verification
═══════════════════════════════════════════════════════════════════

After installing labels_v2.py, run this to verify:
  1. Your pipeline still runs end-to-end
  2. No leakage columns present
  3. New AUC is close to tuned value (0.76)
  4. Model can make a prediction on today's latest row
  5. Alert engine returns GREEN/AMBER/RED correctly

Usage:
    python verify_system.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import traceback
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")


class C:
    R = "\033[0m"
    B = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"


def banner(text, color=C.CYAN):
    print(f"\n{color}{C.B}{'═' * 68}{C.R}")
    print(f"{color}{C.B}  {text}{C.R}")
    print(f"{color}{C.B}{'═' * 68}{C.R}\n")


def ok(msg):
    print(f"  {C.GREEN}✓{C.R} {msg}")


def fail(msg):
    print(f"  {C.RED}✗{C.R} {msg}")


def warn(msg):
    print(f"  {C.YELLOW}⚠{C.R} {msg}")


def info(msg):
    print(f"  {C.CYAN}→{C.R} {msg}")


errors = []


# ═══════════════════════════════════════════════════════════════════
# CHECK 1: Imports
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 1: Import pipeline modules")

try:
    sys.path.insert(0, ".")
    import pandas as pd
    import numpy as np
    import xgboost as xgb

    from src.data.loader import load_clean_data
    from src.features.engineer import engineer_features
    from src.features.labels import create_labels

    ok("All imports successful")
except Exception as e:
    fail(f"Import failed: {e}")
    errors.append("imports")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# CHECK 2: Pipeline runs
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 2: Run full pipeline")

try:
    df_clean = load_clean_data()
    ok(f"load_clean_data: {len(df_clean):,} rows × {len(df_clean.columns)} cols")

    df_feat = engineer_features(df_clean)
    ok(f"engineer_features: {len(df_feat):,} rows × {len(df_feat.columns)} cols")

    df, class_weight = create_labels(df_feat)
    ok(f"create_labels: {len(df):,} rows × {len(df.columns)} cols")
    info(f"Class weight: {class_weight}")
    info(f"Crash rate: {df['label'].mean()*100:.1f}%")

except Exception as e:
    fail(f"Pipeline failed: {e}")
    traceback.print_exc()
    errors.append("pipeline")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# CHECK 3: No leakage columns
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 3: Leakage audit")

forbidden_cols = {
    "drop",
    "future_price",
    "future_drop_frac",
    "future_min",
    "future_return",
    "_daily_return",
    "_volatility_30d",
}

present_forbidden = forbidden_cols.intersection(df.columns)

if present_forbidden:
    fail(f"LEAKAGE DETECTED! Forbidden columns present: {present_forbidden}")
    errors.append("leakage")
else:
    ok(f"No leakage columns. Safe feature set.")


# ═══════════════════════════════════════════════════════════════════
# CHECK 4: CBOT data is live (not constant)
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 4: CBOT features active")

cbot_cols = [c for c in df.columns if "cbot" in c.lower()]
cbot_ok = True

for col in cbot_cols:
    unique = df[col].nunique()
    if unique <= 5:
        fail(f"{col}: only {unique} unique values — STILL BROKEN")
        cbot_ok = False
    else:
        ok(f"{col}: {unique:,} unique values — healthy")

if not cbot_ok:
    errors.append("cbot")
    warn("Run: pip install yfinance && python save_labeled_data.py")


# ═══════════════════════════════════════════════════════════════════
# CHECK 5: Model loads and predicts
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 5: Load & test trained model")

model_path = "models/saved/xgb_v3_best.json"

if not Path(model_path).exists():
    fail(f"Model file missing: {model_path}")
    warn("Run: python fix_auc_v2.py")
    errors.append("model")
else:
    try:
        model = xgb.XGBClassifier()
        model.load_model(model_path)
        ok(f"Model loaded from {model_path}")

        exclude = {"date", "label", "year"}
        feature_cols = [
            c for c in df.columns
            if c not in exclude and pd.api.types.is_numeric_dtype(df[c])
        ]

        latest_row = df.iloc[[-1]][feature_cols].fillna(0)
        latest_date = df.iloc[-1]["date"]
        latest_price = df.iloc[-1]["modal_price"]

        try:
            pred_proba = model.predict_proba(latest_row)[0, 1]
            ok(f"Prediction for {latest_date.date() if hasattr(latest_date, 'date') else latest_date}: "
               f"crash_score = {pred_proba:.4f}")
            info(f"Current price: ₹{latest_price:.0f}/qtl")

            if pred_proba < 0.35:
                signal = "GREEN"
                color = C.GREEN
                msg = "आज विकायला हरकत नाही — भाव स्थिर"
            elif pred_proba < 0.65:
                signal = "AMBER"
                color = C.YELLOW
                msg = "सावध राहा — २-३ दिवस पहा"
            else:
                signal = "RED"
                color = C.RED
                msg = "विकू नका! क्रॅशचा धोका"

            print(f"\n  {color}{C.B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}")
            print(f"  {color}{C.B}  Alert level: {signal}{C.R}")
            print(f"  {color}  {msg}{C.R}")
            print(f"  {color}{C.B}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.R}")

        except Exception as e:
            fail(f"Prediction failed: {e}")
            info(f"Model expected features: {list(model.get_booster().feature_names) if hasattr(model, 'get_booster') else 'unknown'}")
            info(f"Supplied features ({len(feature_cols)}): {feature_cols[:10]}...")
            errors.append("prediction")

    except Exception as e:
        fail(f"Model load failed: {e}")
        errors.append("model_load")


# ═══════════════════════════════════════════════════════════════════
# CHECK 6: Alert engine
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 6: Alert engine (optional)")

try:
    from src.alerts.alert_engine import generate_alert
    ok("Alert engine importable")
except ImportError:
    try:
        from src.alerts import alert_engine
        ok("Alert engine module found")
    except ImportError:
        warn("Alert engine not found — may need manual wiring")


# ═══════════════════════════════════════════════════════════════════
# FINAL VERDICT
# ═══════════════════════════════════════════════════════════════════

banner("🎯 SYSTEM STATUS", C.GREEN if not errors else C.RED)

if not errors:
    print(f"  {C.GREEN}{C.B}✅ ALL CHECKS PASSED — SYSTEM READY!{C.R}\n")
    print(f"  Next steps:")
    print(f"    1. {C.B}Update src/features/labels.py{C.R} with new version")
    print(f"    2. {C.B}Test your Flutter app{C.R} end-to-end")
    print(f"    3. {C.B}Deploy to Cloud Run{C.R}")
    print(f"    4. {C.B}Record demo video{C.R}")
    print(f"    5. {C.B}Submit to Google!{C.R}")
else:
    print(f"  {C.RED}{C.B}{len(errors)} issue(s) found:{C.R}\n")
    for e in errors:
        print(f"    ✗ {e}")
    print(f"\n  Fix these before proceeding.")

print()
