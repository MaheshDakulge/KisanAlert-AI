# -*- coding: utf-8 -*-
"""
PHASE 4B — Layer 3: LSTM Deep Learning Model (TensorFlow/Keras)

Learns temporal patterns from raw price sequences that XGBoost cannot capture:
  - Multi-week crash build-up rhythms
  - Seasonal oscillation patterns in post-harvest months (Oct–Jan)
  - Price-velocity gradients across rolling windows

Architecture:
  Input: (lookback, n_lstm_features)  →  LSTM(64) → Dropout → LSTM(32) → Dense(1, sigmoid)

Trains on the same chronological split as XGBoost (no shuffle, no leakage).
Saves model weights to models/saved/lstm_<crop>.keras
"""

import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── LSTM Feature Set (time-series signals only — no static calendar dummies) ──
LSTM_FEATURES = [
    "modal_price",        # raw price
    "price_trend_30d",    # medium-term momentum
    "price_vs_7d_avg",    # short-term momentum
    "price_velocity",     # 3-day rate of change
    "drawdown_7",         # distance from 7-day peak
    "msp_gap",            # government floor pressure
    "arrival_ratio",      # supply shock signal (or spread proxy)
    "surrounding_price",  # lead-market anchor
    "price_wave_lag_score", # inter-district wave
    "rain_7d_sum",        # weather supply-side
]


def _get_active_lstm_features(df: pd.DataFrame) -> list:
    """Return LSTM features present in df (gracefully skip missing cols)."""
    available = [f for f in LSTM_FEATURES if f in df.columns]
    if len(available) < 3:
        raise ValueError(
            f"Too few LSTM features found in DataFrame. Expected ~{len(LSTM_FEATURES)}, "
            f"got {len(available)}: {available}"
        )
    if len(available) < len(LSTM_FEATURES):
        missing = set(LSTM_FEATURES) - set(available)
        log.warning("LSTM: %d feature(s) missing, using %d available: skipped=%s",
                    len(missing), len(available), missing)
    return available


def _build_sequences(df: pd.DataFrame, features: list, lookback: int) -> tuple:
    """
    Slide a window of `lookback` days over df to create (X, y) pairs.
    X shape: (n_samples, lookback, n_features)
    y shape: (n_samples,)
    """
    X_raw = df[features].values.astype(np.float32)
    y_raw = df["label"].values.astype(np.float32)

    X_seq, y_seq = [], []
    for i in range(lookback, len(df)):
        X_seq.append(X_raw[i - lookback: i])   # window
        y_seq.append(y_raw[i])                  # label at end of window

    return np.array(X_seq), np.array(y_seq)


def _scale_features(X_train: np.ndarray, X_val: np.ndarray, X_test: np.ndarray) -> tuple:
    """
    Per-feature min-max normalisation using only training statistics
    (prevents leakage from validation / test distributions).
    Returns (X_train_scaled, X_val_scaled, X_test_scaled, scale_params)
    """
    # Shape: (samples, lookback, features)
    feat_min = X_train.min(axis=(0, 1), keepdims=True)
    feat_max = X_train.max(axis=(0, 1), keepdims=True)
    denom    = (feat_max - feat_min)
    denom[denom == 0] = 1.0   # avoid /0 for constant columns

    X_tr_s  = (X_train - feat_min) / denom
    X_val_s = (X_val   - feat_min) / denom
    X_tst_s = (X_test  - feat_min) / denom

    return X_tr_s, X_val_s, X_tst_s, {"min": feat_min, "max": feat_max}


