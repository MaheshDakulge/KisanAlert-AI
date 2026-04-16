# -*- coding: utf-8 -*-
"""
Phase 11: Offline SQLite Cache
Maintains a local sliding window of the last 48 hours of predictions.
Used by the local dashboard / mobile app when network APIs (Supabase) are unavailable.
"""

import sqlite3
import json
import logging
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

log = logging.getLogger(__name__)

CACHE_DB_PATH = config.CACHE_DIR / "offline_cache.db"

def init_db():
    """Initializes the SQLite database and creates the daily_alerts table if it doesn't exist."""
    try:
        # Create CACHE_DIR if it doesn't exist
        CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        
        # We store the raw JSON payload to maintain flexibility
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            commodity TEXT NOT NULL,
            district TEXT NOT NULL,
            alert_level TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, commodity, district)
        )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("Failed to initialize SQLite cache: %s", e)

def save_alert_to_cache(alert: dict):
    """Saves the generated alert dictionary to the local SQLite DB."""
    init_db()
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        
        date = alert.get("date")
        commodity = alert.get("commodity")
        district = alert.get("district")
        level = alert.get("alert_level")
        payload = json.dumps(alert, ensure_ascii=False)
        
        # Insert or replace (update) the payload for the day
        cursor.execute('''
        INSERT OR REPLACE INTO daily_alerts (date, commodity, district, alert_level, payload_json)
        VALUES (?, ?, ?, ?, ?)
        ''', (date, commodity, district, level, payload))
        
        conn.commit()
        conn.close()
        log.info("💾 Saved alert to SQLite offline cache for %s (%s)", date, commodity)
    except Exception as e:
        log.error("Failed to save alert to SQLite cache: %s", e)

def get_latest_cached_alert(commodity: str, district: str) -> dict:
    """Retrieves the most recent alert from the local SQLite DB."""
    try:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT payload_json FROM daily_alerts 
        WHERE commodity = ? AND district = ?
        ORDER BY date DESC LIMIT 1
        ''', (commodity, district))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    except Exception as e:
        log.error("Failed to retrieve cached alert: %s", e)
        return None

if __name__ == "__main__":
    init_db()
    log.info("SQLite offline cache initialized at %s", CACHE_DB_PATH)
