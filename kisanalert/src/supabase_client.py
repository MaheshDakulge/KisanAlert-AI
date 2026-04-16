# -*- coding: utf-8 -*-
"""
Supabase client for KisanAlert.
Handles pushing daily alerts and predictions to the cloud backend.
"""

import sys
import logging
from pathlib import Path
from supabase import create_client, Client

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config

log = logging.getLogger(__name__)

def get_supabase() -> Client:
    """Returns an authenticated Supabase client."""
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        log.error("Supabase credentials not found in environment!")
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY")
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

def push_daily_alert(date: str, price: float, crash_score: float, alert_level: str, message: str) -> None:
    """Push the daily alert to the daily_alerts table."""
    supabase = get_supabase()
    data = {
        "date": date,
        "commodity": config.TARGET_COMMODITY,
        "district": config.TARGET_DISTRICT,
        "price": price,
        "crash_score": crash_score,
        "alert_level": alert_level,
        "message": message
    }
    try:
        response = supabase.table("daily_alerts").upsert(data, on_conflict="date,commodity,district").execute()
        log.info("✅ Successfully pushed alert to Supabase for %s", date)
    except Exception as e:
        log.error("❌ Failed to push alert to Supabase: %s", e)

def log_pipeline_run(status: str, logs: str = None) -> None:
    """Log the pipeline execution status."""
    supabase = get_supabase()
    data = {
        "status": status,
        "logs": logs
    }
    try:
        supabase.table("pipeline_runs").insert(data).execute()
    except Exception as e:
        log.error("Failed to log pipeline run to Supabase: %s", e)
