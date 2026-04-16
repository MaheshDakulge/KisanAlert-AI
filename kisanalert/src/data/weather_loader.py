# -*- coding: utf-8 -*-
"""
Phase 8: Open-Meteo Integration
Fetches historical and live/forecast weather data for Nanded.
"""

import logging
import requests
import pandas as pd
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

def get_coordinates():
    district = config.TARGET_DISTRICT
    return config.DISTRICT_COORDINATES.get(district, config.DISTRICT_COORDINATES["Nanded"])

def fetch_historical_weather(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetches historical weather data from open-meteo archive API."""
    coords = get_coordinates()
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,temperature_2m_max",
        "timezone": "Asia/Kolkata"
    }
    log.info("Fetching historical weather from %s to %s...", start_date, end_date)
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        log.error("Failed to fetch historical weather: %s", resp.text)
        return pd.DataFrame()
    data = resp.json()["daily"]
    df = pd.DataFrame({
        "date": data["time"],
        "rain_mm": data["precipitation_sum"],
        "temp_max_c": data["temperature_2m_max"]
    })
    # Fill N/As that Open-Meteo returns sometimes
    df = df.fillna(0.0) 
    return df

def fetch_live_weather() -> pd.DataFrame:
    """Fetches recent and forecast weather data from open-meteo forecast API."""
    coords = get_coordinates()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "past_days": 14,
        "forecast_days": 7,
        "daily": "precipitation_sum,temperature_2m_max",
        "timezone": "Asia/Kolkata"
    }
    log.info("Fetching live weather (past 14 days + forecast)...")
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        log.error("Failed to fetch live weather: %s", resp.text)
        return pd.DataFrame()
    data = resp.json()["daily"]
    df = pd.DataFrame({
        "date": data["time"],
        "rain_mm": data["precipitation_sum"],
        "temp_max_c": data["temperature_2m_max"]
    })
    df = df.fillna(0.0)
    return df

def get_weather_data() -> pd.DataFrame:
    """
    Combined loader that gets archive + live weather and merges them
    so there are no gaps.
    """
    # historical API is severely lagging by 5-7 days
    # So we fetch historical up to 10 days ago just to be safe
    today = datetime.now()
    hist_end = today - timedelta(days=10)
    
    # 2021 is when our price data starts
    df_hist = fetch_historical_weather("2021-01-01", hist_end.strftime("%Y-%m-%d"))
    df_live = fetch_live_weather()
    
    if df_hist.empty and df_live.empty:
        log.warning("Weather fetch failed completely. Returning empty df.")
        return pd.DataFrame(columns=["date", "rain_mm", "temp_max_c"])
        
    df_comb = pd.concat([df_hist, df_live], ignore_index=True)
    df_comb["date"] = pd.to_datetime(df_comb["date"])
    
    # Keep the most recent data if there are overlapping dates
    df_comb = df_comb.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
    
    log.info("Loaded weather data: %d rows from %s to %s", 
             len(df_comb), df_comb["date"].min().date(), df_comb["date"].max().date())
             
    return df_comb
