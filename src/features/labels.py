# -*- coding: utf-8 -*-
"""
PHASE 3 — Label Creation
Creates binary crash label: 1 if price drops >15% within next 7 days, else 0.
Computes class weights for XGBoost.
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def create_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Public entry point for Phase 3.

    For each row: look at the minimum price in the next CRASH_WINDOW_DAYS days.
    If it drops more than CRASH_THRESHOLD_PCT from today → label = 1 (crash).

    Returns:
        df_labelled : DataFrame with 'label' column added, last N rows dropped
        class_weight: dict {0: 1.0, 1: ratio} for XGBoost scale_pos_weight
    """
    df = df.copy()
    window = config.CRASH_WINDOW_DAYS
    threshold_pct = float(config.CRASH_THRESHOLD_PCT)
    min_abs_drop = float(getattr(config, "CRASH_MIN_ABS_DROP_RUPEES", 0.0))

    # Forward-looking minimum over the NEXT `window` days (excluding today):
    # future_min[i] = min(modal_price[i+1 : i+window+1])
    s = df["modal_price"]
    future_min = (
        s[::-1]
        .rolling(window=window, min_periods=window)
        .min()[::-1]
        .shift(-1)
    )

    drop_frac = (future_min - s) / s
    df["drop"] = drop_frac

    # Optionally auto-tune the threshold on TRAIN period to hit target crash-rate.
    # This keeps labels meaningful (rarer) without leaking test info.
    threshold_frac = threshold_pct / 100.0
    if bool(getattr(config, "LABEL_AUTO_TUNE", False)):
        target_rate = float(getattr(config, "LABEL_TARGET_CRASH_RATE", 0.18))
        train_end = pd.Timestamp(getattr(config, "TRAIN_END"))
        train_mask = df["date"] <= train_end
        drops_train = drop_frac[train_mask].dropna()
        if len(drops_train) > 50:
            tuned = float(drops_train.quantile(target_rate))
            threshold_frac = tuned
            try:
                config.LABEL_THRESHOLD_PATH.write_text(f"{threshold_frac:.6f}\n", encoding="utf-8")
                log.info("Auto-tuned label threshold saved to %s", config.LABEL_THRESHOLD_PATH)
            except Exception:
                pass
            log.info(
                "Auto-tuned label threshold (train only): %.2f%% at target_rate=%.0f%%",
                100.0 * threshold_frac,
                100.0 * target_rate,
            )

    abs_drop = (s - future_min).fillna(0.0)
    df["label"] = ((drop_frac <= threshold_frac) & (abs_drop >= min_abs_drop)).astype(int)

    # Drop last `window` rows — they have no valid future window
    n_drop = config.DROP_END_ROWS
    df = df.iloc[:-n_drop].reset_index(drop=True)
    log.info("Dropped last %d rows (no valid future window). Remaining: %d", n_drop, len(df))

    # Class distribution
    n_total  = len(df)
    n_crash  = df["label"].sum()
    n_safe   = n_total - n_crash
    crash_pct = 100 * n_crash / n_total

    log.info("Label distribution → 0 (safe): %d  |  1 (crash): %d  |  crash rate: %.1f%%",
             n_safe, n_crash, crash_pct)

    if not (15 <= crash_pct <= 20):
        log.warning(
            "Crash rate %.1f%% is outside expected 15–20%% range. "
            "Consider adjusting CRASH_THRESHOLD_PCT in config.py.",
            crash_pct
        )

    # Class weights: minority class gets higher weight
    class_weight = {0: 1.0, 1: float(n_safe / max(n_crash, 1))}
    log.info("Class weight ratio → {0: %.2f, 1: %.2f}", class_weight[0], class_weight[1])

    _validate_labels(df, crash_pct)
    return df, class_weight


def _validate_labels(df: pd.DataFrame, crash_pct: float) -> None:
    """Assert label quality gates."""
    assert df["label"].isin([0, 1]).all(), "Label contains values other than 0 and 1!"
    assert df["label"].isna().sum() == 0, "Label column has NaN values!"

    # Spot-check: Oct–Nov 2021 soybean crash should have crash labels
    oct_nov_2021 = df[
        (df["date"].dt.year == 2021) &
        (df["date"].dt.month.isin([9, 10, 11]))
    ]
    if len(oct_nov_2021) > 0:
        crash_in_period = oct_nov_2021["label"].sum()
        log.info("Oct–Nov 2021 crash check: %d crash labels in %d rows (%.0f%%)",
                 crash_in_period, len(oct_nov_2021),
                 100 * crash_in_period / len(oct_nov_2021))
    else:
        log.warning("No Oct–Nov 2021 rows found — check date range in data.")

    log.info("✅ Phase 3 validation passed.")


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from src.data.loader import load_clean_data
    from src.features.engineer import engineer_features

    df_clean  = load_clean_data()
    df_feat   = engineer_features(df_clean)
    df_labelled, cw = create_labels(df_feat)

    print(df_labelled[["date", "modal_price", "label"]].head(20))
    print(f"\nFinal shape: {df_labelled.shape}")
    print(f"Class weights: {cw}")
