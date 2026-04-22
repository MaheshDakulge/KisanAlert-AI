# -*- coding: utf-8 -*-
"""
Synthetic Data Generator for KisanAlert
Generates a realistic Soybean Nanded CSV for 2019–2024 so you can
run and test the full pipeline before obtaining real Agmarknet data.

Usage:
    python generate_sample_data.py

Saves to: data/raw/soybean_nanded.csv
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config


def generate(seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    dates = pd.date_range(start=config.DATE_START, end=config.DATE_END, freq="D")

    n = len(dates)
    price = np.zeros(n)
    arrivals = np.zeros(n)

    # Base price around ₹4,500 with seasonal and trend effects
    base = 4500.0
    for i, d in enumerate(dates):
        month = d.month
        year  = d.year

        # Seasonal pattern: Oct–Nov lowest (harvest surplus), Apr–Jun highest
        seasonal = -400 * np.cos(2 * np.pi * (month - 4) / 12)

        # Multi-year trend: crashed in 2021, recovered 2022–2023
        if year == 2020:
            trend = -200
        elif year == 2021:
            trend = -600
        elif year == 2022:
            trend = 300
        elif year == 2023:
            trend = 500
        elif year == 2024:
            trend = 200
        else:
            trend = 0

        # Random walk component
        noise = np.random.normal(0, 60) if i == 0 else np.random.normal(0, 60)
        price[i] = max(2000, base + seasonal + trend + noise)

        # Occasional crash injection in Oct–Nov to create labels
        if month in [10, 11] and year in [2021, 2022]:
            price[i] *= np.random.choice([0.80, 0.85, 0.90, 1.0], p=[0.15, 0.10, 0.10, 0.65])

    # Smooth price slightly
    price = pd.Series(price).rolling(3, min_periods=1).mean().values

    # Arrivals: high Oct–Dec (harvest), low Jan–Mar, zero on Sundays
    for i, d in enumerate(dates):
        month = d.month
        dow   = d.dayofweek  # 6 = Sunday

        if dow == 6:  # market closed on Sundays
            arrivals[i] = 0
        else:
            base_arr = 5000 + 3000 * np.sin(2 * np.pi * (month - 10) / 12 + np.pi)
            arrivals[i] = max(0, base_arr + np.random.normal(0, 800))

    # Only keep weekday trading days in the CSV (real data has gaps)
    trading_mask = pd.Series(dates).dt.dayofweek != 6  # exclude Sundays
    trading_dates = dates[trading_mask]
    trading_price = price[trading_mask.values]
    trading_arr   = arrivals[trading_mask.values]

    df = pd.DataFrame({
        "date"       : trading_dates.strftime("%d/%m/%Y"),
        "commodity"  : "Soybean",
        "district"   : "Nanded",
        "market"     : "Nanded",
        "arrival_qty": trading_arr.astype(int),
        "min_price"  : (trading_price * 0.95).astype(int),
        "max_price"  : (trading_price * 1.05).astype(int),
        "modal_price": trading_price.astype(int),
    })

    return df


if __name__ == "__main__":
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = generate()
    out = config.RAW_CSV_PATH
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"✅ Synthetic CSV saved to {out}")
    print(f"   Rows: {len(df)}  |  Date range: {df['date'].iloc[0]} → {df['date'].iloc[-1]}")
    print(df.head())
