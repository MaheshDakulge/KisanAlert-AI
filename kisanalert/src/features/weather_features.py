# -*- coding: utf-8 -*-
"""
Weather feature engineering.
Takes in the merged dataframe (prices + weather) and computes rolling
shock features (e.g., sudden heavy rainfall, heatwaves).
"""

import pandas as pd
import numpy as np

WEATHER_FEATURES = [
    "rain_7d_sum",
    "temp_7d_avg",
    "is_raining_today",
    "weather_shock_flag"
]

def add_weather_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes basic to advanced weather features."""
    df = df.copy()
    
    # 1. 7-day cumulative rainfall
    df["rain_7d_sum"] = df["rain_mm"].rolling(7, min_periods=1).sum().fillna(0.0)
    
    # 2. 7-day average max temperature
    df["temp_7d_avg"] = df["temp_max_c"].rolling(7, min_periods=1).mean().fillna(df["temp_max_c"].mean())
    df["temp_7d_avg"] = df["temp_7d_avg"].fillna(30.0) # safe fallback
    
    # 3. Binary flag: Did it rain today? (> 2mm)
    df["is_raining_today"] = (df["rain_mm"] > 2.0).astype(int)
    
    # 4. Shock flag: Sudden unseasonal heavy rain (> 20mm in a day) 
    # OR Extreme Heat (> 40C) which destroys yields
    df["weather_shock_flag"] = ((df["rain_mm"] > 20.0) | (df["temp_max_c"] > 40.0)).astype(int)
    
    return df
