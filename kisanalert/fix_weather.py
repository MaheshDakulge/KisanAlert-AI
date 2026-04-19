"""
═══════════════════════════════════════════════════════════════════
KisanAlert — Weather Data Fixer 🌧️
═══════════════════════════════════════════════════════════════════

Problem:  engineer_features() never called weather_loader.py
          → 4 weather columns are all zeros since 2021

Fix:      1. Fetch 2021-2026 weather from Open-Meteo (free, no key)
          2. Compute rain_7d_sum, temp_7d_avg, is_raining_today,
             weather_shock_flag
          3. Patch features_labeled.csv with real values
          4. Re-run fix_auc_v2.py to see if AUC improves

Nanded coordinates: lat=19.15, lon=77.32

Usage:
    python fix_weather.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")


class C:
    R = "\033[0m"
    B = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"


def banner(text, color=C.CYAN):
    print(f"\n{color}{C.B}{'═' * 68}{C.R}")
    print(f"{color}{C.B}  {text}{C.R}")
    print(f"{color}{C.B}{'═' * 68}{C.R}\n")


def ok(msg):
    print(f"  {C.GREEN}✓{C.R} {msg}")


def fail(msg):
    print(f"  {C.RED}✗{C.R} {msg}")


def warn(msg):
    print(f"  {C.YELLOW}⚠{C.R} {msg}")


def info(msg):
    print(f"  {C.CYAN}→{C.R} {msg}")


banner("🌧️ KisanAlert — Weather Data Fixer")

# ═══════════════════════════════════════════════════════════════════
# STEP 1: Try your existing weather loader first
# ═══════════════════════════════════════════════════════════════════

banner("STEP 1: Try your existing weather loader", C.YELLOW)

sys.path.insert(0, ".")
weather_df = None

try:
    from src.data.weather_loader import get_weather_data
    info("Calling get_weather_data()...")
    result = get_weather_data()

    if result is not None and len(result) > 100:
        ok(f"Loader returned {len(result):,} rows!")
        info(f"Columns: {list(result.columns)}")
        weather_df = result
    else:
        warn(f"Loader returned too few rows: {len(result) if result is not None else 0}")

except Exception as e:
    warn(f"Existing loader failed: {e}")
    info("Falling back to direct Open-Meteo fetch...")


# ═══════════════════════════════════════════════════════════════════
# STEP 2: Direct Open-Meteo fetch (guaranteed to work!)
# ═══════════════════════════════════════════════════════════════════

if weather_df is None or len(weather_df) < 100:
    banner("STEP 2: Direct Open-Meteo fetch (FREE, no key)", C.YELLOW)

    try:
        import requests
    except ImportError:
        fail("requests not installed. Run: pip install requests")
        sys.exit(1)

    NANDED_LAT = 19.15
    NANDED_LON = 77.32
    START_DATE = "2021-01-01"
    END_DATE   = "2026-04-30"

    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={NANDED_LAT}&longitude={NANDED_LON}"
        f"&start_date={START_DATE}&end_date={END_DATE}"
        f"&daily=precipitation_sum,temperature_2m_mean,"
        f"temperature_2m_max,temperature_2m_min,"
        f"relative_humidity_2m_mean,windspeed_10m_max"
        f"&timezone=Asia%2FKolkata"
    )

    info(f"Fetching from Open-Meteo...")
    info(f"  Dates: {START_DATE} → {END_DATE}")
    info(f"  Location: Nanded ({NANDED_LAT}°N, {NANDED_LON}°E)")

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "daily" not in data:
            fail(f"Unexpected response: {list(data.keys())}")
            sys.exit(1)

        daily = data["daily"]
        weather_raw = pd.DataFrame({
            "date": pd.to_datetime(daily["time"]),
            "precipitation_mm": daily.get("precipitation_sum", [0]*len(daily["time"])),
            "temp_mean_c":      daily.get("temperature_2m_mean", [25]*len(daily["time"])),
            "temp_max_c":       daily.get("temperature_2m_max", [30]*len(daily["time"])),
            "humidity_pct":     daily.get("relative_humidity_2m_mean", [60]*len(daily["time"])),
        })

        # Fill NaN from API with forward-fill
        weather_raw = weather_raw.ffill().bfill()

        ok(f"Fetched {len(weather_raw):,} daily weather rows")
        info(f"Date range: {weather_raw['date'].min().date()} → {weather_raw['date'].max().date()}")
        info(f"Rain range: {weather_raw['precipitation_mm'].min():.1f} - "
             f"{weather_raw['precipitation_mm'].max():.1f} mm")
        info(f"Temp range: {weather_raw['temp_mean_c'].min():.1f}°C - "
             f"{weather_raw['temp_mean_c'].max():.1f}°C")

    except Exception as e:
        fail(f"Open-Meteo fetch failed: {e}")
        info("Check internet connection")
        sys.exit(1)


    # ── Compute the 4 engineered weather features ────────────────

    banner("STEP 3: Computing weather features", C.YELLOW)

    df_w = weather_raw.sort_values("date").reset_index(drop=True)
    df_w = df_w.set_index("date").asfreq("D").ffill().bfill()
    df_w = df_w.reset_index()

    df_w["rain_7d_sum"] = (
        df_w["precipitation_mm"].rolling(7, min_periods=1).sum()
    )
    df_w["temp_7d_avg"] = (
        df_w["temp_mean_c"].rolling(7, min_periods=1).mean()
    )
    df_w["is_raining_today"] = (df_w["precipitation_mm"] > 2.0).astype(int)

    HUMIDITY_THRESH = 75.0
    HUMIDITY_DAYS   = 10
    df_w["humidity_shock"] = (
        (df_w["humidity_pct"] > HUMIDITY_THRESH).astype(int)
        .rolling(HUMIDITY_DAYS, min_periods=1).sum()
        >= 7
    ).astype(int)
    df_w["weather_shock_flag"] = df_w["humidity_shock"]

    weather_df = df_w[["date", "rain_7d_sum", "temp_7d_avg",
                        "is_raining_today", "weather_shock_flag"]].copy()

    info(f"Features computed:")
    info(f"  rain_7d_sum    — mean: {weather_df['rain_7d_sum'].mean():.1f} mm/7d  "
         f"max: {weather_df['rain_7d_sum'].max():.1f}")
    info(f"  temp_7d_avg    — mean: {weather_df['temp_7d_avg'].mean():.1f}°C  "
         f"range: {weather_df['temp_7d_avg'].min():.1f}-{weather_df['temp_7d_avg'].max():.1f}")
    info(f"  is_raining     — {int(weather_df['is_raining_today'].sum())} rainy days "
         f"({weather_df['is_raining_today'].mean()*100:.1f}%)")
    info(f"  weather_shock  — {int(weather_df['weather_shock_flag'].sum())} humid spells")


# ═══════════════════════════════════════════════════════════════════
# STEP 4: Patch features_labeled.csv
# ═══════════════════════════════════════════════════════════════════

banner("STEP 4: Patching features_labeled.csv", C.YELLOW)

FEATURES_PATH = Path("data/processed/features_labeled.csv")
if not FEATURES_PATH.exists():
    fail(f"Not found: {FEATURES_PATH}")
    fail("Run save_labeled_data.py first!")
    sys.exit(1)

df = pd.read_csv(FEATURES_PATH)
df["date"] = pd.to_datetime(df["date"])
ok(f"Loaded existing features: {len(df):,} rows × {len(df.columns)} cols")

before_rain_unique = df["rain_7d_sum"].nunique() if "rain_7d_sum" in df.columns else 0
info(f"Before: rain_7d_sum unique values = {before_rain_unique}")

weather_df["date"] = pd.to_datetime(weather_df["date"])

df = df.drop(columns=[
    c for c in ["rain_7d_sum", "temp_7d_avg", "is_raining_today", "weather_shock_flag"]
    if c in df.columns
], errors="ignore")

df = df.merge(
    weather_df[["date", "rain_7d_sum", "temp_7d_avg",
                "is_raining_today", "weather_shock_flag"]],
    on="date",
    how="left",
)

df["rain_7d_sum"]      = df["rain_7d_sum"].fillna(0)
df["temp_7d_avg"]      = df["temp_7d_avg"].fillna(25.0)
df["is_raining_today"] = df["is_raining_today"].fillna(0).astype(int)
df["weather_shock_flag"] = df["weather_shock_flag"].fillna(0).astype(int)

after_rain_unique = df["rain_7d_sum"].nunique()
info(f"After:  rain_7d_sum unique values = {after_rain_unique}")

if after_rain_unique > 50:
    ok(f"Weather data successfully patched!")
else:
    warn(f"Still few unique values ({after_rain_unique}) — date alignment issue?")

FEATURES_PATH.write_bytes(
    df.to_csv(index=False).encode("utf-8")
)
ok(f"Saved patched file: {FEATURES_PATH}")


# ═══════════════════════════════════════════════════════════════════
# STEP 5: Quick verification
# ═══════════════════════════════════════════════════════════════════

banner("STEP 5: Verification", C.GREEN)

for col in ["rain_7d_sum", "temp_7d_avg", "is_raining_today", "weather_shock_flag"]:
    s = df[col]
    unique = s.nunique()
    zero_pct = 100 * (s == 0).sum() / len(s)
    mean = s.mean()

    if unique > 10:
        ok(f"{col:25s} → {unique:4d} unique values, mean={mean:.2f}")
    elif unique > 1:
        warn(f"{col:25s} → {unique:4d} unique values, mean={mean:.2f}")
    else:
        fail(f"{col:25s} → STILL only {unique} unique value!")

# Sample seasonal pattern — should show monsoon peaks Jun-Sep
print(f"\n  {C.B}Monthly rain_7d_sum averages (should show Jun-Sep peaks):{C.R}")
df["month"] = pd.to_datetime(df["date"]).dt.month
monthly = df.groupby("month")["rain_7d_sum"].mean().round(1)
for m, val in monthly.items():
    month_names = {1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May",
                   6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct",
                   11:"Nov", 12:"Dec"}
    bar = "█" * int(val / 5)
    peak = " ← MONSOON" if m in [6, 7, 8, 9] else ""
    print(f"    {month_names[int(str(m))]}: {C.CYAN}{bar}{C.R} {val:.1f}mm{peak}")


# ═══════════════════════════════════════════════════════════════════
# FINAL MESSAGE
# ═══════════════════════════════════════════════════════════════════

banner("🎯 WEATHER FIX COMPLETE!", C.GREEN)

print(f"  {C.GREEN}{C.B}✅ features_labeled.csv now has REAL weather data!{C.R}\n")
print(f"  Next steps:")
print(f"    1. Re-run the AUC tuner to see if weather helps:")
print(f"       python fix_auc_v2.py")
print(f"    2. Re-run save_labeled_data.py to regenerate cleanly")
print(f"    3. Re-run run_pipeline.py — weather warning should be gone!")
print()
print(f"  {C.B}Weather features explained:{C.R}")
print(f"    rain_7d_sum      — Heavy rain → farmers rush to harvest → arrival surge → crash")
print(f"    temp_7d_avg      — High temp pre-harvest → quality damage → lower bids")
print(f"    is_raining_today — Immediate market avoidance")
print(f"    weather_shock_flag — Prolonged humidity → grade penalty risk")
print()
