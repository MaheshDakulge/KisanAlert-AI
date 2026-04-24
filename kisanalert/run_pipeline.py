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
        logging.StreamHandler(
            stream=open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1,
                        closefd=False)
        ),
        logging.FileHandler(config.LOG_PIPELINE_FILE, encoding="utf-8"),
    ]
)
log = logging.getLogger("kisanalert.pipeline")


def run(live_price: float = None, live_arrivals: float = None) -> dict:
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
        
        # INJECT LIVE SCRAPED DATA if provided
        if live_price is not None:
            df_clean.loc[df_clean.index[-1], "modal_price"] = live_price
            log.info("💉 Injected LIVE modal_price = %.2f into today's row", live_price)
        if live_arrivals is not None:
            df_clean.loc[df_clean.index[-1], "arrival_qty"] = live_arrivals
            log.info("💉 Injected LIVE arrival_qty = %.2f into today's row", live_arrivals)
            
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

    _meta_cols = {"date", "label", "commodity", "district", "_daily_return", "_volatility_30d"}
    _model_feature_cols = [c for c in df_features.columns if c not in _meta_cols
                           and df_features[c].dtype in ["float64", "int64", "float32", "int32"]]

    today_row   = df_features.iloc[-1]
    today_date  = today_row["date"]
    today_price = today_row["modal_price"]
    
    # Robust feature matching: only pass what the model was trained on
    try:
        model_expected = model.get_booster().feature_names
        if model_expected is None:
            model_expected = []
        # Reindex to ensure order and presence (cast to list to satisfy static type checker)
        X_today = df_features.reindex(columns=list(model_expected), fill_value=0.0).iloc[[-1]]
        X_yesterday = None
        if len(df_features) >= 2:
            X_yesterday = df_features.reindex(columns=list(model_expected), fill_value=0.0).iloc[[-2]]
        log.info("[Predict] Matching model features: %d expected, %d provided (filtered)", len(model_expected), len(_model_feature_cols))
    except Exception as e:
        log.warning("[Predict] Booster feature_names not found, falling back to all numeric features: %s", e)
        X_today     = df_features[_model_feature_cols].iloc[[-1]] 
        X_yesterday = None
        if len(df_features) >= 2:
            X_yesterday = df_features[_model_feature_cols].iloc[[-2]]

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

    # ── Phase 4B: LSTM Inference (Layer 3) ────────────────────────────────────
    lstm_prob       = -1.0    # sentinel — “LSTM unavailable”
    ensemble_method = "xgb_only"
    rule_score      = 0.0     # numeric rule engine component (0.0 / 0.5 / 1.0)

    if getattr(config, "USE_LSTM", True):
        log.info("[Phase 4B] Running LSTM inference...")
        try:
            from src.models.lstm_model import predict_lstm
            lstm_prob = predict_lstm(df_features)
        except Exception as e:
            log.warning("⚠️  LSTM inference failed: %s — falling back to XGBoost-only.", e)

    # ── Phase 10: Rule Engine Overrides ─────────────────────────────────────────
    override = {"override_level": None, "reason": None}
    try:
        from src.data.macro_loader import fetch_macro_data
        from src.models.rule_engine import evaluate_macro_rules
        from src.models.ensemble import override_to_rule_score
        log.info("[Phase 10] Fetching macro data and evaluating rules...")
        df_macro = fetch_macro_data()
        override = evaluate_macro_rules(str(today_date.date()), df_macro, today_row=today_row)
        # Convert override level to numeric rule_score (0.0 / 0.5 / 1.0)
        rule_score = override_to_rule_score(override.get("override_level"))
        log.info("[Phase 10] rule_score=%.2f from override_level=%s",
                 rule_score, override.get("override_level"))
    except Exception as e:
        log.error("❌ Rule Engine failed: %s", e)

    # ── Ensemble Formula (v2): 0.60×XGB + 0.30×LSTM + 0.10×rule ─────────────────
    log.info("[Ensemble v2] XGB=%.4f  LSTM=%.4f  rule=%.2f", soft_score, lstm_prob, rule_score)
    try:
        from src.models.ensemble import ensemble_score
        soft_score, ensemble_method = ensemble_score(
            xgb_prob   = soft_score,
            lstm_prob  = lstm_prob,
            rule_score = rule_score,
        )
    except Exception as e:
        log.warning("⚠️  Ensemble failed (%s) — retaining XGBoost soft_score.", e)

    # Hard overrides AFTER ensemble (Rule Engine can still force RED/GREEN ceiling)
    if override.get("override_level") == "RED":
        soft_score = max(soft_score, config.ALERT_RED_MIN)   # at least RED threshold
        log.info("[Rule Override] Force RED floor applied.")
    elif override.get("override_level") == "GREEN":
        soft_score = min(soft_score, config.ALERT_GREEN_MAX - 0.01)  # cap below GREEN threshold
        log.info("[Rule Override] Force GREEN cap applied.")

    # ── Phase 6: Generate alert ────────────────────────────────────────────────
    log.info(
        "[Phase 6] Generating alert for raw_prob=%.4f, soft_score=%.4f",
        prob_today,
        soft_score,
    )
    from src.alerts.edge_handler import generate_safe_alert

    features_row = df_features[_model_feature_cols].iloc[[-1]]
    current_price = float(today_price)
    price_30d_max = float(df_features["modal_price"].tail(30).max())
    last_14_days_prices = df_features["modal_price"].tail(14)

    alert = generate_safe_alert(
        features_row=features_row,
        current_price=current_price,
        price_30d_max=price_30d_max,
        recent_prices=last_14_days_prices,   # ← NEW: pass recent prices
        crop="Soybean",
        district="Nanded",
    )

    # ── Phase 8A: Trust Badge — Log this prediction ────────────────────────────
    try:
        from src.alerts.trust_badge import log_prediction, verify_predictions
        log_prediction(alert, current_price=current_price)
        log.info("[Trust Badge] Prediction logged.")
        # Verify any past predictions whose 7-day window has now elapsed
        price_history = df_features[["date", "modal_price"]].copy()
        price_history["date"] = price_history["date"].astype(str)
        summary = verify_predictions(price_history)
        if summary["newly_verified"] > 0:
            log.info("[Trust Badge] Verified %d past predictions.", summary["newly_verified"])
    except Exception as e:
        log.warning("Trust badge logging skipped: %s", e)

    # ── Final console output ───────────────────────────────────────────────────
    alert_lvl  = alert.get("alert_level", "AMBER")
    alert_icon = {"RED": "[RED]", "GREEN": "[GREEN]", "BLUE": "[BLUE]"}.get(alert_lvl, "[AMBER]")
    msg        = alert.get("message_marathi", alert.get("marathi_message", ""))
    rise_score = alert.get("rise_score")
    trend      = alert.get("trend_is_rising")
    forecast   = alert.get("forecast_days", 7)
    action     = alert.get("action", "")

    # Safe print: encode to utf-8 bytes then write directly so Marathi text never
    # triggers cp1252 UnicodeEncodeError on Windows terminals.
    def _p(text: str):
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    sep = "=" * 50
    _p(f"\n{sep}")
    _p("  KisanAlert -- Daily Report")
    _p(sep)
    _p(f"  Date          : {today_date.date()}")
    _p(f"  Crop          : {config.TARGET_COMMODITY}")
    _p(f"  District      : {config.TARGET_DISTRICT}")
    _p(f"  Price Today   : Rs.{today_price:,.0f}/qtl")
    _p(f"  Crash Score   : {soft_score:.4f}  (XGB={prob_today:.4f})")
    _p(f"  Rise Score    : {rise_score:.4f}" if rise_score is not None else "  Rise Score    : N/A (BLUE disabled)")
    _p(f"  Trend Rising  : {'Yes (upward)' if trend else 'No (flat/down)'}")
    _p(f"  Forecast Days : {forecast}")
    _p(f"  Alert Level   : {alert_icon} {alert_lvl}")
    _p(f"  Action        : {action}")
    _p(f"  Message       : {msg}")
    _p(sep)

    # ── Phase 8: Offline Cache (SQLite) ─────────────────────────────────────────
    try:
        from src.data.cache_db import save_alert_to_cache
        save_alert_to_cache(alert)
    except Exception as e:
        log.error("Failed to write to offline SQLite cache: %s", e)

    # ── Phase 9: Push to Supabase ──────────────────────────────────────────────
    try:
        from src.supabase_client import push_daily_alert, log_pipeline_run
        log.info("[Phase 8] Pushing results to Supabase backend...")
        push_daily_alert(
            date=str(today_date.date()),
            price=today_price,
            crash_score=soft_score,
            alert_level=alert_lvl,
            message=msg if isinstance(msg, str) else str(msg)
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

    if getattr(config, "USE_LSTM", True):
        log.info("🧠 Training LSTM model (Layer 3)...")
        from src.models.lstm_model import train_lstm
        train_lstm(df_labelled)

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
    parser.add_argument(
        "--crop",
        type=str,
        help="Override the TARGET_COMMODITY config."
    )
    parser.add_argument(
        "--price",
        type=float,
        help="Inject live scraped modal price for today."
    )
    parser.add_argument(
        "--arrivals",
        type=float,
        help="Inject live scraped arrival quantity for today."
    )
    args = parser.parse_args()

    if args.crop:
        config.TARGET_COMMODITY = args.crop

    if args.train:
        run_full_training()

    run(live_price=args.price, live_arrivals=args.arrivals)
