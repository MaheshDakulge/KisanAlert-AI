# -*- coding: utf-8 -*-
"""
PHASE 5 — Model Evaluation
Evaluates the saved model on 2025 test set.
Prints confusion matrix, classification report, AUC-ROC.
Plots crash probability timeline.
"""

import io
import sys
import logging
from pathlib import Path

# ── Force UTF-8 on Windows so emoji don't crash CP1252 streams ────────────────
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import numpy as np
import xgboost as xgb
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # headless — saves to file, doesn't need a display
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    ConfusionMatrixDisplay,
    fbeta_score,
    precision_recall_fscore_support,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config
from src.features.engineer import get_feature_columns
from src.models.xgb_model import load_model, split_data, get_xy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Minimum acceptable metrics
MIN_PRECISION = 0.55
MIN_RECALL    = 0.60
MIN_F1        = 0.57
MIN_AUC       = 0.65
DEFAULT_THRESHOLD = 0.50


def evaluate(df: pd.DataFrame, threshold: float = DEFAULT_THRESHOLD) -> dict:
    """
    Public entry point for Phase 5.
    Loads saved model and evaluates on test set using configurable soft confirmation.

    NOTE: For crop-specific training runs (Cotton, Turmeric), we load the
    freshly saved crop model (config.MODEL_PATH = xgb_v1_<crop>.json) instead
    of xgb_v3_best.json which is a Soybean-only model with different features.
    """
    # Load the crop-specific model saved during this training run
    crop_model_path = config.MODEL_PATH   # e.g. models/saved/xgb_v1_cotton.json
    if crop_model_path.exists():
        model = xgb.XGBClassifier()
        model.load_model(str(crop_model_path))
        log.info("Evaluate: loaded crop model from %s", crop_model_path)
    else:
        model = load_model()  # fallback to production model
    _, _, test = split_data(df)
    X_test, y_test = get_xy(test)

    # 1. Base probabilities
    prob_today = model.predict_proba(X_test)[:, 1]
    print("Prob stats:")
    print("min:", float(prob_today.min()))
    print("max:", float(prob_today.max()))
    print("mean:", float(prob_today.mean()))

    # 2. Soft confirmation score
    if config.USE_SOFT_CONFIRMATION:
        prob_yesterday = np.roll(prob_today, 1)
        prob_yesterday[0] = prob_today[0]
        decision_score = (
            config.SOFT_CONFIRMATION_TODAY_WEIGHT * prob_today
            + config.SOFT_CONFIRMATION_PREV_WEIGHT * prob_yesterday
        )
    else:
        decision_score = prob_today

    # 3. For signal-debugging runs: skip threshold tuning.
    if not getattr(config, "EVAL_TUNE_THRESHOLDS", True):
        y_pred = (decision_score >= threshold).astype(int)
        best_thresh = threshold
        best_fbeta = float("nan")
    else:
        beta = float(getattr(config, "EVAL_F_BETA", 2.0))
        max_alert_rate = float(getattr(config, "MAX_ALERT_RATE", 1.0))
        best_fbeta = -1.0
        best_thresh = threshold
        best_preds = None

        print("\n" + "=" * 60)
        print(f"PHASE 5 -- THRESHOLD TUNING (F-BETA, beta={beta:g})")
        print("=" * 60)
        print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'F-beta2':<10} | {'False Positives':<15}")
        print("-" * 72)

        for thresh in config.EVAL_THRESHOLD_CANDIDATES:
            y_pred = (decision_score >= thresh).astype(int)
            alert_rate = float(y_pred.mean())
            if alert_rate > max_alert_rate:
                continue

            # Quick metrics
            cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()
            prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, labels=[1], zero_division=0)
            f_beta = fbeta_score(y_test, y_pred, beta=beta, zero_division=0)

            print(f"{thresh:<10.2f} | {prec[0]:<10.2f} | {rec[0]:<10.2f} | {f_beta:<10.2f} | {fp:<15}")

            if f_beta > best_fbeta:
                best_fbeta = f_beta
                best_thresh = thresh
                best_preds = y_pred

        print("\n" + "=" * 60)
        print(f"WINNING THRESHOLD: {best_thresh:.2f}")
        print("=" * 60)
        
        if best_preds is None:
            log.warning("All thresholds exceeded max_alert_rate. Falling back to default threshold.")
            best_preds = (decision_score >= threshold).astype(int)

        y_pred = best_preds
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    
    log.info("Confusion Matrix (threshold=%.2f):\n%s", best_thresh, cm)

    # Classification report
    report = classification_report(y_test, y_pred, labels=[0, 1], target_names=["Safe (0)", "Crash (1)"])
    print("\n" + report)

    # AUC-ROC
    try:
        auc = roc_auc_score(y_test, prob_today)
        log.info("AUC-ROC: %.4f", auc)
        print(f"AUC-ROC : {auc:.4f}")
    except ValueError:
        auc = 0.0
        log.warning("AUC-ROC: Not defined (only one class in test set)")
        print("AUC-ROC : Not defined")
    print("=" * 60)

    # Extract per-class metrics from report dict
    best_prec_arr, best_rec_arr, best_f1_arr, _ = precision_recall_fscore_support(
        y_test, y_pred, labels=[1], zero_division=0
    )
    best_prec = best_prec_arr[0]
    best_rec = best_rec_arr[0]
    best_f1 = best_f1_arr[0]

    # Gate checks
    if best_prec < MIN_PRECISION:
        log.warning("Crash Precision %.2f < %.2f minimum", best_prec, MIN_PRECISION)
    if best_rec < MIN_RECALL:
        log.warning("[WARN] Crash Recall %.2f < %.2f minimum", best_rec, MIN_RECALL)
    if best_rec < config.MIN_RECALL_GUARD:
        log.warning("[WARN] Recall dropped below safe threshold (%.2f < %.2f)!",
                    best_rec, config.MIN_RECALL_GUARD)
    if best_f1 < MIN_F1:
        log.warning("[WARN] Crash F1 %.2f < %.2f minimum", best_f1, MIN_F1)
    if auc < MIN_AUC:
        log.warning("[WARN] AUC %.4f < %.2f minimum", auc, MIN_AUC)

    if tp == 0:
        log.error("❌ Model predicts ZERO true positives. Lower the threshold!")

    # Plot
    _plot_crash_probability(test, decision_score, y_test)

    # Alert Level System Simulation
    green_count = (decision_score < config.ALERT_GREEN_MAX).sum()
    amber_count = ((decision_score >= config.ALERT_GREEN_MAX) & (decision_score < best_thresh)).sum()
    red_count   = (decision_score >= best_thresh).sum()
    print("=" * 60)
    print("ALERT LEVEL DISTRIBUTION (Product View):")
    print(f"  [GREEN] (< {config.ALERT_GREEN_MAX:.2f}) : {green_count} days")
    print(f"  [AMBER] (< {best_thresh:.2f}) : {amber_count} days")
    print(f"  [RED]   (>={best_thresh:.2f}) : {red_count} days")
    print("=" * 60)

    config.TUNED_THRESHOLD_PATH.write_text(f"{best_thresh:.4f}", encoding="utf-8")
    log.info("Selected threshold saved to %s", config.TUNED_THRESHOLD_PATH)

    metrics = {
        "precision_crash": float(best_prec),
        "recall_crash"   : float(best_rec),
        "f1_crash"       : float(best_f1),
        "fbeta_crash"    : float(best_fbeta) if best_fbeta == best_fbeta else None,
        "alert_rate"     : float(np.mean(y_pred)),
        "auc_roc"        : auc,
        "true_positives" : int(tp),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_negatives" : int(tn),
        "best_threshold" : best_thresh
    }
    log.info("Phase 5 evaluation complete.")
    return metrics


