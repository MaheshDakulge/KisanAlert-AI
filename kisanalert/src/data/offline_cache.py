# -*- coding: utf-8 -*-
"""
KisanAlert Offline Cache — JSON-based local cache for latest alert results.

Why: API should never block on cold start or Supabase downtime.
How: After every pipeline run, results are saved to data/cache/latest_alerts.json.
     API reads from cache first → falls back to Supabase only if cache is missing/stale.

Cache structure (per crop):
{
  "Soybean": {
    "ts": 1714000000.0,          # Unix timestamp of last save
    "saved_at_ist": "17:05 IST", # Human-readable (for the /api/v1/status endpoint)
    "data": { ...alert dict... }
  }
}
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ── Cache file location ────────────────────────────────────────────────────────
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"
_CACHE_FILE = _CACHE_DIR / "latest_alerts.json"

# Cache is considered stale after 6 hours (so demo always shows fresh data
# after a 5 PM pipeline run, and stays usable until the next run)
_CACHE_MAX_AGE_SECONDS = 6 * 3600


def _load_all() -> dict:
    """Load the entire cache file. Returns empty dict if missing or corrupt."""
    try:
        if _CACHE_FILE.exists():
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning("Offline cache read failed (%s) — returning empty", e)
    return {}


def _save_all(cache: dict) -> None:
    """Write the full cache dict to disk atomically."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _CACHE_FILE.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, default=str)
        tmp.replace(_CACHE_FILE)
        log.info("Offline cache saved → %s", _CACHE_FILE)
    except Exception as e:
        log.error("Offline cache write failed: %s", e)


def save_cache(crop: str, data: dict) -> None:
    """
    Save the latest alert result for a crop.
    Called by smart_scheduler after every successful pipeline run.
    """
    import time
    now = datetime.now()
    ist_str = now.strftime("%H:%M IST")

    cache = _load_all()
    cache[crop] = {
        "ts": time.time(),
        "saved_at_ist": ist_str,
        "saved_at_iso": now.isoformat(),
        "data": data,
    }
    _save_all(cache)
    log.info("[OfflineCache] Saved %s alert (level=%s, price=%.0f)",
             crop, data.get("alert_level", "?"), data.get("price", 0))


def load_cache(crop: str, max_age_seconds: int = _CACHE_MAX_AGE_SECONDS) -> Optional[dict]:
    """
    Load the latest cached alert for a crop.
    Returns None if cache is missing or older than max_age_seconds.
    """
    import time
    cache = _load_all()
    entry = cache.get(crop)
    if not entry:
        log.info("[OfflineCache] No cache entry for %s", crop)
        return None

    age = time.time() - entry.get("ts", 0)
    if age > max_age_seconds:
        log.info("[OfflineCache] Cache stale for %s (age=%.0fh)", crop, age / 3600)
        return None

    log.info("[OfflineCache] Serving %s from cache (saved=%s, age=%.0fmin)",
             crop, entry.get("saved_at_ist", "?"), age / 60)
    return entry["data"]


def get_cache_status() -> dict:
    """
    Returns a summary of cache freshness for all crops.
    Used by /api/v1/status endpoint.
    """
    import time
    cache = _load_all()
    status = {}
    for crop, entry in cache.items():
        age = time.time() - entry.get("ts", 0)
        status[crop] = {
            "saved_at": entry.get("saved_at_ist", "Unknown"),
            "age_minutes": round(age / 60),
            "is_fresh": age < _CACHE_MAX_AGE_SECONDS,
            "alert_level": entry.get("data", {}).get("alert_level", "?"),
            "price": entry.get("data", {}).get("price", 0),
        }
    return status


def invalidate_cache(crop: Optional[str] = None) -> None:
    """Clear cache for one crop or all crops. Used for testing."""
    if crop is None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _save_all({})
        log.info("[OfflineCache] All cache cleared")
    else:
        cache = _load_all()
        if crop in cache:
            del cache[crop]
            _save_all(cache)
            log.info("[OfflineCache] Cache cleared for %s", crop)
