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
RAW_CSV_PATH    = RAW_DIR / "cotton_nanded.csv"
TARGET_COMMODITY = "Cotton"
TARGET_DISTRICT  = "Nanded"
DATE_START       = "2021-01-01"   # extended: yearly CSVs cover 2021-2026
DATE_END         = "2026-04-30"

# ── MSP (Minimum Support Price) ────────────────────────────────────────────────
# TODO (Phase 9): Make this dynamic per crop-year via government API
MSP_SOYBEAN_2024 = 4892  # ₹ per quintal

# ── Feature engineering ────────────────────────────────────────────────────────
ARRIVAL_ROLLING_WINDOW = 7   # days for arrival ratio denominator
PRICE_VELOCITY_LAG     = 3   # days for price velocity calculation
DROP_START_ROWS        = 7   # rows to drop at start (rolling window warm-up)

# ── Label creation ─────────────────────────────────────────────────────────────
CRASH_WINDOW_DAYS    = 7     # look-ahead window for crash detection
CRASH_THRESHOLD_PCT  = -8.0  # stronger crash definition (more meaningful events)
CRASH_MIN_ABS_DROP_RUPEES = 200.0  # ignore small %-drops that are not action-worthy
DROP_END_ROWS        = 7     # rows to drop at end (no valid future window)

# Label rate control: auto-pick a threshold on TRAIN period to hit target frequency.
LABEL_AUTO_TUNE = True
LABEL_TARGET_CRASH_RATE = 0.18  # aim ~15–20% positives
LABEL_THRESHOLD_PATH = MODELS_DIR / "label_threshold.txt"

# ── Model settings ─────────────────────────────────────────────────────────────
MODEL_PATH    = MODELS_DIR / "xgb_v1.json"
CALIBRATED_MODEL_PATH = MODELS_DIR / "xgb_v1_calibrated.joblib"
TUNED_THRESHOLD_PATH = MODELS_DIR / "selected_threshold.txt"
TRAIN_END     = "2022-12-31"
VAL_START     = "2023-01-01"
VAL_END       = "2023-12-31"
TEST_START    = "2024-01-01"
TEST_END      = "2024-12-31"
XGB_PARAMS = {
    "max_depth"      : 4,
    "learning_rate"  : 0.05,
    "n_estimators"   : 400,
    "subsample"      : 0.8,
    "colsample_bytree": 0.8,
    "eval_metric"    : "auc",
    "n_jobs"         : -1,
    "random_state"   : 42,
}

USE_CALIBRATION = False
CALIBRATION_METHOD = "sigmoid"
USE_SOFT_CONFIRMATION = True
SOFT_CONFIRMATION_TODAY_WEIGHT = 0.7
SOFT_CONFIRMATION_PREV_WEIGHT = 0.3
EVAL_THRESHOLD_CANDIDATES = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65]

# Reject thresholds that alert too frequently (product guardrail)
MAX_ALERT_RATE = 0.40

# Threshold tuning objective (beta>1 emphasizes recall; beta<2 balances precision more)
EVAL_F_BETA = 1.5

# For signal-debugging runs: skip threshold sweeps and only report AUC + a single confusion matrix
EVAL_TUNE_THRESHOLDS = False

# ── Alert thresholds ───────────────────────────────────────────────────────────
ALERT_GREEN_MAX = 0.40   # score < 0.40 → GREEN
ALERT_RED_MIN   = 0.65   # score >= ALERT_RED_MIN → RED (can be overridden by tuned threshold)
# Between those two → AMBER

# Evaluation guardrails
MIN_RECALL_GUARD = 0.50

ALERT_MESSAGES = {
    "GREEN": "आज सोयाबीन विकणे सुरक्षित आहे. भाव स्थिर आहेत.",
    "AMBER": "सावध राहा. पुढील 2-3 दिवस थांबा आणि परिस्थिती पाहा.",
    "RED"  : "सोयाबीन आज विकू नका! भाव पडण्याची शक्यता आहे.",
}

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_ALERTS_FILE   = LOGS_DIR / "alerts.log"
LOG_PIPELINE_FILE = LOGS_DIR / "pipeline.log"
