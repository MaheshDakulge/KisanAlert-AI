# -*- coding: utf-8 -*-
"""
KisanAlert — Central Configuration
All tuneable constants in one place.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Project root ───────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR.parent / ".env")

# ── Supabase Configuration ─────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR        = ROOT_DIR / "data"
RAW_DIR         = DATA_DIR / "raw"
YEARLY_DIR      = DATA_DIR / "yearly"   # source: Agmarknet yearly price reports
PROCESSED_DIR   = DATA_DIR / "processed"
CACHE_DIR       = DATA_DIR / "cache"
MODELS_DIR      = ROOT_DIR / "models" / "saved"
LOGS_DIR        = ROOT_DIR / "logs"

# Ensure directories exist
for _d in [RAW_DIR, PROCESSED_DIR, CACHE_DIR, MODELS_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Data settings ──────────────────────────────────────────────────────────────
RAW_CSV_PATH    = RAW_DIR / "soybean_nanded.csv"
SUPPORTED_CROPS = ["Soybean", "Cotton", "Turmeric"]
TARGET_COMMODITY = "Soybean"  # Default fallback if no flag
TARGET_DISTRICT  = "Nanded"
DATE_START       = "2021-01-01"   # extended: yearly CSVs cover 2021-2026
DATE_END         = "2026-04-30"

# ── MSP (Minimum Support Price) ────────────────────────────────────────────────
MSP_2024 = {
    "Soybean": 4892,
    "Cotton": 7521,     # long-staple
    "Turmeric": 10000   # rough estimate for Nanded
}

# ── District Coordinates ───────────────────────────────────────────────────────
DISTRICT_COORDINATES = {
    "Nanded": {"lat": 19.15, "lon": 77.30},
    "Wardha": {"lat": 20.73, "lon": 78.60},
    "Yavatmal": {"lat": 20.40, "lon": 78.13}
}



# ── Feature engineering ────────────────────────────────────────────────────────
ARRIVAL_ROLLING_WINDOW = 7   # days for arrival ratio denominator
PRICE_VELOCITY_LAG     = 3   # days for price velocity calculation
DROP_START_ROWS        = 7   # rows to drop at start (rolling window warm-up)

# ── Label creation ─────────────────────────────────────────────────────────────
CRASH_WINDOW_DAYS    = 7     # look-ahead window for crash detection
# -7% in 7 days = ~Rs.350 drop at Rs.5000 price — more uniform crash rate across years
# Previously -10% caused 2024 val to have only 5 crash events (1.4%) → AUC collapse
CRASH_THRESHOLD_PCT  = -7.0
CRASH_MIN_ABS_DROP_RUPEES = 100.0  # ignore tiny %-drops that aren't action-worthy
DROP_END_ROWS        = 7     # rows to drop at end (no valid future window)

# Label rate control: OFF — use fixed threshold for consistent cross-year labels.
# Auto-tune was causing AUC < 0.5 (model inverted) because 2024 crash rate
# was only 1% vs the 18% seen in 2021–2022 training data.
LABEL_AUTO_TUNE = False
LABEL_TARGET_CRASH_RATE = 0.18  # not used when LABEL_AUTO_TUNE=False
LABEL_THRESHOLD_PATH = MODELS_DIR / "label_threshold.txt"

# ── Model settings ─────────────────────────────────────────────────────────────

# To allow dynamic loading, we define these as properties by overriding the module's __getattr__
def __getattr__(name):
    if name == "MODEL_PATH":
        return MODELS_DIR / f"xgb_v1_{TARGET_COMMODITY.lower()}.json"
    if name == "CALIBRATED_MODEL_PATH":
        return MODELS_DIR / f"xgb_v1_{TARGET_COMMODITY.lower()}_calibrated.joblib"
    if name == "TUNED_THRESHOLD_PATH":
        return MODELS_DIR / f"selected_threshold_{TARGET_COMMODITY.lower()}.txt"
    if name == "LOG_ALERTS_FILE":
        return LOGS_DIR / f"alerts_{TARGET_COMMODITY.lower()}.log"
    if name == "LOG_PIPELINE_FILE":
        return LOGS_DIR / f"pipeline_{TARGET_COMMODITY.lower()}.log"
    # ── LSTM dynamic paths (per-crop) ──────────────────────────────────────────
    if name == "LSTM_MODEL_PATH":
        return MODELS_DIR / f"lstm_{TARGET_COMMODITY.lower()}.keras"
    if name == "LSTM_SCALE_PATH":
        return MODELS_DIR / f"lstm_{TARGET_COMMODITY.lower()}_scale.npz"
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Extended training: 3 years (2021-2023). Val: 2024. Test: 2025.
# eval_metric=aucpr handles extreme class imbalance far better than plain auc
TRAIN_END     = "2023-12-31"
VAL_START     = "2024-01-01"
VAL_END       = "2024-12-31"
TEST_START    = "2025-01-01"
TEST_END      = "2025-12-31"
XGB_PARAMS = {
    "max_depth"       : 5,
    "learning_rate"   : 0.04,
    "n_estimators"    : 600,
    "subsample"       : 0.8,
    "colsample_bytree": 0.7,
    "min_child_weight": 5,
    "gamma"           : 1,
    "reg_alpha"       : 0.1,
    "reg_lambda"      : 1.0,
    "eval_metric"     : "aucpr",   # AUC-PR handles severe class imbalance; auc collapses at 1.4% crash rate
    "n_jobs"          : -1,
    "random_state"    : 42,
}

USE_CALIBRATION = False
CALIBRATION_METHOD = "sigmoid"
USE_SOFT_CONFIRMATION = True
SOFT_CONFIRMATION_TODAY_WEIGHT = 0.7
SOFT_CONFIRMATION_PREV_WEIGHT = 0.3
EVAL_THRESHOLD_CANDIDATES = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]

# ── LSTM (Layer 3) Hyperparameters ─────────────────────────────────────────────
LSTM_LOOKBACK    = 30        # days of history fed as one sequence (blueprint: 30-day window)
LSTM_EPOCHS      = 80        # max epochs (EarlyStopping kicks in early)
LSTM_BATCH_SIZE  = 32
LSTM_LR          = 1e-3      # Adam learning rate
LSTM_PATIENCE    = 12        # EarlyStopping patience (val_AUC)
USE_LSTM         = True      # set False to skip LSTM entirely

# ── Ensemble Weights (Layer 1 LSTM + Layer 2 XGBoost + Layer 3 Rule Engine) ─────────
# Blueprint formula: crash_score = 0.4×LSTM + 0.4×XGBoost + 0.2×rule_score
ENSEMBLE_XGB_WEIGHT  = 0.40  # matches blueprint
ENSEMBLE_LSTM_WEIGHT = 0.40  # matches blueprint
ENSEMBLE_RULE_WEIGHT = 0.20  # rule_score component (0.0=no override, 1.0=full override)

# Reject thresholds that alert too frequently (product guardrail)
MAX_ALERT_RATE = 0.40

# Threshold tuning objective (beta>1 emphasizes recall; beta<2 balances precision more)
EVAL_F_BETA = 1.5

# For signal-debugging runs: skip threshold sweeps and only report AUC + a single confusion matrix
EVAL_TUNE_THRESHOLDS = True  # run F-beta sweep to find the optimal operating threshold

# ── Alert thresholds ───────────────────────────────────────────────────────────
ALERT_GREEN_MAX = 0.35   # score < 0.35 → GREEN  (blueprint: GREEN < 0.35)
ALERT_RED_MIN   = 0.65   # score >= 0.65 → RED    (blueprint: RED > 0.65)
# Between those two → AMBER (blueprint: AMBER 0.35–0.65)

# Evaluation guardrails
MIN_RECALL_GUARD = 0.50

ALERT_MESSAGES = {
    "GREEN": "आज सोयाबीन विकणे सुरक्षित आहे. भाव स्थिर आहेत.",
    "AMBER": "सावध राहा. पुढील 2-3 दिवस थांबा आणि परिस्थिती पाहा.",
    "RED"  : "सोयाबीन आज विकू नका! भाव पडण्याची शक्यता आहे.",
}

# ── Logging ────────────────────────────────────────────────────────────────────
# LOG_ALERTS_FILE and LOG_PIPELINE_FILE are handled by __getattr__ for dynamic paths.

# ── v2 Model Paths (production — no leakage) ───────────────────────────────────
CRASH_MODEL_PATH   = MODELS_DIR / "xgb_v3_best.json"       # AUC 0.76
RISE_MODEL_PATH    = MODELS_DIR / "xgb_blue_signal.json"    # AUC 0.70

# ── 4-Signal Alert Thresholds ──────────────────────────────────────────────────
CRASH_THRESHOLD          = 0.65   # crash_score ≥ this → RED
BLUE_THRESHOLD           = 0.60   # rise_score ≥ this (+ trend) → BLUE
BLUE_SAFE_CRASH_CEIL     = 0.35   # BLUE only fires when crash risk is low
PEAK_THRESHOLD           = 0.97   # price ≥ 97% of 30d max → GREEN
LOW_RISK_CEILING         = 0.35   # alias for GREEN condition

# ── Ensemble v2 Weights ─────────────────────────────────────────────────────────
# v2 blueprint: crash = 0.60×XGB + 0.30×LSTM + 0.10×rule
# (Previously 0.40/0.40/0.20 — updated to give XGB more weight after AUC fix)
ENSEMBLE_XGB_WEIGHT  = 0.60
ENSEMBLE_LSTM_WEIGHT = 0.30
ENSEMBLE_RULE_WEIGHT = 0.10

# ── Trust Badge Settings ────────────────────────────────────────────────────────
VERIFY_WINDOW_DAYS           = 7     # days after prediction to check actual price
SIGNIFICANT_PRICE_CHANGE_PCT = 3.0   # minimum % move for RED/BLUE to be "correct"
