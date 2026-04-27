# -*- coding: utf-8 -*-
"""
PHASE 4 — XGBoost Model Training
Strict time-series split (no shuffle). Trains on 2019–2022, validates on 2023,
tests on 2024. Saves model to disk.
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.calibration import CalibratedClassifierCV
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config
from src.features.engineer import get_feature_columns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def split_data(df: pd.DataFrame):
    """
    Strict chronological split — NO random shuffle.
    Train: 2019–2022 | Val: 2023 | Test: 2024
    """
    train = df[df["date"] <= config.TRAIN_END]
    val   = df[(df["date"] >= config.VAL_START) & (df["date"] <= config.VAL_END)]
    test  = df[(df["date"] >= config.TEST_START) & (df["date"] <= config.TEST_END)]

    log.info("Split sizes → Train: %d  Val: %d  Test: %d", len(train), len(val), len(test))

    # Guard against data leakage
    assert train["date"].max() < pd.Timestamp(config.VAL_START), "Leakage: train overlaps val!"
    assert val["date"].max()   < pd.Timestamp(config.TEST_START), "Leakage: val overlaps test!"

    return train, val, test


def get_xy(df: pd.DataFrame):
    """Extract feature matrix X and label vector y."""
    X = df[get_feature_columns()].copy()
    y = df["label"].copy()
    return X, y


def train_model(df: pd.DataFrame, class_weight: dict):
    """
    Public entry point for Phase 4.
    Trains XGBoost with class weighting. Validates on 2023. Saves model.
    """
    train, val, _ = split_data(df)

    X_train, y_train = get_xy(train)
    X_val,   y_val   = get_xy(val)

    scale_pos_weight = class_weight.get(1, 4.0)
    log.info("Using scale_pos_weight = %.2f", scale_pos_weight)

    params = {**config.XGB_PARAMS, "scale_pos_weight": scale_pos_weight}

    # Remove deprecated parameter if XGBoost >= 1.6
    params.pop("use_label_encoder", None)

    base_model = xgb.XGBClassifier(**params)

    base_model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50
    )

    model = base_model
    if config.USE_CALIBRATION:
        calibration_method = config.CALIBRATION_METHOD
        try:
            model = CalibratedClassifierCV(base_model, method=calibration_method, cv=3)
            model.fit(X_train, y_train)
            log.info("Applied probability calibration with method=%s", calibration_method)
        except Exception as e:
            if calibration_method != "sigmoid":
                log.warning(
                    "Calibration with method=%s failed (%s). Falling back to sigmoid.",
                    calibration_method, e
                )
                model = CalibratedClassifierCV(base_model, method="sigmoid", cv=3)
                model.fit(X_train, y_train)
                log.info("Applied probability calibration with fallback method=sigmoid")
            else:
                raise

    # Validation AUC
    val_proba = model.predict_proba(X_val)[:, 1]
    print("Prob stats:")
    print("min:", float(val_proba.min()))
    print("max:", float(val_proba.max()))
    print("mean:", float(val_proba.mean()))
    val_auc   = roc_auc_score(y_val, val_proba)
    log.info("Validation AUC: %.4f", val_auc)

    if val_auc < 0.65:
        log.warning(
            "⚠️  Validation AUC %.4f is below threshold 0.65. "
            "Model may not have learned useful patterns — check features and labels.",
            val_auc
        )

    # Sanity check — model must predict some 1s
    val_preds = (val_proba >= 0.5).astype(int)
    pred_counts = pd.Series(val_preds).value_counts().to_dict()
    log.info("Val prediction distribution: %s", pred_counts)
    if pred_counts.get(1, 0) == 0:
        log.warning("⚠️  Model predicts ONLY class 0 on validation set! "
                    "Increase scale_pos_weight or lower threshold in evaluation.")

    # Feature importances
    importances = dict(zip(get_feature_columns(), base_model.feature_importances_))
    log.info("Feature importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        log.info("  %-20s %.4f", feat, imp)

    # Save models
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    base_model.save_model(str(config.MODEL_PATH))
    log.info("✅ Base model saved to %s", config.MODEL_PATH)
    if config.USE_CALIBRATION:
        joblib.dump(model, config.CALIBRATED_MODEL_PATH)
        log.info("✅ Calibrated model saved to %s", config.CALIBRATED_MODEL_PATH)

    return model


def load_model():
    """Load calibrated model when enabled, else load raw XGBoost model.

    Priority:
      1. Calibrated model (joblib) — if USE_CALIBRATION is True
      2. xgb_v3_best.json (AUC 0.76, production model)
      3. config.MODEL_PATH fallback  (legacy)
    """
    if config.USE_CALIBRATION and config.CALIBRATED_MODEL_PATH.exists():
        model = joblib.load(config.CALIBRATED_MODEL_PATH)
        log.info("Calibrated model loaded from %s", config.CALIBRATED_MODEL_PATH)
        return model

    # Prefer the new v3 crash model (fixed AUC 0.76, no leakage)
    v3_path = config.MODELS_DIR / "xgb_v3_best.json"
    if v3_path.exists():
        model = xgb.XGBClassifier()
        model.load_model(str(v3_path))
        log.info("✅ Crash model v3 loaded from %s (AUC 0.76)", v3_path)
        return model

    if not config.MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {config.MODEL_PATH}. Run training first."
        )
    model = xgb.XGBClassifier()
    model.load_model(str(config.MODEL_PATH))
    log.info("Base model loaded from %s", config.MODEL_PATH)
    return model


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.data.loader import load_clean_data
    from src.features.engineer import engineer_features
    from src.features.labels import create_labels

    df_clean    = load_clean_data()
    df_feat     = engineer_features(df_clean)
    df_labelled, cw = create_labels(df_feat)

    model = train_model(df_labelled, cw)
    print(f"\nModel type: {type(model)}")
    print(f"Model file: {config.MODEL_PATH}")
