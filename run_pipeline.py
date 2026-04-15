# -*- coding: utf-8 -*-
"""
PHASE 7 — End-to-End Pipeline
Single entry point: loads data → engineers features → loads model → predicts → alerts.
Run: python run_pipeline.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# ── Bootstrap path so imports resolve from project root ───────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import config

# ── Logging setup ──────────────────────────────────────────────────────────────
config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_PIPELINE_FILE, encoding="utf-8"),
    ]
)
log = logging.getLogger("kisanalert.pipeline")


def run() -> dict:
    """
    Full inference pipeline (no training).
    Uses the most recent row of the cleaned DataFrame as today's data.
    """
    run_start = datetime.now()
    log.info("=" * 60)
    log.info("KisanAlert Pipeline Started — %s", run_start.strftime("%Y-%m-%d %H:%M:%S"))
    log.info("=" * 60)

    # ── Phase 1: Load & clean data ─────────────────────────────────────────────
    log.info("[Phase 1] Loading and cleaning data...")
    try:
        from src.data.loader import load_clean_data
        df_clean = load_clean_data()
    except FileNotFoundError as e:
        log.error("❌ Data file missing: %s", e)
        log.error("Download soybean Nanded CSV from https://agmarknet.gov.in and place at:")
        log.error("  %s", config.RAW_CSV_PATH)
        sys.exit(1)
    except Exception as e:
        log.error("❌ Data loading failed: %s", e)
        sys.exit(1)

    # ── Phase 2: Feature engineering ──────────────────────────────────────────
    log.info("[Phase 2] Engineering features...")
    try:
        from src.features.engineer import engineer_features
        df_features = engineer_features(df_clean)
    except Exception as e:
        log.error("❌ Feature engineering failed: %s", e)
        sys.exit(1)

    # ── Phase 4: Load saved model (training was done separately) ──────────────
    log.info("[Phase 4] Loading saved model...")
    try:
        from src.models.xgb_model import load_model
        model = load_model()
    except FileNotFoundError as e:
        log.error("❌ Model file missing: %s", e)
        log.error("Run training first: python -c \"from src.models.xgb_model import *; ...\"")
        sys.exit(1)
    except Exception as e:
        log.error("❌ Model loading failed: %s", e)
        sys.exit(1)

    # ── Inference: most recent row ─────────────────────────────────────────────
    from src.features.engineer import FEATURE_COLUMNS

    today_row   = df_features.iloc[-1]
    today_date  = today_row["date"]
    today_price = today_row["modal_price"]
    X_today     = df_features[FEATURE_COLUMNS].iloc[[-1]]   # shape (1, n_features)

    X_yesterday = None
    if len(df_features) >= 2:
        X_yesterday = df_features[FEATURE_COLUMNS].iloc[[-2]]

    log.info("[Predict] Running inference on %s (₹%.0f/qtl)", today_date.date(), today_price)

    try:
        prob_today = float(model.predict_proba(X_today)[0][1])
        prob_yesterday = float(model.predict_proba(X_yesterday)[0][1]) if X_yesterday is not None else None
        if prob_yesterday is None:
            prob_yesterday = prob_today

        if config.USE_SOFT_CONFIRMATION:
            soft_score = (
                config.SOFT_CONFIRMATION_TODAY_WEIGHT * prob_today
                + config.SOFT_CONFIRMATION_PREV_WEIGHT * prob_yesterday
            )
        else:
            soft_score = prob_today
    except Exception as e:
        log.error("❌ Prediction failed: %s", e)
        sys.exit(1)

    # ── Phase 6: Generate alert ────────────────────────────────────────────────
    log.info(
        "[Phase 6] Generating alert for raw_prob=%.4f, soft_score=%.4f",
        prob_today,
        soft_score,
    )
    from src.alerts.alert_engine import generate_alert, print_alert

    alert = generate_alert(
        crash_score=soft_score,
        date=str(today_date.date()),
        price=today_price,
    )

    # ── Final console output ───────────────────────────────────────────────────
    print("\n" + "═" * 40)
    print("=== KisanAlert — Daily Report ===")
    print(f"Date        : {today_date.date()}")
    print(f"Crop        : {config.TARGET_COMMODITY}")
    print(f"District    : {config.TARGET_DISTRICT}")
    print(f"Price Today : ₹{today_price:,.0f}/qtl")
    print(f"Raw Prob    : {prob_today:.2f}")
    print(f"Prev Prob   : {prob_yesterday:.2f}")
    print(f"Soft Score  : {soft_score:.2f}")
    print(f"Alert Level : {alert['icon']} {alert['alert_level']}")
    print(f"Message     : {alert['marathi_message']}")
    print("=" * 40)

    # ── Phase 8: Push to Supabase ──────────────────────────────────────────────
    try:
        from src.supabase_client import push_daily_alert, log_pipeline_run
        log.info("[Phase 8] Pushing results to Supabase backend...")
        push_daily_alert(
            date=str(today_date.date()),
            price=today_price,
            crash_score=soft_score,
            alert_level=alert['alert_level'],
            message=alert['marathi_message']
        )
        log_pipeline_run(status="SUCCESS")
    except Exception as e:
        log.error("Failed to integrate with Supabase: %s", e)

    run_end = datetime.now()
    log.info("Pipeline completed in %.2f seconds.", (run_end - run_start).total_seconds())
    log.info("Alert log : %s", config.LOG_ALERTS_FILE)
    log.info("Pipeline log: %s", config.LOG_PIPELINE_FILE)

    return alert


def run_full_training() -> None:
    """
    Full training pipeline (Phases 1–4 + evaluation).
    Run this once to train and save the model.
    """
    log.info("🔧 Starting full training pipeline...")

    from src.data.loader import load_clean_data
    from src.features.engineer import engineer_features
    from src.features.labels import create_labels
    from src.models.xgb_model import train_model
    from src.models.evaluate import evaluate

    df_clean = load_clean_data()
    df_feat  = engineer_features(df_clean)
    df_labelled, class_weight = create_labels(df_feat)

    log.info("🏋️  Training XGBoost model...")
    model = train_model(df_labelled, class_weight)

    log.info("📊 Evaluating on 2024 test set...")
    metrics = evaluate(df_labelled)

    log.info("Training complete. Metrics:")
    for k, v in metrics.items():
        log.info("  %-25s: %s", k, v)

    log.info("✅ Model ready. Now run: python run_pipeline.py")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="KisanAlert Pipeline")
    parser.add_argument(
        "--train",
        action="store_true",
        help="Run full training pipeline (Phases 1–4 + evaluation) before inference."
    )
    args = parser.parse_args()

    if args.train:
        run_full_training()

    run()
