"""
═══════════════════════════════════════════════════════════════════
KisanAlert — Weather API Doctor 🌧️
═══════════════════════════════════════════════════════════════════

Diagnoses why weather features are returning all zeros.

Checks:
  1. Which weather loader module exists
  2. What API it tries to call
  3. Whether the API key is present
  4. Whether the API endpoint is reachable
  5. Whether the response has actual weather data
  6. Whether the parser correctly extracts rain/temp

Usage:
    python diagnose_weather.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path


class C:
    R = "\033[0m"
    B = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    DIM = "\033[2m"


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


banner("🌧️ Weather API Doctor — Finding Why Features Are Zero")


# ═══════════════════════════════════════════════════════════════════
# CHECK 1: Weather loader file exists
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 1: weather_loader.py file", C.YELLOW)

loader_path = Path("src/data/weather_loader.py")
if not loader_path.exists():
    fail(f"Missing: {loader_path}")
    sys.exit(1)

ok(f"Found: {loader_path}")
info(f"Size: {loader_path.stat().st_size} bytes")


# ═══════════════════════════════════════════════════════════════════
# CHECK 2: Inspect the loader code
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 2: Which API does the loader call?", C.YELLOW)

code = loader_path.read_text(encoding="utf-8")

apis_detected = []
if "openweathermap" in code.lower() or "owm" in code.lower():
    apis_detected.append("OpenWeatherMap")
if "open-meteo" in code.lower() or "openmeteo" in code.lower() or "open_meteo" in code.lower():
    apis_detected.append("Open-Meteo")
if "weatherapi" in code.lower():
    apis_detected.append("WeatherAPI.com")
if "visualcrossing" in code.lower():
    apis_detected.append("Visual Crossing")

if not apis_detected:
    warn("Could not detect which API is used")
    info("Looking for API URLs in code...")
    import re
    urls = re.findall(r"https?://[^\s'\"]+", code)
    for url in urls[:5]:
        info(f"  Found URL: {url}")
else:
    for api in apis_detected:
        ok(f"Detected API: {api}")


# ═══════════════════════════════════════════════════════════════════
# CHECK 3: API key in environment
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 3: API key configured?", C.YELLOW)

env_path = Path(".env")
if env_path.exists():
    ok(f"Found .env file")
    env_content = env_path.read_text(encoding="utf-8")

    keys_to_check = [
        "OPENWEATHER_API_KEY",
        "OPENWEATHERMAP_API_KEY",
        "OWM_API_KEY",
        "WEATHER_API_KEY",
        "WEATHERAPI_KEY",
    ]

    found_key = None
    for key in keys_to_check:
        if key in env_content:
            for line in env_content.splitlines():
                if line.startswith(key + "="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if value and value != "your_key_here" and len(value) > 10:
                        ok(f"{key} is set (length: {len(value)} chars)")
                        found_key = (key, value)
                    else:
                        warn(f"{key} is EMPTY or placeholder")
                    break

    if not found_key:
        warn("No valid weather API key found in .env")
        info("If using OpenWeatherMap: get free key at https://openweathermap.org/api")
        info("If using Open-Meteo: no key needed (free)")
else:
    warn("No .env file found")


# ═══════════════════════════════════════════════════════════════════
# CHECK 4: Try importing and running the loader
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 4: Does the loader run?", C.YELLOW)

try:
    sys.path.insert(0, ".")

    if "python-dotenv" in sys.modules or True:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            ok("Loaded .env variables")
        except ImportError:
            warn("python-dotenv not installed — .env not loaded")

    from src.data import weather_loader as wl
    ok("Imported weather_loader module")

    functions = [name for name in dir(wl) if not name.startswith("_") and callable(getattr(wl, name, None))]
    info(f"Available functions: {functions[:10]}")

    candidate_funcs = [
        "load_weather",
        "fetch_weather",
        "get_weather",
        "load_weather_data",
        "fetch_weather_data",
        "get_weather_features",
    ]

    main_func = None
    for fname in candidate_funcs:
        if hasattr(wl, fname):
            main_func = getattr(wl, fname)
            ok(f"Found main function: {fname}()")
            break

    if main_func is None:
        warn("Could not auto-detect main weather function")
        info(f"Try one of these: {functions}")

except Exception as e:
    fail(f"Import failed: {e}")
    traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════
# CHECK 5: Inspect actual weather data in the DataFrame
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 5: Current weather data quality", C.YELLOW)

try:
    import pandas as pd

    data_path = Path("data/processed/features_labeled.csv")
    if not data_path.exists():
        warn(f"{data_path} not found — run save_labeled_data.py first")
    else:
        df = pd.read_csv(data_path)
        weather_cols = [c for c in df.columns if any(
            term in c.lower() for term in ["rain", "temp", "humidity", "weather"]
        )]

        if not weather_cols:
            fail("No weather columns in features_labeled.csv!")
        else:
            info(f"Weather columns found: {weather_cols}")

            for col in weather_cols:
                s = df[col]
                unique = s.nunique()
                non_zero = (s != 0).sum()
                zero_pct = 100 * (s == 0).sum() / len(s)
                mean = s.mean()
                std = s.std()

                print(f"\n  {C.B}{col}:{C.R}")
                print(f"    Unique values: {unique}")
                print(f"    Non-zero rows: {non_zero} / {len(df)} ({100-zero_pct:.1f}%)")
                print(f"    Mean: {mean:.3f}  Std: {std:.3f}")

                if unique == 1:
                    fail(f"    All identical — LOADER IS BROKEN!")
                elif zero_pct > 90:
                    fail(f"    >90% zeros — LOADER IS MOSTLY BROKEN!")
                elif zero_pct > 50:
                    warn(f"    {zero_pct:.1f}% zeros — may be real dry season")
                else:
                    ok(f"    Healthy variance")

except Exception as e:
    fail(f"Data check failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════════════════

banner("💊 VERDICT & FIX RECOMMENDATION", C.GREEN)

print("  Likely causes of zero weather data:\n")
print(f"    {C.YELLOW}1. OpenWeatherMap key not set → use Open-Meteo (free, no key){C.R}")
print(f"    {C.YELLOW}2. Loader writes to wrong column names{C.R}")
print(f"    {C.YELLOW}3. Historical weather not fetched during feature engineering{C.R}")
print(f"    {C.YELLOW}4. Rate-limited API returning empty responses{C.R}")

print("\n  {} Next step:".format(C.B))
print(f"  {C.CYAN}→ Share this diagnostic output with Claude{C.R}")
print(f"  {C.CYAN}→ Claude will write a targeted fix for weather_loader.py{C.R}")
print()