def _build_model(n_features: int, lookback: int):
    """
    Stacked Bidirectional LSTM with:
      - Layer 1: Bidirectional LSTM(64) — captures forward & backward context
      - Layer 2: LSTM(32)               — distils temporal encoding
      - Dense(16, relu) + Dropout(0.3)
      - Dense(1, sigmoid)               — binary crash probability output
    """
    # Lazy import so TF doesn't load unless training/inference is actually called
    import tensorflow as tf
    from tensorflow.keras import layers, models, regularizers

    inp = layers.Input(shape=(lookback, n_features), name="price_sequence")

    x = layers.Bidirectional(
        layers.LSTM(64, return_sequences=True, kernel_regularizer=regularizers.l2(1e-4)),
        name="bilstm_1"
    )(inp)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)

    x = layers.LSTM(32, return_sequences=False, kernel_regularizer=regularizers.l2(1e-4),
                    name="lstm_2")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)

    x = layers.Dense(16, activation="relu", name="dense_1")(x)
    x = layers.Dropout(0.2)(x)

    out = layers.Dense(1, activation="sigmoid", name="crash_prob")(x)

    model = models.Model(inputs=inp, outputs=out, name="KisanAlert_LSTM")
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=config.LSTM_LR),
        loss="binary_crossentropy",
        metrics=["AUC"],
    )
    log.info("LSTM model built — parameters: %d", model.count_params())
    return model


def _get_class_weight(y_train: np.ndarray) -> dict:
    """Compute positive class weight to handle severe class imbalance."""
    n_neg = float((y_train == 0).sum())
    n_pos = float((y_train == 1).sum())
    if n_pos == 0:
        return {0: 1.0, 1: 1.0}
    ratio = n_neg / n_pos
    log.info("LSTM class weight ratio (neg/pos) = %.2f", ratio)
    return {0: 1.0, 1: min(ratio, 10.0)}   # cap at 10x to avoid over-penalisation


def train_lstm(df: pd.DataFrame) -> None:
    """
    Public entry point — trains the LSTM and saves weights to disk.
    Uses the same strict time-series split as XGBoost (no leakage).

    Args:
        df: Labelled DataFrame with all feature columns + 'label' + 'date'.
    """
    import tensorflow as tf

    tf.random.set_seed(42)
    np.random.seed(42)

    lookback = config.LSTM_LOOKBACK
    features = _get_active_lstm_features(df)
    log.info("LSTM training — lookback=%d, features=%d: %s", lookback, len(features), features)

    # ── Chronological split (same boundaries as XGBoost) ────────────────────────
    train_df = df[df["date"] <= config.TRAIN_END].reset_index(drop=True)
    val_df   = df[(df["date"] >= config.VAL_START) & (df["date"] <= config.VAL_END)].reset_index(drop=True)
    test_df  = df[(df["date"] >= config.TEST_START) & (df["date"] <= config.TEST_END)].reset_index(drop=True)

    log.info("Split → Train: %d  Val: %d  Test: %d", len(train_df), len(val_df), len(test_df))

    # ── Build sequences ──────────────────────────────────────────────────────────
    X_train, y_train = _build_sequences(train_df, features, lookback)
    X_val,   y_val   = _build_sequences(val_df,   features, lookback)
    X_test,  y_test  = _build_sequences(test_df,  features, lookback)

    if len(X_train) == 0 or len(X_val) == 0:
        log.error("Not enough data to build LSTM sequences (lookback=%d). Skipping LSTM training.", lookback)
        return

    # ── Normalise ────────────────────────────────────────────────────────────────
    X_train, X_val, X_test, scale_params = _scale_features(X_train, X_val, X_test)

    # ── Model ────────────────────────────────────────────────────────────────────
    n_features = X_train.shape[2]
    model = _build_model(n_features, lookback)
    model.summary(print_fn=log.info)

    class_weight = _get_class_weight(y_train)

    # ── Callbacks ────────────────────────────────────────────────────────────────
    lstm_path = config.LSTM_MODEL_PATH
    lstm_scale_path = config.LSTM_SCALE_PATH
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_AUC", patience=config.LSTM_PATIENCE,
            mode="max", restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_AUC", factor=0.5, patience=5,
            mode="max", min_lr=1e-6, verbose=1
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(lstm_path), monitor="val_AUC", save_best_only=True,
            mode="max", verbose=1
        ),
    ]

    log.info("🏋️  Fitting LSTM (epochs=%d, batch=%d) …", config.LSTM_EPOCHS, config.LSTM_BATCH_SIZE)
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=config.LSTM_EPOCHS,
        batch_size=config.LSTM_BATCH_SIZE,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=1,
    )

    # ── Evaluate on test ─────────────────────────────────────────────────────────
    from sklearn.metrics import roc_auc_score
    if len(X_test) > 0 and y_test.sum() > 0:
        test_proba = model.predict(X_test, verbose=0).flatten()
        test_auc   = roc_auc_score(y_test, test_proba)
        log.info("✅ LSTM Test AUC-ROC: %.4f", test_auc)
    else:
        log.warning("Test set is empty or has no positives — skipping AUC.")

    # ── Save scale params ────────────────────────────────────────────────────────
    np.savez(str(lstm_scale_path),
             feat_min=scale_params["min"],
             feat_max=scale_params["max"],
             features=np.array(features))
    log.info("✅ LSTM scale params saved to %s", lstm_scale_path)
    log.info("✅ LSTM model saved to %s", lstm_path)

    best_val_auc = max(history.history.get("val_AUC", [0.0]))
    log.info("Best validation AUC during training: %.4f", best_val_auc)


