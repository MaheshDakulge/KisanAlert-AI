"""
═══════════════════════════════════════════════════════════════════
KisanAlert — Train BLUE Signal Model 🔵
═══════════════════════════════════════════════════════════════════

This trains a SECOND XGBoost model that predicts price RISES.
Combined with your existing CRASH model, you get 4-signal system:

  🔴 RED   — crash predicted → "Don't sell!"
  🔵 BLUE  — rise predicted  → "Hold, wait!"
  🟢 GREEN — at 30-day peak  → "Sell now!"
  🟡 AMBER — stable          → "Farmer's choice"

The RISE model uses THE SAME FEATURES as your crash model.
Only the LABEL is flipped: rise (opposite direction).

Usage:
    python train_blue_model.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import f1_score, roc_auc_score

warnings.filterwarnings("ignore")


class C:
    R = "\033[0m"
    B = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"


def banner(text, color=C.CYAN):
    print(f"\n{color}{C.B}{'═' * 68}{C.R}")
    print(f"{color}{C.B}  {text}{C.R}")
    print(f"{color}{C.B}{'═' * 68}{C.R}\n")


def ok(msg):
    print(f"  {C.GREEN}✓{C.R} {msg}")


def info(msg):
    print(f"  {C.CYAN}→{C.R} {msg}")


DATA_PATH = "data/processed/features_labeled.csv"
FUTURE_WINDOW_DAYS = 7
VOLATILITY_MULTIPLIER = 0.85
TRAIN_END = "2024-12-31"
VALID_END = "2025-06-30"
RANDOM_STATE = 42

LEAKED_FEATURES = ["drop", "future_price", "future_return", "future_drop_pct", "label", "date"]


banner("🔵 KisanAlert — Training BLUE Signal Model", C.BLUE)


# ═══════════════════════════════════════════════════════════════════
# Load data
# ═══════════════════════════════════════════════════════════════════

info(f"Loading: {DATA_PATH}")
df = pd.read_csv(DATA_PATH)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)
ok(f"Loaded {len(df):,} rows")


# ═══════════════════════════════════════════════════════════════════
# Create RISE label (opposite of crash)
# ═══════════════════════════════════════════════════════════════════

banner("STEP 1: Create RISE label", C.YELLOW)

df["daily_return"] = df["modal_price"].pct_change()
df["volatility_30d"] = df["daily_return"].rolling(30).std()

# Future MAXIMUM price (opposite of future min)
future_max = (
    df["modal_price"][::-1]
    .rolling(window=FUTURE_WINDOW_DAYS, min_periods=FUTURE_WINDOW_DAYS)
    .max()[::-1]
    .shift(-1)
)

# Future rise fraction
future_rise_frac = (future_max - df["modal_price"]) / df["modal_price"]

# Dynamic threshold (positive — we want rises ABOVE this)
dynamic_threshold = VOLATILITY_MULTIPLIER * df["volatility_30d"] * np.sqrt(FUTURE_WINDOW_DAYS)

# Label = 1 if rise exceeds threshold
df["label_rise"] = (future_rise_frac > dynamic_threshold).astype(int)

# Invalidate where data insufficient
invalid_mask = (
    df["volatility_30d"].isna()
    | future_max.isna()
    | dynamic_threshold.isna()
)
df = df[~invalid_mask].reset_index(drop=True)

ok(f"Rows after filtering: {len(df):,}")

# Per-year breakdown
df["year"] = df["date"].dt.year
rise_by_year = df.groupby("year")["label_rise"].mean().round(3)
print(f"\n  {C.B}Rise rate per year:{C.R}")
for yr, rate in rise_by_year.items():
    bar = "█" * int(rate * 50)
    print(f"    {yr}: {C.BLUE}{bar}{C.R} {rate*100:.1f}%")

overall_rise = df["label_rise"].mean() * 100
print(f"\n  Overall rise rate: {overall_rise:.1f}%")


# ═══════════════════════════════════════════════════════════════════
# Prepare features (NO leakage)
# ═══════════════════════════════════════════════════════════════════

banner("STEP 2: Feature selection (no leakage)", C.YELLOW)

excluded = set(LEAKED_FEATURES) | {
    "daily_return", "volatility_30d", "year",
    "label", "label_rise",
}
feature_cols = [
    c for c in df.columns
    if c not in excluded and pd.api.types.is_numeric_dtype(df[c])
]

info(f"Using {len(feature_cols)} features (same as crash model)")


# ═══════════════════════════════════════════════════════════════════
# Time-series split
# ═══════════════════════════════════════════════════════════════════

banner("STEP 3: Train / validate / test split", C.YELLOW)

train_mask = df["date"] <= pd.Timestamp(TRAIN_END)
valid_mask = (df["date"] > pd.Timestamp(TRAIN_END)) & (df["date"] <= pd.Timestamp(VALID_END))
test_mask = df["date"] > pd.Timestamp(VALID_END)

X_train = df.loc[train_mask, feature_cols].fillna(0)
y_train = df.loc[train_mask, "label_rise"]
X_valid = df.loc[valid_mask, feature_cols].fillna(0)
y_valid = df.loc[valid_mask, "label_rise"]
X_test = df.loc[test_mask, feature_cols].fillna(0)
y_test = df.loc[test_mask, "label_rise"]

info(f"Train: {len(X_train):,} rows | rise rate: {y_train.mean()*100:.1f}%")
info(f"Valid: {len(X_valid):,} rows | rise rate: {y_valid.mean()*100:.1f}%")
info(f"Test:  {len(X_test):,} rows | rise rate: {y_test.mean()*100:.1f}%")


# ═══════════════════════════════════════════════════════════════════
# Train RISE model
# ═══════════════════════════════════════════════════════════════════

banner("STEP 4: Train XGBoost (RISE predictor)", C.YELLOW)

scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
info(f"scale_pos_weight: {scale_pos:.2f}")

model = xgb.XGBClassifier(
    n_estimators=500,
    max_depth=4,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.5,
    reg_lambda=1.0,
    scale_pos_weight=scale_pos,
    eval_metric="auc",
    early_stopping_rounds=30,
    random_state=RANDOM_STATE,
    tree_method="hist",
    verbosity=0,
)

info("Training...")
model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
ok(f"Training complete! Used {model.best_iteration + 1} trees.")


# ═══════════════════════════════════════════════════════════════════
# Evaluate
# ═══════════════════════════════════════════════════════════════════

banner("STEP 5: Evaluation", C.GREEN)

for split, X, y in [("Train", X_train, y_train), ("Valid", X_valid, y_valid), ("Test", X_test, y_test)]:
    probs = model.predict_proba(X)[:, 1]
    preds = (probs >= 0.5).astype(int)
    auc = roc_auc_score(y, probs) if len(np.unique(y)) > 1 else float("nan")
    f1 = f1_score(y, preds, pos_label=1, zero_division=0)
    color = C.GREEN if auc >= 0.70 else (C.YELLOW if auc >= 0.60 else C.RED)
    print(f"  {C.B}{split:6s}{C.R}  AUC: {color}{auc:.4f}{C.R}  F1 (rise): {f1:.4f}")


# ═══════════════════════════════════════════════════════════════════
# Top features
# ═══════════════════════════════════════════════════════════════════

banner("STEP 6: Top features for RISE prediction", C.GREEN)

imp = pd.Series(model.feature_importances_, index=feature_cols)
top = imp.sort_values(ascending=False).head(10)
for feat_name, v in top.items():
    bar = "█" * int(v * 100)
    print(f"    {feat_name:30s} {C.BLUE}{bar}{C.R} {v:.3f}")


# ═══════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════

banner("STEP 7: Save BLUE model", C.GREEN)

Path("models/saved").mkdir(parents=True, exist_ok=True)
Path("reports").mkdir(exist_ok=True)

model_path = "models/saved/xgb_blue_signal.json"
model.save_model(model_path)
ok(f"BLUE model saved: {model_path}")

test_probs = model.predict_proba(X_test)[:, 1]
test_preds = (test_probs >= 0.5).astype(int)
test_auc = roc_auc_score(y_test, test_probs) if len(np.unique(y_test)) > 1 else None
test_f1 = f1_score(y_test, test_preds, pos_label=1, zero_division=0)

report = {
    "timestamp": datetime.now().isoformat(),
    "model_type": "blue_signal_rise_predictor",
    "volatility_multiplier": VOLATILITY_MULTIPLIER,
    "future_window_days": FUTURE_WINDOW_DAYS,
    "test_auc": float(test_auc) if test_auc else None,
    "test_f1": float(test_f1),
    "overall_rise_rate": float(df["label_rise"].mean()),
    "rise_rate_by_year": {int(k): float(v) for k, v in rise_by_year.items()},
    "features": feature_cols,
}
report_path = f"reports/blue_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)
ok(f"Report saved: {report_path}")


banner("🎯 BLUE MODEL READY!", C.BLUE)

if test_auc and test_auc >= 0.65:
    print(f"  {C.GREEN}{C.B}✅ Test AUC {test_auc:.4f} — BLUE model is production-ready!{C.R}")
    print(f"  {C.GREEN}Your system now predicts BOTH crashes AND rises.{C.R}")
elif test_auc and test_auc >= 0.55:
    print(f"  {C.YELLOW}Test AUC {test_auc:.4f} — acceptable but could improve.{C.R}")
else:
    print(f"  {C.RED}Test AUC low — rise prediction is harder than crash prediction.{C.R}")
    print(f"  {C.YELLOW}This is OK — use as weak signal, combined with rule engine.{C.R}")

print(f"\n  Next: Update alert_engine.py to use BOTH models.")
print(f"  I'll give you the code in the next message!\n")