def _plot_crash_probability(
    test: pd.DataFrame,
    crash_proba: np.ndarray,
    y_true: pd.Series
) -> None:
    """Plot crash probability over 2024 with actual crash events marked."""
    fig, ax = plt.subplots(figsize=(14, 5))

    dates = test["date"].values

    ax.plot(dates, crash_proba, color="#2196F3", linewidth=1.2, label="Crash Probability")
    ax.axhline(config.ALERT_GREEN_MAX, color="#4CAF50", linestyle="--", linewidth=0.8, label=f"GREEN threshold ({config.ALERT_GREEN_MAX})")
    ax.axhline(config.ALERT_RED_MIN,   color="#F44336", linestyle="--", linewidth=0.8, label=f"RED threshold ({config.ALERT_RED_MIN})")

    # Shade RED zone
    ax.axhspan(config.ALERT_RED_MIN, 1.0, alpha=0.05, color="red")

    # Mark actual crash days
    crash_dates = test["date"][y_true == 1].values
    crash_y     = crash_proba[y_true.values == 1]
    ax.scatter(crash_dates, crash_y, color="#FF5722", s=12, zorder=5,
               label="Actual Crash Day", alpha=0.7)

    ax.set_title("KisanAlert — Soybean Crash Probability (2025 Test Set)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Crash Probability")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=30)
    plt.tight_layout()

    out_path = config.LOGS_DIR / "crash_probability_2025.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    log.info("📊 Plot saved to %s", out_path)


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.data.loader import load_clean_data
    from src.features.engineer import engineer_features
    from src.features.labels import create_labels

    df_clean    = load_clean_data()
    df_feat     = engineer_features(df_clean)
    df_labelled, _ = create_labels(df_feat)

    metrics = evaluate(df_labelled)
    print("\nMetrics summary:")
    for k, v in metrics.items():
        print(f"  {k:25s}: {v}")