def load_lstm_model():
    """
    Load the saved LSTM model and its scaling parameters from disk.
    Returns (model, scale_params, features) or raises FileNotFoundError.
    """
    import tensorflow as tf

    lstm_path       = config.LSTM_MODEL_PATH
    lstm_scale_path = config.LSTM_SCALE_PATH

    if not lstm_path.exists():
        raise FileNotFoundError(
            f"LSTM model not found at {lstm_path}. Run training first with --train flag."
        )
    if not lstm_scale_path.exists():
        raise FileNotFoundError(
            f"LSTM scale params not found at {lstm_scale_path}. Run training first."
        )

    model = tf.keras.models.load_model(str(lstm_path))
    log.info("LSTM model loaded from %s", lstm_path)

    scale_data = np.load(str(lstm_scale_path), allow_pickle=True)
    scale_params = {
        "min"     : scale_data["feat_min"],
        "max"     : scale_data["feat_max"],
        "features": list(scale_data["features"]),
    }
    log.info("LSTM scale params loaded — features: %s", scale_params["features"])
    return model, scale_params


def predict_lstm(df: pd.DataFrame) -> float:
    """
    Run LSTM inference on the tail of `df` (most recent `lookback` days).

    Returns:
        float: crash probability in [0, 1] from the LSTM, or -1.0 if unavailable.
    """
    try:
        model, scale_params = load_lstm_model()
    except FileNotFoundError as e:
        log.warning("LSTM not available (%s) — LSTM score will be skipped.", e)
        return -1.0   # sentinel: "no LSTM score"

    features = scale_params["features"]
    lookback = config.LSTM_LOOKBACK

    # Check all required features are present
    missing = [f for f in features if f not in df.columns]
    if missing:
        log.warning("LSTM inference: missing columns %s — returning -1.0", missing)
        return -1.0

    if len(df) < lookback:
        log.warning(
            "LSTM inference: only %d rows available, need %d (lookback). "
            "Returning -1.0.", len(df), lookback
        )
        return -1.0

    # Extract the last `lookback` rows
    window = df[features].tail(lookback).values.astype(np.float32)   # (lookback, n_feat)

    # Normalise using training scale params
    feat_min = scale_params["min"]   # (1, 1, n_feat)
    feat_max = scale_params["max"]
    denom    = feat_max - feat_min
    denom[denom == 0] = 1.0

    # Reshape window to (1, lookback, n_feat) for normalisation
    window_3d = window[np.newaxis, ...]   # (1, lookback, n_feat)
    window_scaled = (window_3d - feat_min) / denom

    lstm_prob = float(model.predict(window_scaled, verbose=0)[0][0])
    log.info("LSTM crash probability: %.4f", lstm_prob)
    return lstm_prob


# ── Standalone test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.data.loader import load_clean_data
    from src.features.engineer import engineer_features
    from src.features.labels import create_labels
    import pandas as pd

    df_clean          = load_clean_data()
    df_feat           = engineer_features(df_clean)
    df_labelled, _cw  = create_labels(df_feat)

    train_lstm(df_labelled)
    print("\nLSTM training complete.")

    prob = predict_lstm(df_labelled)
    print(f"LSTM latest crash probability: {prob:.4f}")
