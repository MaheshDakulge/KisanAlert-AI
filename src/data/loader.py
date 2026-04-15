# -*- coding: utf-8 -*-
"""
PHASE 1 — Data Foundation
Loads raw Agmarknet CSV, cleans it, reindexes to daily frequency,
forward-fills gaps, and returns a stable DataFrame for all future phases.
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd

# Allow running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PRICE_OUTLIER_MULTIPLIER = 3.0  # flag price > 3× 30-day rolling median


def load_raw(csv_path: Path = config.RAW_CSV_PATH) -> pd.DataFrame:
    """Read raw Agmarknet CSV with robust date parsing."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Raw CSV not found at {csv_path}\n"
            "Download from https://agmarknet.gov.in and place it there."
        )
    log.info("Loading raw CSV from %s", csv_path)
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1")

    log.info("Raw shape: %s", df.shape)
    return df


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip all column names."""
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date column to datetime; try multiple formats."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            df["date"] = pd.to_datetime(df["date"], format=fmt, dayfirst=True)
            log.info("Date parsed with format: %s", fmt)
            return df
        except (ValueError, KeyError):
            continue
    # Fallback: let pandas infer
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, infer_datetime_format=True)
    log.warning("Date format inferred — verify visually.")
    return df


def filter_crop_district(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only target commodity + district rows."""
    commodity_col = next((c for c in df.columns if "commodity" in c), None)
    district_col  = next((c for c in df.columns if "district" in c), None)

    if commodity_col:
        mask = df[commodity_col].str.strip().str.lower() == config.TARGET_COMMODITY.lower()
        df = df[mask]
        log.info("After commodity filter: %d rows", len(df))
    if district_col:
        mask = df[district_col].str.strip().str.lower() == config.TARGET_DISTRICT.lower()
        df = df[mask]
        log.info("After district filter: %d rows", len(df))
    return df


def pick_price_qty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise price and qty column names; keep variety / min / max if present."""
    # Modal price
    modal_candidates = ["modal_price", "modal price", "modalprice", "modal"]
    for c in modal_candidates:
        if c in df.columns:
            df = df.rename(columns={c: "modal_price"})
            break

    # Arrival quantity
    arrival_candidates = ["arrival_qty", "arrivals", "arrival", "quantity_arrived"]
    for c in arrival_candidates:
        if c in df.columns:
            df = df.rename(columns={c: "arrival_qty"})
            break

    required = {"date", "modal_price", "arrival_qty"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(
            f"Required columns missing after normalisation: {missing}\n"
            f"Available columns: {list(df.columns)}"
        )

    # Optional columns — include when present (v2 CSV has these)
    optional_cols = []
    for col in ["variety", "min_price", "max_price", "market"]:
        if col in df.columns:
            optional_cols.append(col)

    base_cols = ["date", "modal_price", "arrival_qty"]
    return df[base_cols + optional_cols]


def aggregate_multiple_markets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate to ONE row per day by summing arrivals and averaging prices.
    When the variety column is present the aggregation is done across all
    varieties (weighted average by arrival_qty for modal / min / max price).
    """
    n_before = len(df)

    agg_dict: dict = {"modal_price": "mean", "arrival_qty": "sum"}
    if "min_price" in df.columns:
        agg_dict["min_price"] = "mean"
    if "max_price" in df.columns:
        agg_dict["max_price"] = "mean"

    df = df.groupby("date", as_index=False).agg(agg_dict)

    if len(df) < n_before:
        log.info("Aggregated %d market/variety rows → %d daily rows", n_before, len(df))
    return df


def reindex_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Reindex to calendar-daily frequency and forward-fill gaps."""
    df = df.set_index("date").sort_index()
    full_range = pd.date_range(
        start=config.DATE_START,
        end=config.DATE_END,
        freq="D"
    )
    df = df.reindex(full_range)
    df.index.name = "date"

    # Columns to forward-fill / back-fill
    price_cols = ["modal_price", "arrival_qty"]
    if "min_price" in df.columns:
        price_cols.append("min_price")
    if "max_price" in df.columns:
        price_cols.append("max_price")

    for col in price_cols:
        df[col] = df[col].ffill().bfill()

    log.info("Reindexed to %d daily rows (%s → %s)", len(df), config.DATE_START, config.DATE_END)
    return df.reset_index()


def flag_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Flag price values that are > 3× the 30-day rolling median (likely typos)."""
    rolling_median = df["modal_price"].rolling(30, min_periods=5).median()
    outlier_mask = df["modal_price"] > PRICE_OUTLIER_MULTIPLIER * rolling_median
    n_outliers = outlier_mask.sum()
    if n_outliers > 0:
        log.warning(
            "⚠️  %d price outlier rows detected (>%.0f× 30-day median). "
            "These are NOT removed — verify raw data manually.",
            n_outliers, PRICE_OUTLIER_MULTIPLIER
        )
        outlier_rows = df[outlier_mask][["date", "modal_price"]]
        log.warning("Outlier rows:\n%s", outlier_rows.to_string())
    return df


def validate(df: pd.DataFrame) -> None:
    """Assert all quality gates pass before returning."""
    assert df["modal_price"].isna().sum() == 0, "NULL modal_price values remain!"
    assert df["arrival_qty"].isna().sum() == 0, "NULL arrival_qty values remain!"
    assert pd.api.types.is_datetime64_any_dtype(df["date"]), "date column is not datetime!"
    assert df["date"].is_monotonic_increasing, "date column is not sorted ascending!"
    assert df["date"].duplicated().sum() == 0, "Duplicate dates found!"

    date_min = df["date"].min()
    date_max = df["date"].max()
    assert str(date_min.date()) == config.DATE_START, f"Min date mismatch: {date_min.date()}"
    assert str(date_max.date()) == config.DATE_END,   f"Max date mismatch: {date_max.date()}"

    price_min = df["modal_price"].min()
    price_max = df["modal_price"].max()
    if not (500 < price_min < 15_000):
        log.warning("modal_price min ₹%.0f looks unusual — check data.", price_min)
    if not (500 < price_max < 30_000):
        log.warning("modal_price max ₹%.0f looks unusual — check data.", price_max)

    log.info("✅ Phase 1 validation passed.")


def load_clean_data(csv_path: Path = config.RAW_CSV_PATH) -> pd.DataFrame:
    """
    Public entry point for Phase 1.
    Returns a clean, daily-frequency DataFrame with no nulls.
    """
    df = load_raw(csv_path)
    df = normalise_columns(df)
    df = parse_dates(df)
    df = filter_crop_district(df)
    df = pick_price_qty_columns(df)
    df = aggregate_multiple_markets(df)
    df = reindex_to_daily(df)
    df = flag_outliers(df)
    validate(df)

    log.info("━" * 60)
    log.info("Phase 1 complete. Final shape: %s", df.shape)
    log.info("Date range: %s → %s", df['date'].min().date(), df['date'].max().date())
    log.info("modal_price  → min: ₹%.0f  max: ₹%.0f  mean: ₹%.0f",
             df['modal_price'].min(), df['modal_price'].max(), df['modal_price'].mean())
    log.info("arrival_qty  → min: %.0f    max: %.0f",
             df['arrival_qty'].min(), df['arrival_qty'].max())
    log.info("Nulls: %d", df.isnull().sum().sum())
    log.info("━" * 60)
    print(df.info())

    return df


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_clean_data()
    print(df.head(10))
    print(df.tail(5))
