# -*- coding: utf-8 -*-
"""
PHASE 2 — Feature Engineering
Adds exactly 5 features to the clean DataFrame from Phase 1.
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

FEATURE_COLUMNS = [
    "price_trend_30d",
    "month",
    "msp_gap",
    "distance_from_min",
    "trend_strength",
    "drawdown_7",
]


def add_price_spread_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    price_spread_ratio = (max_price - min_price) / modal_price

    Measures intra-day price volatility across markets.
    A wide spread (> 0.10) means buyers and sellers are far apart —
    a strong early-warning signal for impending price crashes.

    Replaces arrival_ratio which required arrival_qty (not in yearly CSVs).
    Falls back to 0.0 if min/max price columns are absent.
    """
    if "min_price" in df.columns and "max_price" in df.columns:
        modal = df["modal_price"].replace(0, np.nan)
        df["price_spread_ratio"] = (
            (df["max_price"] - df["min_price"]) / modal
        ).clip(lower=0).fillna(0)
    else:
        log.warning("min_price / max_price not found — price_spread_ratio set to 0.")
        df["price_spread_ratio"] = 0.0
    return df


def add_price_velocity(df: pd.DataFrame) -> pd.DataFrame:
    """
    price_velocity = (price_today - price_3daysago) / price_3daysago.
    Falling fast = early warning signal.
    """
    price_lag = (
        df["modal_price"]
        .shift(config.PRICE_VELOCITY_LAG)
        .replace(0, np.nan)        # avoid division by zero
    )
    df["price_velocity"] = (df["modal_price"] - price_lag) / price_lag
    # Replace any inf that slipped through
    df["price_velocity"] = df["price_velocity"].replace([np.inf, -np.inf], np.nan).ffill()
    return df


def add_price_trend_30d(df: pd.DataFrame) -> pd.DataFrame:
    """
    price_trend_30d = (price_today - rolling_30d_mean) / rolling_30d_mean.
    If negative, we have been in a sustained downward trend for a month.
    """
    rolling_30d = df["modal_price"].rolling(30, min_periods=5).mean()
    df["price_trend_30d"] = (df["modal_price"] - rolling_30d) / rolling_30d
    df["price_trend_30d"] = df["price_trend_30d"].fillna(0.0)
    return df

def add_advanced_proxy_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simulate supply-demand behavior using price itself.
    """
    # 1. Acceleration (Short term drop faster than long term = crash signal)
    vel_3 = df['modal_price'].pct_change(3)
    vel_7 = df['modal_price'].pct_change(7)
    df['acceleration'] = (vel_3 - vel_7).fillna(0)

    # 2. Rolling Min Distance (Price close to recent low = weak market)
    rolling_min_7 = df['modal_price'].rolling(7, min_periods=3).min()
    df['distance_from_min'] = (df['modal_price'] - rolling_min_7).fillna(0)

    # 3. Trend Strength (Strong negative = downtrend confirmation)
    ma_7 = df['modal_price'].rolling(7, min_periods=3).mean()
    ma_30 = df['modal_price'].rolling(30, min_periods=5).mean()
    df['trend_strength'] = ((ma_7 - ma_30) / ma_30).fillna(0)

    # 4. Drawdown from recent peak (high-signal crash indicator)
    rolling_max_7 = df["modal_price"].rolling(7, min_periods=3).max()
    denom = rolling_max_7.replace(0, np.nan)
    df["drawdown_7"] = ((df["modal_price"] - rolling_max_7) / denom).fillna(0.0)

    return df


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    month       = integer 1–12   (Oct–Nov always lowest soybean prices)
    day_of_week = integer 0–6    (Monday always highest arrivals)
    """
    df["month"]       = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek
    return df


def add_msp_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    msp_gap = modal_price − MSP_SOYBEAN_2024.
    Negative = distress selling zone.
    # TODO (Phase 9 multi-crop): Make MSP dynamic per crop-year via API.
    """
    df["msp_gap"] = df["modal_price"] - config.MSP_SOYBEAN_2024
    return df


def drop_warmup_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop first N rows where rolling features are not yet stable."""
    n = config.DROP_START_ROWS
    df = df.iloc[n:].reset_index(drop=True)
    log.info("Dropped first %d warm-up rows. Remaining: %d", n, len(df))
    return df


def validate_features(df: pd.DataFrame) -> None:
    """Assert all 5 features are clean."""
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Feature column '{col}' missing!"
        null_count = df[col].isna().sum()
        assert null_count == 0, f"Feature '{col}' has {null_count} NaN values!"
        inf_count = np.isinf(df[col]).sum()
        assert inf_count == 0, f"Feature '{col}' has {inf_count} infinite values!"

    assert df["month"].between(1, 12).all(), "month values outside 1-12!"
    assert df["day_of_week"].between(0, 6).all(), "day_of_week outside 0-6!"

    # price_spread_ratio: 0-1 range expected, warn if mean > 0.3
    psr_mean = df["price_spread_ratio"].mean()
    log.info("price_spread_ratio mean: %.3f  (>0.10 = high volatility day)", psr_mean)
    if psr_mean > 0.3:
        log.warning("price_spread_ratio mean %.3f seems high - verify data.", psr_mean)

    # msp_gap negative means price is below MSP
    below_msp = (df["msp_gap"] < 0).sum()
    log.info("Days with price below MSP: %d (%.1f%%)", below_msp, 100 * below_msp / len(df))

    log.info("Phase 2 validation passed.")



def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Public entry point for Phase 2.
    Takes clean Phase 1 DataFrame, adds 6 features, drops warm-up rows.
    """
    df = df.copy()
    df = add_price_spread_ratio(df)
    df = add_price_velocity(df)
    df = add_price_trend_30d(df)
    df = add_calendar_features(df)
    df = add_advanced_proxy_signals(df)
    df = add_msp_gap(df)
    df = drop_warmup_rows(df)
    validate_features(df)

    log.info("-" * 60)
    log.info("Phase 2 complete. Shape with features: %s", df.shape)
    log.info("Features added: %s", FEATURE_COLUMNS)
    log.info("price_spread_ratio -> mean: %.3f  std: %.3f",
             df["price_spread_ratio"].mean(), df["price_spread_ratio"].std())
    log.info("price_velocity     -> mean: %.4f  std: %.4f",
             df["price_velocity"].mean(), df["price_velocity"].std())
    log.info("msp_gap            -> mean: Rs.%.0f  (negative = below MSP)",
             df["msp_gap"].mean())
    log.info("-" * 60)

    return df


# Standalone test
if __name__ == "__main__":
    from src.data.loader import load_clean_data
    df_clean = load_clean_data()
    df_feat  = engineer_features(df_clean)
    print(df_feat[["date", "modal_price"] + FEATURE_COLUMNS].head(15))

    # Oct-Nov rows: typically lowest prices / highest spreads
    oct_nov = df_feat[df_feat["month"].isin([10, 11])]
    print("\nOct-Nov sample:")
    print(oct_nov[["date", "price_velocity", "price_spread_ratio", "msp_gap"]].head(10))
