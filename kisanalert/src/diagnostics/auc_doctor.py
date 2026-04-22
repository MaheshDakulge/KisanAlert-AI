"""
═══════════════════════════════════════════════════════════════════
KisanAlert — AUC Diagnostic Doctor 🩺
═══════════════════════════════════════════════════════════════════

Your current AUC: 0.577 (bad)
Target AUC:      0.70+ (good)

This script checks THREE things in order:
  1. Is your train/test split causing distribution shift?
  2. Is there data leakage in features?
  3. Are your labels inconsistent across years?

Run this in your kisanalert/ project root:
    python auc_doctor.py

It reads your existing model + data and auto-diagnoses the problem.
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

warnings.filterwarnings("ignore")


class C:
    """Terminal colors."""
    R = "\033[0m"
    B = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"


def banner(text: str, color: str = C.CYAN) -> None:
    print(f"\n{color}{C.B}{'═' * 68}{C.R}")
    print(f"{color}{C.B}  {text}{C.R}")
    print(f"{color}{C.B}{'═' * 68}{C.R}\n")


def ok(msg: str) -> None:
    print(f"  {C.GREEN}✓{C.R} {msg}")


def fail(msg: str) -> None:
    print(f"  {C.RED}✗{C.R} {msg}")


def warn(msg: str) -> None:
    print(f"  {C.YELLOW}⚠{C.R} {msg}")


def info(msg: str) -> None:
    print(f"  {C.BLUE}→{C.R} {msg}")


def header(text: str) -> None:
    print(f"\n{C.B}{C.CYAN}[ {text} ]{C.R}\n")


# ═══════════════════════════════════════════════════════════════════
# STEP 0: SETUP & IMPORTS
# ═══════════════════════════════════════════════════════════════════

banner("🩺 KisanAlert AUC Doctor — Diagnosing Your Model")

print(f"  {C.DIM}Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.R}")
print(f"  {C.DIM}Working dir: {os.getcwd()}{C.R}")

header("STEP 0: Checking dependencies")

try:
    import numpy as np
    import pandas as pd
    from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report
    from sklearn.model_selection import TimeSeriesSplit
    import xgboost as xgb
    ok("All required packages installed")
except ImportError as e:
    fail(f"Missing package: {e}")
    info("Run: pip install pandas numpy scikit-learn xgboost")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# STEP 1: FIND YOUR DATA FILES
# ═══════════════════════════════════════════════════════════════════

header("STEP 1: Locating your data files")

CANDIDATE_PATHS = [
    "data/processed/features_labeled.csv",
    "data/processed/features_labeled.parquet",
    "data/processed/soybean_nanded.csv",
    "data/raw/agmarknet_soybean_nanded_2019_2024.csv",
    "data/soybean_features.csv",
    "features_labeled.csv",
]

data_file = None
for path in CANDIDATE_PATHS:
    if Path(path).exists():
        data_file = path
        ok(f"Found data at: {path}")
        break

if data_file is None:
    fail("Could not auto-find your data file!")
    info("Please enter path manually below, or place your CSV here.")
    data_file = input(f"  {C.YELLOW}Data file path: {C.R}").strip()
    if not Path(data_file).exists():
        fail(f"File not found: {data_file}")
        sys.exit(1)

# Load the data
try:
    if data_file.endswith(".parquet"):
        df = pd.read_parquet(data_file)
    else:
        df = pd.read_csv(data_file)
    ok(f"Loaded {len(df):,} rows × {len(df.columns)} columns")
except Exception as e:
    fail(f"Failed to load data: {e}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# STEP 2: IDENTIFY KEY COLUMNS
# ═══════════════════════════════════════════════════════════════════

header("STEP 2: Identifying date / label / price columns")

# Auto-detect date column
date_col = None
for col in ["date", "Date", "arrival_date", "price_date", "timestamp"]:
    if col in df.columns:
        date_col = col
        break

if date_col is None:
    fail("No date column found!")
    info(f"Available columns: {list(df.columns)[:10]}")
    date_col = input(f"  {C.YELLOW}Enter date column name: {C.R}").strip()

df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=[date_col]).sort_values(date_col).reset_index(drop=True)
ok(f"Date column: '{date_col}' | Range: {df[date_col].min().date()} → {df[date_col].max().date()}")

# Auto-detect label column
label_col = None
for col in ["label", "target", "crash", "y", "signal"]:
    if col in df.columns:
        label_col = col
        break

if label_col is None:
    fail("No label column found!")
    label_col = input(f"  {C.YELLOW}Enter label column name: {C.R}").strip()

ok(f"Label column: '{label_col}' | Unique values: {sorted(df[label_col].unique())}")

# Auto-detect price column
price_col = None
for col in ["modal_price", "price", "close_price", "Modal Price"]:
    if col in df.columns:
        price_col = col
        break

if price_col:
    ok(f"Price column: '{price_col}' | Range: ₹{df[price_col].min():.0f} - ₹{df[price_col].max():.0f}")
else:
    warn("No price column found — some checks will be skipped")


# ═══════════════════════════════════════════════════════════════════
# DIAGNOSIS 1: DISTRIBUTION SHIFT
# ═══════════════════════════════════════════════════════════════════

banner("🔬 DIAGNOSIS 1: Train/Test Distribution Shift", C.YELLOW)

df["year"] = df[date_col].dt.year
years = sorted(df["year"].unique())
info(f"Years in dataset: {years}")

yearly_crash_rate = df.groupby("year")[label_col].mean().round(3)
print(f"\n  {C.B}Crash rate per year:{C.R}")
for yr, rate in yearly_crash_rate.items():
    bar = "█" * int(rate * 50)
    color = C.RED if rate > 0.30 else (C.GREEN if rate < 0.20 else C.YELLOW)
    print(f"    {yr}: {color}{bar}{C.R} {rate*100:.1f}%")

# Compute shift metric
max_rate = yearly_crash_rate.max()
min_rate = yearly_crash_rate.min()
shift_pct = (max_rate - min_rate) * 100

print()
if shift_pct > 15:
    fail(f"HUGE DISTRIBUTION SHIFT DETECTED: {shift_pct:.1f}% difference between years")
    diagnosis_1 = "SHIFT"
elif shift_pct > 8:
    warn(f"Moderate shift detected: {shift_pct:.1f}% difference between years")
    diagnosis_1 = "MILD_SHIFT"
else:
    ok(f"Distributions look stable: only {shift_pct:.1f}% variance")
    diagnosis_1 = "OK"


# ═══════════════════════════════════════════════════════════════════
# DIAGNOSIS 2: DATA LEAKAGE DETECTOR
# ═══════════════════════════════════════════════════════════════════

banner("🔬 DIAGNOSIS 2: Data Leakage Detector", C.YELLOW)

# Find numeric feature columns (exclude id, date, label)
exclude_cols = {date_col, label_col, "year", "id", "index"}
feature_cols = [
    c for c in df.columns
    if c not in exclude_cols and pd.api.types.is_numeric_dtype(df[c])
]

info(f"Testing {len(feature_cols)} numeric features for leakage")

if len(feature_cols) == 0:
    fail("No numeric features found!")
    diagnosis_2 = "UNKNOWN"
else:
    # Check each feature's correlation with the label
    # A feature that's "too good" is suspicious
    correlations = []
    for col in feature_cols:
        try:
            corr = df[col].corr(df[label_col])
            if pd.notna(corr):
                correlations.append((col, abs(corr), corr))
        except Exception:
            pass

    correlations.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  {C.B}Top feature correlations with label:{C.R}")
    suspicious = []
    for col, abs_corr, corr in correlations[:10]:
        if abs_corr > 0.7:
            marker = f"{C.RED}🚨 SUSPICIOUS{C.R}"
            suspicious.append(col)
        elif abs_corr > 0.4:
            marker = f"{C.YELLOW}⚠ high{C.R}"
        else:
            marker = f"{C.GREEN}✓ normal{C.R}"
        print(f"    {col:35s} {corr:+.3f}  {marker}")

    # Check for common leakage patterns by name
    print()
    leakage_patterns = ["future", "next", "tomorrow", "_lead", "_ahead", "_f_"]
    name_leakage = []
    for col in feature_cols:
        for pattern in leakage_patterns:
            if pattern in col.lower():
                name_leakage.append(col)

    if name_leakage:
        fail(f"Columns with suspicious names (future/lead/ahead): {name_leakage}")
        diagnosis_2 = "LEAKAGE"
    elif suspicious:
        warn(f"Features with >0.7 correlation (possibly leakage): {suspicious}")
        diagnosis_2 = "MAYBE_LEAKAGE"
    else:
        ok("No obvious leakage detected")
        diagnosis_2 = "OK"


# ═══════════════════════════════════════════════════════════════════
# DIAGNOSIS 3: LABEL CONSISTENCY
# ═══════════════════════════════════════════════════════════════════

banner("🔬 DIAGNOSIS 3: Label Consistency Across Years", C.YELLOW)

if price_col is None:
    warn("Skipping — no price column available")
    diagnosis_3 = "UNKNOWN"
else:
    # Compute rolling volatility per year
    df_sorted = df.sort_values(date_col).reset_index(drop=True)
    df_sorted["daily_return"] = df_sorted[price_col].pct_change()
    df_sorted["rolling_vol_30d"] = (
        df_sorted["daily_return"].rolling(30).std()
    )

    yearly_vol = df_sorted.groupby(df_sorted[date_col].dt.year)["rolling_vol_30d"].mean()
    yearly_vol = yearly_vol.dropna().round(4)

    print(f"\n  {C.B}Average 30-day volatility per year:{C.R}")
    for yr, vol in yearly_vol.items():
        bar = "█" * int(vol * 500)
        print(f"    {yr}: {C.CYAN}{bar}{C.R} {vol:.4f}")

    vol_range = yearly_vol.max() - yearly_vol.min()
    vol_ratio = yearly_vol.max() / max(yearly_vol.min(), 0.0001)

    print()
    if vol_ratio > 2.5:
        fail(f"Volatility varies {vol_ratio:.1f}x across years — fixed 15% threshold is WRONG")
        info("Your label definition is inconsistent: 15% drop means different things in 2021 vs 2024")
        diagnosis_3 = "INCONSISTENT_LABELS"
    elif vol_ratio > 1.5:
        warn(f"Moderate volatility variation: {vol_ratio:.1f}x")
        diagnosis_3 = "SOMEWHAT_OK"
    else:
        ok(f"Volatility stable across years: {vol_ratio:.1f}x variance")
        diagnosis_3 = "OK"


# ═══════════════════════════════════════════════════════════════════
# DIAGNOSIS 4: BASELINE MODEL TEST (TIME-SERIES SPLIT)
# ═══════════════════════════════════════════════════════════════════

banner("🔬 DIAGNOSIS 4: Fresh Time-Series Model Test", C.YELLOW)

if len(feature_cols) < 3:
    warn("Skipping — not enough features")
    diagnosis_4 = "SKIPPED"
else:
    # Train a simple XGBoost on the LAST 80/20 split
    split_idx = int(len(df) * 0.8)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]

    info(f"Train: {len(train)} rows ({train[date_col].min().date()} to {train[date_col].max().date()})")
    info(f"Test:  {len(test)} rows ({test[date_col].min().date()} to {test[date_col].max().date()})")
    info(f"Train crash rate: {train[label_col].mean():.3f}")
    info(f"Test crash rate:  {test[label_col].mean():.3f}")

    X_train = train[feature_cols].fillna(0)
    y_train = train[label_col]
    X_test = test[feature_cols].fillna(0)
    y_test = test[label_col]

    try:
        scale = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=scale,
            eval_metric="auc",
            random_state=42,
            use_label_encoder=False,
        )
        model.fit(X_train, y_train)

        # Train AUC
        train_pred = model.predict_proba(X_train)[:, 1]
        train_auc = roc_auc_score(y_train, train_pred)

        # Test AUC
        test_pred = model.predict_proba(X_test)[:, 1]
        test_auc = roc_auc_score(y_test, test_pred)

        print()
        train_color = C.GREEN if train_auc > 0.75 else C.YELLOW
        test_color = C.GREEN if test_auc > 0.70 else C.RED

        print(f"  {C.B}Train AUC:{C.R} {train_color}{train_auc:.4f}{C.R}")
        print(f"  {C.B}Test AUC: {C.R} {test_color}{test_auc:.4f}{C.R}")

        gap = train_auc - test_auc
        if gap > 0.15:
            fail(f"BIG train/test gap: {gap:.3f} — classic overfitting")
            diagnosis_4 = "OVERFIT"
        elif test_auc < 0.60:
            fail("Test AUC below 0.60 — model isn't learning useful signal")
            diagnosis_4 = "UNDERFIT"
        elif test_auc < 0.70:
            warn(f"Test AUC = {test_auc:.3f}, needs improvement to hit 0.70+")
            diagnosis_4 = "BORDERLINE"
        else:
            ok(f"Test AUC = {test_auc:.3f} — healthy!")
            diagnosis_4 = "OK"

        # Top features from this clean retrain
        importances = pd.Series(model.feature_importances_, index=feature_cols)
        top_feat = importances.sort_values(ascending=False).head(5)
        print(f"\n  {C.B}Top 5 features (clean retrain):{C.R}")
        for name, imp in top_feat.items():
            print(f"    {name:35s} {imp:.3f}")

    except Exception as e:
        fail(f"Model training failed: {e}")
        diagnosis_4 = "ERROR"


# ═══════════════════════════════════════════════════════════════════
# FINAL DIAGNOSIS & PRESCRIPTION
# ═══════════════════════════════════════════════════════════════════

banner("💊 DIAGNOSIS SUMMARY & PRESCRIPTION", C.GREEN)

diagnoses = {
    "Distribution Shift": diagnosis_1,
    "Data Leakage": diagnosis_2,
    "Label Consistency": diagnosis_3,
    "Model Fit": diagnosis_4,
}

print(f"  {C.B}Check Results:{C.R}\n")
for check, result in diagnoses.items():
    if result == "OK":
        symbol, color = "✓", C.GREEN
    elif result in ("SHIFT", "LEAKAGE", "INCONSISTENT_LABELS", "OVERFIT", "UNDERFIT"):
        symbol, color = "✗", C.RED
    else:
        symbol, color = "⚠", C.YELLOW
    print(f"    {color}{symbol} {check:25s} → {result}{C.R}")


banner("🎯 YOUR ACTION PLAN", C.CYAN)

actions = []

if diagnosis_1 in ("SHIFT", "MILD_SHIFT"):
    actions.append({
        "priority": "🔥 CRITICAL",
        "fix": "Fix #1: Recalibrate labels per year",
        "detail": (
            "Instead of fixed 15% drop = crash, use year-specific rolling threshold.\n"
            "      → 'crash' = price drops more than 1.5× local 30-day volatility"
        ),
        "code": "fix_labels.py",
    })

if diagnosis_2 == "LEAKAGE":
    actions.append({
        "priority": "🔥 CRITICAL",
        "fix": "Fix #2: Remove leaking features",
        "detail": (
            "Features using future data MUST be removed. Rename or rebuild.\n"
            "      → Ensure every feature only uses data from BEFORE the prediction date"
        ),
        "code": "audit_features.py",
    })

if diagnosis_3 == "INCONSISTENT_LABELS":
    actions.append({
        "priority": "🔥 CRITICAL",
        "fix": "Fix #3: Volatility-adjusted labels",
        "detail": (
            "Your 15% threshold catches 36% of 2021 days but only 13% of 2024.\n"
            "      → Use percentile-based labels: 'crash' = bottom 15% of returns THIS year"
        ),
        "code": "fix_labels.py",
    })

if diagnosis_4 == "OVERFIT":
    actions.append({
        "priority": "⚠ HIGH",
        "fix": "Fix #4: Reduce model complexity",
        "detail": "Lower max_depth (5→3), increase regularization (reg_alpha=0.5)",
        "code": "retrain_model.py",
    })

if diagnosis_4 == "UNDERFIT":
    actions.append({
        "priority": "⚠ HIGH",
        "fix": "Fix #4: Add stronger features",
        "detail": "Add: price_vs_mandi_peers, NCDEX_basis, lag_correlation_latur",
        "code": "add_features.py",
    })

if not actions:
    print(f"  {C.GREEN}{C.B}✅ Your model is healthy! No critical fixes needed.{C.R}")
    print(f"  {C.GREEN}Next step: Deploy to Cloud Run with confidence.{C.R}")
else:
    for i, a in enumerate(actions, 1):
        print(f"\n  {C.B}{a['priority']}{C.R}")
        print(f"    {a['fix']}")
        print(f"      {C.DIM}{a['detail']}{C.R}")


# ═══════════════════════════════════════════════════════════════════
# SAVE REPORT
# ═══════════════════════════════════════════════════════════════════

report = {
    "timestamp": datetime.now().isoformat(),
    "data_file": data_file,
    "rows": len(df),
    "years": [int(y) for y in years],
    "yearly_crash_rate": {int(k): float(v) for k, v in yearly_crash_rate.items()},
    "diagnoses": diagnoses,
    "train_auc": float(train_auc) if "train_auc" in dir() else None,
    "test_auc": float(test_auc) if "test_auc" in dir() else None,
    "feature_count": len(feature_cols) if feature_cols else 0,
}

import json
Path("reports").mkdir(exist_ok=True)
report_path = f"reports/auc_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)

print(f"\n  {C.DIM}📄 Full report saved to: {report_path}{C.R}")

banner("Doctor's done. Share output with Claude for next fix script! 🩺", C.CYAN)
