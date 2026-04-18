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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Base feature set — arrival_ratio may be swapped out for zero-arrival crops at runtime
FEATURE_COLUMNS = [
    "price_trend_30d",
    "month",
    "msp_gap",
    "distance_from_min",
    "trend_strength",
    "drawdown_7",
    "arrival_ratio",
    "price_vs_7d_avg",
    "rain_7d_sum",
    "temp_7d_avg",
    "is_raining_today",
    "weather_shock_flag",
    "year_norm",
    "surrounding_price",
    "price_wave_lag_score",
    "cbot_price_inr",
    "cbot_7day_trend",
    "days_from_harvest_start",
]

# Runtime-active feature list (updated by engineer_features for zero-arrival crops)
_ACTIVE_FEATURE_COLUMNS: list = list(FEATURE_COLUMNS)


def get_feature_columns() -> list:
    """Returns the currently active feature column list. Always call this instead of
    reading FEATURE_COLUMNS directly to handle zero-arrival crop swaps correctly."""
    return list(_ACTIVE_FEATURE_COLUMNS)


from src.features.weather_features import add_weather_features


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

def add_arrival_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    arrival_ratio = arrival_qty_today / 7_day_rolling_avg_arrival
    Spikes > 1.0 indicate flood of supply -> crash risk.
    """
    rolling_7d_arr = df["arrival_qty"].rolling(config.ARRIVAL_ROLLING_WINDOW, min_periods=3).mean()
    rolling_7d_arr = rolling_7d_arr.replace(0, np.nan)
    df["arrival_ratio"] = (df["arrival_qty"] / rolling_7d_arr).fillna(0.0)
    return df

def add_price_vs_7d_avg(df: pd.DataFrame) -> pd.DataFrame:
    """
    price_vs_7d_avg = price_today / 7_day_rolling_avg_price - 1
    Short-term momentum.
    """
    rolling_7d_price = df["modal_price"].rolling(7, min_periods=3).mean()
    df["price_vs_7d_avg"] = ((df["modal_price"] / rolling_7d_price) - 1).fillna(0.0)
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


def add_cbot_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes CBOT parity price in INR and 7-day trend.
    1 soybean bushel = ~27.215 kg.
    So, 1 metric tonne = 36.74 bushels.
    1 quintal = 100 kg = 3.674 bushels.
    cbot_price_inr = cbot_close (cents/bushel) * 10 (to $/bushel) * usd_inr / 36.74
    Wait, cbot is in Cents per bushel. So cbot_close/100 is USD per bushel.
    USD per quintal = (cbot_close / 100) * 3.674
    INR per quintal = USD per quintal * usd_inr.
    """
    if "cbot_close" in df.columns:
        # Prevent division by zero and nulls
        cbot = df["cbot_close"].fillna(1200.0)
        inr  = df["usd_inr"].fillna(83.0)
        
        # cbot is often quoted in cents/bushel. e.g., 1200 = $12.00/bu.
        usd_per_quintal = (cbot / 100) * 3.674
        df["cbot_price_inr"] = (usd_per_quintal * inr).fillna(0.0)
        df["cbot_7day_trend"] = df["cbot_weekly_change"].fillna(0.0)
    else:
        df["cbot_price_inr"] = 0.0
        df["cbot_7day_trend"] = 0.0
    return df


