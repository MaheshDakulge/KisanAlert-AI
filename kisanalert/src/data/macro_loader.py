# -*- coding: utf-8 -*-
"""
Phase 10 & ML Features: Macro Data Loader
Fetches USD/INR and CBOT Soybean Futures for the entire history or just today.
Provides NAFED & DGFT scraper stubs for the Rule Engine.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None

log = logging.getLogger(__name__)

def fetch_macro_data(start_date: str | datetime = None, end_date: str | datetime = None) -> pd.DataFrame:
    """
    Fetches USD/INR and ZS=F (CBOT Soybean) and returns a DataFrame.
    If dates are omitted, fetches the last 1 year (used during daily inference).
    If dates are provided, fetches that historical range (used during model training).
    
    Fields: date, usd_inr, cbot_close, cbot_weekly_change
    """
    if yf is None:
        log.error("yfinance is not installed. Macro data will be empty.")
        return pd.DataFrame(columns=["date", "usd_inr", "cbot_close", "cbot_weekly_change"])
        
    log.info("Fetching macro indicators from Yahoo Finance (CBOT & USD/INR)...")
    
    if end_date is None:
        end_dt = datetime.now()
    elif isinstance(end_date, str):
        end_dt = pd.to_datetime(end_date)
    else:
        end_dt = end_date

    if start_date is None:
        start_dt = end_dt - timedelta(days=365) # Last 1 year for rolling calcs
    elif isinstance(start_date, str):
        start_dt = pd.to_datetime(start_date)
    else:
        start_dt = start_date

    # Add a 30 day padding to the start date so weekly rolling calcs work at the exact start_date
    fetch_start = start_dt - timedelta(days=30)
    
    # ZS=F is CBOT Soybean Futures
    # INR=X is USD/INR Exchange Rate
    tickers = ["ZS=F", "INR=X"]
    
    try:
        # Download historical data
        data = yf.download(tickers, start=fetch_start.strftime("%Y-%m-%d"), 
                           end=end_dt.strftime("%Y-%m-%d"), progress=False)
                           
        # Flatten multi-index
        df = data['Close'].reset_index()
        df = df.rename(columns={"Date": "date", "INR=X": "usd_inr", "ZS=F": "cbot_close"})
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        
        # Forward fill weekends/holidays so we have data on all calendar days
        # First ensure full daily index between min and max date
        full_idx = pd.date_range(start=df['date'].min(), end=df['date'].max(), freq='D', name='date')
        df = df.set_index('date').reindex(full_idx).reset_index()
        df = df.ffill()
        
        # Calculate weekly change for CBOT (7 calendar days)
        df["cbot_weekly_change"] = df["cbot_close"].pct_change(periods=7).fillna(0.0)
        
        # Trim off the 30-day padding and return
        df = df[df['date'] >= start_dt].reset_index(drop=True)
        return df
        
    except Exception as e:
        log.error("Failed to fetch macro data: %s", e)
        return pd.DataFrame(columns=["date", "usd_inr", "cbot_close", "cbot_weekly_change"])

import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

def fetch_dgft_export_ban_flag(commodity: str) -> float:
    """
    Scrapes the Directorate General of Foreign Trade (DGFT) news/notifications portal
    for active export bans on the given commodity.
    Returns 1.0 if an export ban is active or recently announced, else 0.0.
    """
    log.info(f"Scraping DGFT portal for export restrictions on {commodity}...")
    try:
        # Check an aggregated ag-commodity news source or generic DGFT keyword search
        # Using a reliable search endpoint or representative site
        url = "https://dgft.gov.in/CP/?opt=notification"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text().lower()
            
            # Keywords indicating an export ban or restriction
            ban_keywords = ["export ban", "prohibited", "export restricted", "halt exports"]
            target = commodity.lower()
            
            # If the commodity and ban keywords appear in the recent notifications
            if target in text_content and any(kw in text_content for kw in ban_keywords):
                log.warning(f"🚨 DGFT Export Ban detected for {commodity}!")
                return 1.0
        return 0.0
    except Exception as e:
        log.error("DGFT scraper failed: %s", e)
        return 0.0

def fetch_nafed_release_flag(commodity: str) -> float:
    """
    Scrapes NAFED / FCI tender releases. 
    Returns 1.0 if the government is releasing buffer stocks into the open market, else 0.0.
    """
    log.info(f"Scraping NAFED active tenders for {commodity} buffer release...")
    try:
        url = "https://www.nafed-india.com/tenders"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text().lower()
            
            # Keywords indicating government buffer stock offloading
            release_keywords = ["disposal", "sale of", "buffer release", "offloading", "open market sale"]
            target = commodity.lower()
            
            if target in text_content and any(kw in text_content for kw in release_keywords):
                log.warning(f"🚨 NAFED Buffer Release detected for {commodity}!")
                return 1.0
        return 0.0
    except Exception as e:
        log.error("NAFED scraper failed: %s", e)
        return 0.0

if __name__ == "__main__":
    b_df = fetch_macro_data(start_date="2021-01-01", end_date="2021-02-01")
    print(b_df.head(10))
    print("DGFT Ban Flag:", fetch_dgft_export_ban_flag("Soybean"))
