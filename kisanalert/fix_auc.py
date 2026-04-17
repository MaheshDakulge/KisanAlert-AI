"""
═══════════════════════════════════════════════════════════════════
KisanAlert — THE AUC FIX 🩺→💪
═══════════════════════════════════════════════════════════════════

Fixes 2 critical bugs found by the doctor:

  🔴 BUG #1: 'drop' column = data leakage
     You created label FROM 'drop', then kept 'drop' as feature.
     Model just memorized the label. AUC=1.0 is fake.

  🟡 BUG #2: Fixed 15% threshold = inconsistent labels
     Catches 49% of 2021 days, only 13% of 2024.
     Train/test distributions don't match.

FIX APPLIED:
  ✓ Drop 'drop' column from features
  ✓ Replace labels with volatility-adjusted version
    (1.5× local 30-day volatility as threshold)
  ✓ Retrain XGBoost with time-series split
  ✓ Report HONEST AUC

Usage:
    python fix_auc.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

warnings.filterwarnings("ignore")


class C:
    R = "\033[0m"
    B = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"


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
    print(f"  {C.CYAN}→{C.R} {msg}")


# ═══════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════

DATA_PATH = "data/processed/features_labeled.csv"
OUTPUT_DATA_PATH = "data/processed/features_labeled_v2.csv"
OUTPUT_MODEL_PATH = "models/saved/xgb_v2_fixed.json"

# Volatility threshold multiplier
# Crash = price drops MORE than (multiplier × local 30-day volatility)
# Start with 1.5× — tune if needed
VOLATILITY_MULTIPLIER = 1.5

# How many days ahead to check for crash
FUTURE_WINDOW_DAYS = 7

# Split dates (time-series, no shuffling!)
TRAIN_END = "2024-12-31"
VALID_END = "2025-06-30"
# Test = everything after VALID_END

# Features KNOWN to be leaked — always drop
LEAKED_FEATURES = [
    "drop",               # THIS is the future price drop! Never use!
    "future_price",
    "future_return",
    "future_drop_pct",
    "label",              # Don't train on label (duh)
    "date",               # Not a feature
]

RANDOM_STATE = 42


# ═══════════════════════════════════════════════════════════════════
# STEP 1: Load data
# ═══════════════════════════════════════════════════════════════════

banner("🩺 KisanAlert AUC FIX — Removing leakage + Fixing labels")

info(f"Loading: {DATA_PATH}")
df = pd.read_csv(DATA_PATH)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)
ok(f"Loaded {len(df):,} rows × {len(df.columns)} columns")
info(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}")


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Create NEW volatility-adjusted labels
# ═══════════════════════════════════════════════════════════════════

banner("STEP 2: Volatility-adjusted labels", C.YELLOW)

info("Computing 30-day rolling volatility...")
df["daily_return"] = df["modal_price"].pct_change()
df["volatility_30d"] = df["daily_return"].rolling(30).std()

info(f"Volatility multiplier: {VOLATILITY_MULTIPLIER}")
info(f"Future window: {FUTURE_WINDOW_DAYS} days")

# Compute future price drop (looking forward)
# future_min = min price in the NEXT 7 days
future_min = (
    df["modal_price"][::-1]
    .rolling(window=FUTURE_WINDOW_DAYS, min_periods=FUTURE_WINDOW_DAYS)
    .min()[::-1]
    .shift(-1)
)

# How much did price drop as a fraction?
future_drop_frac = (future_min - df["modal_price"]) / df["modal_price"]

# Dynamic threshold: each day has its own crash threshold based on LOCAL volatility
# Example: Quiet year → 5% drop = crash. Wild year → 15% drop = crash.
dynamic_threshold = -VOLATILITY_MULTIPLIER * df["volatility_30d"] * np.sqrt(FUTURE_WINDOW_DAYS)

# New label: 1 if actual drop exceeds dynamic threshold
df["label_v2"] = (future_drop_frac < dynamic_threshold).astype(int)

# Drop rows with insufficient history/future
mask = (
    df["volatility_30d"].notna()
    & future_min.notna()
    & dynamic_threshold.notna()
)
df = df[mask].reset_index(drop=True)

ok(f"Rows after filtering: {len(df):,}")

# Check crash rate per year (should be more balanced now!)
df["year"] = df["date"].dt.year
crash_rate_by_year = df.groupby("year")["label_v2"].mean().round(3)

print(f"\n  {C.B}New crash rate per year (target: ~15-20%, balanced):{C.R}")
for yr, rate in crash_rate_by_year.items():
    bar = "█" * int(rate * 50)
    pct = rate * 100
    color = (
        C.GREEN if 10 <= pct <= 25
        else (C.YELLOW if 5 <= pct <= 30 else C.RED)
    )
    print(f"    {yr}: {color}{bar}{C.R} {pct:.1f}%")

overall_rate = df["label_v2"].mean() * 100
print(f"\n  Overall crash rate: {overall_rate:.1f}%")

max_rate = crash_rate_by_year.max() * 100
min_rate = crash_rate_by_year.min() * 100
shift = max_rate - min_rate
if shift < 15:
    ok(f"Shift only {shift:.1f}% — labels now consistent across years!")
else:
    warn(f"Shift still {shift:.1f}% — may need to tune multiplier")


# ═══════════════════════════════════════════════════════════════════
# STEP 3: Remove leaked features + prepare training data
# ═══════════════════════════════════════════════════════════════════

banner("STEP 3: Removing leaked features", C.YELLOW)

# Identify all numeric features
all_cols = df.columns.tolist()
drop_cols = [c for c in LEAKED_FEATURES if c in all_cols]

# Also drop bookkeeping columns
bookkeeping = ["year", "daily_return", "volatility_30d", "label_v2"]

# Active feature columns
feature_cols = [
    c for c in all_cols
    if c not in drop_cols
    and c not in bookkeeping
    and pd.api.types.is_numeric_dtype(df[c])
]

if "drop" in all_cols:
    warn("Removed 'drop' column (was causing 100% fake AUC)")

info(f"Using {len(feature_cols)} features:")
for i, c in enumerate(feature_cols):
    if i < 20:
        print(f"    {C.DIM}•{C.R} {c}")
if len(feature_cols) > 20:
    print(f"    {C.DIM}... +{len(feature_cols)-20} more{C.R}")


# ═══════════════════════════════════════════════════════════════════
# STEP 4: Time-series split
# ═══════════════════════════════════════════════════════════════════

banner("STEP 4: Time-series split (no shuffling!)", C.YELLOW)

train_end = pd.Timestamp(TRAIN_END)
valid_end = pd.Timestamp(VALID_END)

train_mask = df["date"] <= train_end
valid_mask = (df["date"] > train_end) & (df["date"] <= valid_end)
test_mask = df["date"] > valid_end

X_train = df.loc[train_mask, feature_cols].fillna(0)
y_train = df.loc[train_mask, "label_v2"]

X_valid = df.loc[valid_mask, feature_cols].fillna(0)
y_valid = df.loc[valid_mask, "label_v2"]

X_test = df.loc[test_mask, feature_cols].fillna(0)
y_test = df.loc[test_mask, "label_v2"]

info(f"Train: {len(X_train):,} rows | crash rate: {y_train.mean()*100:.1f}%")
info(f"Valid: {len(X_valid):,} rows | crash rate: {y_valid.mean()*100:.1f}%")
info(f"Test:  {len(X_test):,} rows | crash rate: {y_test.mean()*100:.1f}%")

if len(X_test) < 30:
    fail("Test set too small!")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Train XGBoost
# ═══════════════════════════════════════════════════════════════════

banner("STEP 5: Training clean XGBoost", C.YELLOW)

scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
info(f"scale_pos_weight: {scale_pos:.2f}")

model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=4,              # shallow = less overfit
    learning_rate=0.03,       # slow learning
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.5,            # L1 regularization
    reg_lambda=1.0,           # L2 regularization
    scale_pos_weight=scale_pos,
    eval_metric="auc",
    early_stopping_rounds=30,
    random_state=RANDOM_STATE,
    tree_method="hist",
    use_label_encoder=False,
    verbosity=0,
)

info("Training...")
model.fit(
    X_train,
    y_train,
    eval_set=[(X_valid, y_valid)],
    verbose=False,
)
ok(f"Training complete! Used {model.best_iteration + 1} trees.")


# ═══════════════════════════════════════════════════════════════════
# STEP 6: Evaluate honestly
# ═══════════════════════════════════════════════════════════════════

banner("STEP 6: HONEST evaluation", C.GREEN)

for split_name, X, y in [
    ("Train", X_train, y_train),
    ("Valid", X_valid, y_valid),
    ("Test",  X_test,  y_test),
]:
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= 0.5).astype(int)

    auc = roc_auc_score(y, probs) if len(np.unique(y)) > 1 else float("nan")
    f1  = f1_score(y, preds, pos_label=1, zero_division=0)

    color = (
        C.GREEN if auc >= 0.70
        else (C.YELLOW if auc >= 0.60 else C.RED)
    )
    print(f"  {C.B}{split_name:6s}{C.R}  "
          f"AUC: {color}{auc:.4f}{C.R}  "
          f"F1 (crash): {f1:.4f}")

test_probs = model.predict_proba(X_test)[:, 1]
test_preds = (test_probs >= 0.5).astype(int)
test_auc = roc_auc_score(y_test, test_probs) if len(np.unique(y_test)) > 1 else float("nan")

print(f"\n  {C.B}Test set classification report:{C.R}\n")
print(classification_report(y_test, test_preds, target_names=["safe", "crash"], zero_division=0))

print(f"  {C.B}Test set confusion matrix:{C.R}")
cm = confusion_matrix(y_test, test_preds)
print(f"                      Predicted safe   Predicted crash")
print(f"    Actual safe   →   {cm[0][0]:8d}          {cm[0][1]:8d}")
print(f"    Actual crash  →   {cm[1][0]:8d}          {cm[1][1]:8d}")


# ═══════════════════════════════════════════════════════════════════
# STEP 7: Top features (clean!)
# ═══════════════════════════════════════════════════════════════════

banner("STEP 7: Top features (WITHOUT leakage)", C.GREEN)

importances = pd.Series(model.feature_importances_, index=feature_cols)
top = importances.sort_values(ascending=False).head(10)

print(f"  {C.B}Top 10 features:{C.R}\n")
for name, imp in top.items():
    bar = "█" * int(imp * 100)
    print(f"    {name:30s} {C.CYAN}{bar}{C.R} {imp:.3f}")


# ═══════════════════════════════════════════════════════════════════
# STEP 8: Save artifacts
# ═══════════════════════════════════════════════════════════════════

banner("STEP 8: Saving fixed artifacts", C.GREEN)

df_out = df.drop(columns=bookkeeping, errors="ignore")
if "label" in df_out.columns:
    df_out = df_out.rename(columns={"label": "label_old"})
df_out["label"] = df["label_v2"]

Path("data/processed").mkdir(parents=True, exist_ok=True)
df_out.to_csv(OUTPUT_DATA_PATH, index=False)
ok(f"Fixed data: {OUTPUT_DATA_PATH}")

Path("models/saved").mkdir(parents=True, exist_ok=True)
model.save_model(OUTPUT_MODEL_PATH)
ok(f"Fixed model: {OUTPUT_MODEL_PATH}")

# Save summary JSON
import json
summary = {
    "timestamp": datetime.now().isoformat(),
    "fixes_applied": [
        "Removed leaked 'drop' feature",
        "Replaced fixed threshold with volatility-adjusted labels",
        f"New threshold: {VOLATILITY_MULTIPLIER}× rolling 30-day volatility",
    ],
    "metrics": {
        "test_auc": float(test_auc) if not np.isnan(test_auc) else None,
        "test_rows": len(X_test),
        "overall_crash_rate": float(df["label_v2"].mean()),
        "crash_rate_by_year": {int(k): float(v) for k, v in crash_rate_by_year.items()},
    },
    "config": {
        "volatility_multiplier": VOLATILITY_MULTIPLIER,
        "future_window_days": FUTURE_WINDOW_DAYS,
        "train_end": TRAIN_END,
        "valid_end": VALID_END,
        "features_used": feature_cols,
        "features_dropped": drop_cols,
    },
}
Path("reports").mkdir(exist_ok=True)
with open(f"reports/auc_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
    json.dump(summary, f, indent=2)


# ═══════════════════════════════════════════════════════════════════
# FINAL MESSAGE
# ═══════════════════════════════════════════════════════════════════

banner("🎉 AUC FIX COMPLETE!", C.GREEN)

print(f"  Before: {C.RED}AUC = 0.577{C.R} (real) / {C.RED}1.000{C.R} (fake due to leakage)")
if not np.isnan(test_auc):
    color = C.GREEN if test_auc >= 0.70 else C.YELLOW
    print(f"  After:  {color}AUC = {test_auc:.4f}{C.R} (HONEST, on 2025-2026 data)")

print()
if not np.isnan(test_auc) and test_auc >= 0.70:
    print(f"  {C.GREEN}{C.B}✅ Your model is now production-ready!{C.R}")
    print(f"  {C.GREEN}Next: Update run_pipeline.py to use new model + labels{C.R}")
elif not np.isnan(test_auc) and test_auc >= 0.60:
    print(f"  {C.YELLOW}{C.B}⚠ AUC improved but still below 0.70{C.R}")
    print(f"  {C.YELLOW}Try: Tune VOLATILITY_MULTIPLIER (0.8, 1.0, 1.2, 2.0){C.R}")
    print(f"  {C.YELLOW}Or:  Add more features (see suggestions below){C.R}")
else:
    print(f"  {C.RED}{C.B}Still low. Structural issue in features.{C.R}")
    print(f"  {C.RED}Share this output with Claude for next fix.{C.R}")

print()
print(f"  {C.DIM}Fix report: reports/auc_fix_*.json{C.R}")
print()
