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
ROOT = Path(__file__).parent / "kisanalert"
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

    # ── Phase 3: Inject Live Data (Automation Upgrade) ─────────────────────────
    log.info("[Phase 3] Fetching live data for real-time automation...")
    try:
        from src.data.live_price_fetcher import fetch_live_price
        live_data = fetch_live_price(config.TARGET_COMMODITY, config.TARGET_DISTRICT)
        
        # If we got live data, inject it as the final row for prediction
        # (Only if it's newer or we want to ensure today's price is represented)
        last_date = df_features['date'].iloc[-1].date()
        today = datetime.now().date()
        
        if live_data:
            log.info("✅ Live data fetched: ₹%.0f/qtl in %s", live_data['modal_price'], live_data['market'])
            # Create a new row matching the features structure
            # For this simple hackathon pipeline, we'll replace the last row's price/qty
            # if the CSV is lagging behind today.
            df_features.loc[df_features.index[-1], "modal_price"] = live_data['modal_price']
            df_features.loc[df_features.index[-1], "arrival_qty"] = live_data['arrival_qty']
            if "min_price" in df_features.columns:
                df_features.loc[df_features.index[-1], "min_price"] = live_data.get('min_price', live_data['modal_price'])
            if "max_price" in df_features.columns:
                df_features.loc[df_features.index[-1], "max_price"] = live_data.get('max_price', live_data['modal_price'])
    except Exception as e:
        log.warning("⚠️ Live data fetch failed, continuing with CSV data: %s", e)

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
    # The model v3 expects exactly 32 features as listed below:
    MODEL_FEATURES = [
        'modal_price', 'arrival_qty', 'min_price', 'max_price', 'hingoli_price', 
        'latur_price', 'parbhani_price', 'surrounding_price', 'usd_inr', 'cbot_close', 
        'cbot_weekly_change', 'price_spread_ratio', 'price_velocity', 'price_trend_30d', 
        'arrival_ratio', 'price_vs_7d_avg', 'rain_7d_sum', 'temp_7d_avg', 
        'is_raining_today', 'weather_shock_flag', 'month', 'day_of_week', 'year_norm', 
        'price_wave_lag_score', 'acceleration', 'distance_from_min', 'trend_strength', 
        'drawdown_7', 'cbot_price_inr', 'cbot_7day_trend', 'days_from_harvest_start', 'msp_gap'
    ]

    today_row   = df_features.iloc[-1]
    today_date  = today_row["date"]
    today_price = today_row["modal_price"]
    
    # Ensure all required features exist in df_features
    for col in MODEL_FEATURES:
        if col not in df_features.columns:
            log.warning(f"Feature {col} missing in engineered data. Filling with 0.")
            df_features[col] = 0.0

    X_today     = df_features[MODEL_FEATURES].iloc[[-1]]   # shape (1, 32)

    X_yesterday = None
    if len(df_features) >= 2:
        X_yesterday = df_features[MODEL_FEATURES].iloc[[-2]]

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
    from src.alerts.alert_engine import generate_alert
    
    # Calculate peak for the 4-signal logic
    price_30d_max = float(df_features["modal_price"].tail(30).max())
    recent_prices = df_features["modal_price"].tail(14)

    alert = generate_alert(
        features_row=X_today,
        current_price=today_price,
        price_30d_max=price_30d_max,
        recent_prices=recent_prices,
        crop=config.TARGET_COMMODITY,
        district=config.TARGET_DISTRICT
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
    print(f"Alert Level : {alert['alert_level']}")
    print(f"Message     : {alert['message_marathi']}")
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
            message=alert['message_marathi']
        )
        log_pipeline_run(status="SUCCESS")
    except Exception as e:
        log.error("Failed to integrate with Supabase: %s", e)

    # ── Phase 10: FCM Push Notification to Farmer's Phone ──────────────────────
    try:
        from src.alerts.fcm_notifier import broadcast_data_refresh, broadcast_crash_alert
        log.info("[Phase 10] Sending FCM push notification to farmers...")

        # Always send a DATA_REFRESH so the Flutter app silently reloads
        broadcast_data_refresh(
            commodity=config.TARGET_COMMODITY,
            price=float(today_price),
            alert_level=alert['alert_level'],
            message_mr=alert['message_marathi'],
        )

        # If RED alert, also send a loud CRASH ALERT notification
        if alert['alert_level'] == "RED":
            broadcast_crash_alert(
                commodity=config.TARGET_COMMODITY,
                price=float(today_price),
                alert_message=alert['message_marathi'],
            )
            log.info("[Phase 10] 🚨 RED alert FCM sent for %s @ ₹%.0f", config.TARGET_COMMODITY, today_price)
        else:
            log.info("[Phase 10] ✅ DATA_REFRESH FCM sent for %s [%s] @ ₹%.0f", config.TARGET_COMMODITY, alert['alert_level'], today_price)
    except Exception as e:
        log.error("[Phase 10] FCM notification failed (non-blocking): %s", e)

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