def add_harvest_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes days since the start of the most recent harvest season.
    Harvest starts:
    - Soybean : October 1 (Month 10)
    - Cotton  : November 1 (Month 11)
    - Turmeric: February 1 (Month 2)
    """
    import numpy as np
    
    harvest_months = {
        "Soybean": 10,
        "Cotton": 11,
        "Turmeric": 2
    }
    
    crop = config.TARGET_COMMODITY
    harvest_month = harvest_months.get(crop, 10)
    
    def get_days_from_harvest(current_date):
        # The harvest start date for the "current" cycle.
        # If today's month > harvest month, harvest started this year.
        # If today's month < harvest month, harvest started last year.
        curr_year = current_date.year
        harvest_date = pd.Timestamp(year=curr_year, month=harvest_month, day=1)
        
        if current_date < harvest_date:
            harvest_date = pd.Timestamp(year=curr_year - 1, month=harvest_month, day=1)
            
        return (current_date - harvest_date).days

    df["days_from_harvest_start"] = df["date"].apply(get_days_from_harvest)
    # Scale to roughly 0-1 for NN stability (max ~365)
    df["days_from_harvest_start"] = (df["days_from_harvest_start"] / 365.0).clip(0, 1.0)
    
    return df


def add_blue_signal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 9 features specifically for the BLUE (rise) signal model.
    These features capture recovery momentum after a price dip.
    """
    # 1. up_days_streak_7
    diff = df['modal_price'].diff()
    is_up = (diff > 0).astype(int)
    df['up_days_streak_7'] = is_up.rolling(7, min_periods=1).sum().fillna(0)

    # 2. days_since_low_30
    def get_days_since_low(window):
        return len(window) - 1 - window.argmin() if len(window) > 0 else 0
    df['days_since_low_30'] = df['modal_price'].rolling(30, min_periods=1).apply(get_days_since_low).fillna(0)

    # 3. bounce_from_low_30 & 4. price_vs_30d_min
    rolling_min_30 = df['modal_price'].rolling(30, min_periods=1).min()
    denom = rolling_min_30.replace(0, np.nan)
    df['bounce_from_low_30'] = (df['modal_price'] - rolling_min_30) / denom
    df['price_vs_30d_min'] = (df['modal_price'] / denom) - 1
    df['bounce_from_low_30'] = df['bounce_from_low_30'].fillna(0)
    df['price_vs_30d_min'] = df['price_vs_30d_min'].fillna(0)

    # 5. price_accel_3d (Change in velocity)
    df['price_accel_3d'] = df['price_velocity'].diff(3).fillna(0)

    # 6. price_change_14d
    df['price_change_14d'] = df['modal_price'].pct_change(14).fillna(0)

    # 7. cbot_momentum_7d & 8. cbot_momentum_14d
    if 'cbot_price_inr' in df.columns:
        df['cbot_momentum_7d'] = df['cbot_price_inr'].pct_change(7).fillna(0)
        df['cbot_momentum_14d'] = df['cbot_price_inr'].pct_change(14).fillna(0)
    else:
        df['cbot_momentum_7d'] = 0.0
        df['cbot_momentum_14d'] = 0.0

    # 9. is_recovering (Current price > yesterday AND yesterday was low-ish)
    ma_7 = df['modal_price'].rolling(7, min_periods=1).mean()
    df['is_recovering'] = ((diff > 0) & (df['modal_price'].shift(1) < ma_7.shift(1))).astype(float)

    return df


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    month       = integer 1-12   (Oct-Nov always lowest soybean prices)
    day_of_week = integer 0-6    (Monday always highest arrivals)
    year_norm   = float 0.0-1.0  (2021=0.0, 2026=1.0) — temporal regime drift signal
    """
    df["month"]       = df["date"].dt.month
    df["day_of_week"] = df["date"].dt.dayofweek
    year_min, year_max = 2021, 2026
    df["year_norm"] = (df["date"].dt.year - year_min) / (year_max - year_min)
    df["year_norm"] = df["year_norm"].clip(0.0, 1.0)
    return df


def add_lead_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes the price_wave_lag_score based on the lead markets (surrounding_price).
    Negative correlation means surrounding markets dropped -> predicting Nanded will drop.
    """
    if "surrounding_price" in df.columns:
        # Lag 1 day to represent Surrounding markets' yesterday price affecting Nanded today
        surrounding_shifted = df["surrounding_price"].shift(1)
        df["price_wave_lag_score"] = (surrounding_shifted - df["modal_price"]) / df["modal_price"]
        df["price_wave_lag_score"] = df["price_wave_lag_score"].fillna(0.0)
    else:
        df["surrounding_price"] = df["modal_price"]
        df["price_wave_lag_score"] = 0.0
    return df


def add_msp_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    msp_gap = modal_price − MSP.
    Negative = distress selling zone.
    """
    if "commodity" in df.columns:
        msp_values = df["commodity"].map(config.MSP_2024).fillna(config.MSP_2024[config.TARGET_COMMODITY])
    else:
        msp_values = config.MSP_2024.get(config.TARGET_COMMODITY, config.MSP_2024["Soybean"])
        
    df["msp_gap"] = df["modal_price"] - msp_values
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
    assert df["year_norm"].between(0.0, 1.0).all(), "year_norm values outside 0-1!"

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
    Takes clean Phase 1 DataFrame, adds features, drops warm-up rows.
    For crops where arrival_qty is all zero (Cotton, Turmeric), substitutes
    price_spread_ratio for arrival_ratio to retain a supply-proxy signal.
    """
    global _ACTIVE_FEATURE_COLUMNS
    df = df.copy()
    df = add_price_spread_ratio(df)
    df = add_price_velocity(df)
    df = add_price_trend_30d(df)

    # Detect zero-arrival crops and swap feature accordingly
    has_arrivals = df["arrival_qty"].max() > 0
    if has_arrivals:
        df = add_arrival_ratio(df)
        arrival_feature = "arrival_ratio"
    else:
        log.warning(
            "arrival_qty is all zero — substituting price_spread_ratio for arrival_ratio."
        )
        df["arrival_ratio"] = 0.0  # keep column for schema consistency
        arrival_feature = "price_spread_ratio"

    # Build active feature list with correct arrival proxy
    active = [
        f if f != "arrival_ratio" else arrival_feature
        for f in FEATURE_COLUMNS
    ]
    # Deduplicate in case price_spread_ratio appears twice
    seen: set = set()
    active = [f for f in active if not (f in seen or seen.add(f))]
    _ACTIVE_FEATURE_COLUMNS = active

    df = add_price_vs_7d_avg(df)

    # Weather features
    if "rain_mm" in df.columns:
        df = add_weather_features(df)
    else:
        for wf in ["rain_7d_sum", "temp_7d_avg", "is_raining_today", "weather_shock_flag"]:
            df[wf] = 0.0

    df = add_calendar_features(df)
    df = add_lead_lag_features(df)
    df = add_advanced_proxy_signals(df)
    df = add_cbot_features(df)
    df = add_blue_signal_features(df)
    df = add_harvest_features(df)
    df = add_msp_gap(df)
    df = drop_warmup_rows(df)
    validate_features(df)

    log.info("-" * 60)
    log.info("Phase 2 complete. Shape with features: %s", df.shape)
    log.info("Active feature set (%d): %s", len(_ACTIVE_FEATURE_COLUMNS), _ACTIVE_FEATURE_COLUMNS)
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
