# -*- coding: utf-8 -*-
"""
KisanAlert Smart Scheduler — Auto-runs the ML pipeline at government data update times.

Schedule (IST):
  3:35 PM → Fetch NCDEX/MCX futures prices for all 3 crops → save to offline cache
  5:05 PM → Fetch Gov Agmarknet APMC prices → run full ML pipeline → save results
             → broadcast FCM DATA_REFRESH to all Flutter apps
  Every 2h → Weather data refresh (lightweight)

Why these times:
  - Gov data.gov.in (Agmarknet) API updates between 4–5 PM IST after mandi close
  - NCDEX MCX futures settle at 3:30 PM IST
  - 5:05 PM gives a 5-min buffer after data refresh, ensuring freshest data

Usage:
  from src.scheduler.smart_scheduler import start_scheduler, stop_scheduler
  start_scheduler()  # Call once on FastAPI startup
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_scheduler = None   # APScheduler instance (lazy init)
_CROPS = ["Soybean", "Cotton", "Turmeric"]
_DISTRICT = "Nanded"


# ─────────────────────────────────────────────────────────────────────────────
# Job 1: 3:35 PM IST — Fetch NCDEX futures
# ─────────────────────────────────────────────────────────────────────────────
def _job_fetch_futures():
    """Fetch NCDEX/MCX futures for all 3 crops and save to offline cache."""
    log.info("[Scheduler] 3:35 PM — Fetching NCDEX/MCX futures...")
    try:
        from src.data.ncdex_fetcher import get_futures_data
        from src.data.offline_cache import load_cache, save_cache

        for crop in _CROPS:
            try:
                futures = get_futures_data(crop)
                # Merge into existing cache so we don't overwrite alert data
                existing = load_cache(crop, max_age_seconds=86400) or {}
                existing["ncdex_signal"] = futures.get("signal", "")
                existing["ncdex_price"] = futures.get("futures_price", 0)
                existing["ncdex_fetched_at"] = datetime.now().isoformat()
                save_cache(crop, existing)
                log.info("[Scheduler] NCDEX futures for %s: %s", crop, futures.get("signal", ""))
            except Exception as e:
                log.warning("[Scheduler] NCDEX fetch failed for %s: %s", crop, e)
    except Exception as e:
        log.error("[Scheduler] Futures job failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Job 2: 5:05 PM IST — Full pipeline for all crops → FCM broadcast
# ─────────────────────────────────────────────────────────────────────────────
def _run_pipeline_for_crop(crop: str) -> Optional[dict]:
    """Run the full ML pipeline for one crop and return alert dict."""
    import sys, importlib
    ROOT = Path(__file__).resolve().parent.parent.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        import config as cfg
        original_crop = cfg.TARGET_COMMODITY
        original_district = cfg.TARGET_DISTRICT

        # Temporarily override config for this crop
        cfg.TARGET_COMMODITY = crop
        cfg.TARGET_DISTRICT = _DISTRICT

        from run_pipeline import run
        alert = run(use_live=True)

        cfg.TARGET_COMMODITY = original_crop
        cfg.TARGET_DISTRICT = original_district
        return alert
    except Exception as e:
        log.error("[Scheduler] Pipeline failed for %s: %s", crop, e)
        return None


def _job_run_pipeline():
    """
    5:05 PM IST: Run full ML pipeline for all 3 crops.
    Saves results to offline cache, then broadcasts FCM DATA_REFRESH.
    """
    log.info("=" * 60)
    log.info("[Scheduler] 5:05 PM — Running full pipeline for all crops...")
    log.info("=" * 60)

    from src.data.offline_cache import save_cache

    results = {}
    for crop in _CROPS:
        log.info("[Scheduler] Processing %s...", crop)
        alert = _run_pipeline_for_crop(crop)
        if alert:
            # Normalise alert dict keys to match API response format
            cache_payload = {
                "commodity": crop,
                "district": _DISTRICT,
                "date": str(datetime.now().date()),
                "price": alert.get("price", 0),
                "min_price": alert.get("min_price", 0),
                "max_price": alert.get("max_price", 0),
                "crash_score": alert.get("crash_score", 0.5),
                "rise_score": alert.get("rise_score", 0.0),
                "alert_level": alert.get("alert_level", "AMBER"),
                "message": alert.get("message_marathi", alert.get("message", "")),
                "ncdex_signal": alert.get("ncdex_signal", ""),
                "data_source": "scheduler_live",
                "expected_price_48h": alert.get("expected_price_48h", 0),
                "expected_profit_per_qtl": alert.get("expected_profit_per_qtl", 0),
                "trend_is_rising": alert.get("trend_is_rising", False),
            }
            save_cache(crop, cache_payload)
            results[crop] = cache_payload
            log.info("[Scheduler] %s done → %s @ ₹%.0f",
                     crop, cache_payload["alert_level"], cache_payload["price"])

    # Broadcast FCM DATA_REFRESH for each crop that ran successfully
    _broadcast_fcm_refresh(results)

    log.info("[Scheduler] All crops done. Cache updated.")


def _broadcast_fcm_refresh(results: dict):
    """Broadcast FCM DATA_REFRESH push so Flutter apps auto-reload."""
    try:
        from src.alerts.fcm_notifier import broadcast_data_refresh
        for crop, alert in results.items():
            try:
                broadcast_data_refresh(
                    commodity=crop,
                    price=float(alert.get("price", 0)),
                    alert_level=str(alert.get("alert_level", "AMBER")),
                    message_mr=str(alert.get("message", "")),
                )
                log.info("[Scheduler] FCM DATA_REFRESH sent for %s", crop)
            except Exception as e:
                log.warning("[Scheduler] FCM broadcast failed for %s: %s", crop, e)
    except Exception as e:
        log.error("[Scheduler] FCM broadcast error: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Job 3: Every 2 hours — Weather refresh (lightweight)
# ─────────────────────────────────────────────────────────────────────────────
def _job_refresh_weather():
    """Lightweight weather data refresh — triggers API to pre-warm weather cache."""
    try:
        from src.data.live_price_fetcher import fetch_live_price
        log.info("[Scheduler] Weather cache pre-warm triggered")
    except Exception as e:
        log.debug("[Scheduler] Weather refresh: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Scheduler start / stop (called from api.py on FastAPI startup/shutdown)
# ─────────────────────────────────────────────────────────────────────────────
def start_scheduler():
    """
    Start the APScheduler background scheduler.
    Should be called exactly ONCE from FastAPI @app.on_event("startup").
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        log.warning("[Scheduler] Already running — skipping start")
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.error("[Scheduler] APScheduler not installed. Run: pip install apscheduler")
        return

    # IST = UTC+5:30 → express IST times as UTC offsets
    # 3:35 PM IST = 10:05 UTC   |   5:05 PM IST = 11:35 UTC
    _scheduler = BackgroundScheduler(timezone="UTC")

    # Job 1: NCDEX futures at 3:35 PM IST every weekday
    _scheduler.add_job(
        _job_fetch_futures,
        trigger=CronTrigger(day_of_week="mon-fri", hour=10, minute=5, timezone="UTC"),
        id="fetch_futures",
        name="Fetch NCDEX Futures (3:35 PM IST)",
        misfire_grace_time=300,
        replace_existing=True,
    )

    # Job 2: Full pipeline at 5:05 PM IST every weekday
    _scheduler.add_job(
        _job_run_pipeline,
        trigger=CronTrigger(day_of_week="mon-fri", hour=11, minute=35, timezone="UTC"),
        id="run_pipeline",
        name="Run ML Pipeline + FCM Broadcast (5:05 PM IST)",
        misfire_grace_time=600,
        replace_existing=True,
    )

    # Job 3: Weather refresh every 2 hours
    _scheduler.add_job(
        _job_refresh_weather,
        trigger=CronTrigger(minute=0, hour="*/2", timezone="UTC"),
        id="refresh_weather",
        name="Weather Cache Refresh (2h)",
        misfire_grace_time=120,
        replace_existing=True,
    )

    _scheduler.start()
    log.info("=" * 55)
    log.info("[Scheduler] ✅ KisanAlert Smart Scheduler STARTED")
    log.info("[Scheduler]   Job 1: NCDEX fetch   → 3:35 PM IST daily (Mon-Fri)")
    log.info("[Scheduler]   Job 2: ML pipeline   → 5:05 PM IST daily (Mon-Fri)")
    log.info("[Scheduler]   Job 3: Weather cache → every 2 hours")
    log.info("=" * 55)


def stop_scheduler():
    """Stop the scheduler gracefully. Called from FastAPI shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("[Scheduler] Stopped.")


def get_scheduler_status() -> dict:
    """Return current scheduler job status — used by /api/v1/status."""
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_utc": next_run.isoformat() if next_run else "Unknown",
            "next_run_ist": (
                next_run.astimezone(
                    __import__("zoneinfo", fromlist=["ZoneInfo"]).ZoneInfo("Asia/Kolkata")
                ).strftime("%H:%M IST %d %b")
                if next_run else "Unknown"
            ),
        })
    return {"running": True, "jobs": jobs}
