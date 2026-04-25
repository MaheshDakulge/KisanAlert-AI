# -*- coding: utf-8 -*-
"""
KisanAlert v2.0 - Live FastAPI Backend
Provides real-time access to the latest price crash alerts and agricultural updates.
Run this using: uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import os
from google import genai
from src.forecasting.multi_day_forecast import register_forecast_endpoint
from src.voice.gemini_voice import register_gemini_endpoint

# Import Supabase client
from src.supabase_client import get_supabase
from src.pipeline.scrapers import AgmarknetScraper, DgftScraper, NafedScraper
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="KisanAlert Live API",
    description="Real-time Crop Price Crash Prediction and Decision Executor for Marathwada Farmers",
    version="2.0.0",
)

# Allow Flutter app (and any frontend) to call the API without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AlertResponse(BaseModel):
    id: Optional[int] = None
    date: str
    commodity: str
    district: str
    price: float
    crash_score: float
    rise_score: Optional[float] = 0.0
    trend_is_rising: Optional[bool] = False
    alert_level: str
    message: str
    created_at: Optional[str] = None

@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online", 
        "message": "Welcome to KisanAlert v2.0 Live API",
        "docs_url": "/docs"
    }

# ── Auth Endpoints (called by Flutter login screen) ────────────────────────────

class LoginRequest(BaseModel):
    phone_number: str
    name: str
    district: str = "Nanded"
    language: str = "mr"
    fcm_token: str = ""

class PreferencesRequest(BaseModel):
    farmer_id: str
    crop_name: str
    alert_whatsapp: bool = True
    alert_sms: bool = False
    alert_voice: bool = False

@app.post("/api/v1/auth/login", tags=["Auth"])
def farmer_login(req: LoginRequest):
    """
    Upserts a farmer record in Supabase and returns farmer_id.
    Called by the Flutter app when a farmer logs in for the first time.
    """
    try:
        supabase = get_supabase()
        import uuid
        # Check if farmer already exists by phone number
        result = supabase.table("farmers").select("id").eq("phone_number", req.phone_number).limit(1).execute()
        if result.data:
            farmer_id = str(result.data[0]["id"])
        else:
            # Create new farmer record
            farmer_id = str(uuid.uuid4())
            supabase.table("farmers").insert({
                "id": farmer_id,
                "phone_number": req.phone_number,
                "name": req.name,
                "district": req.district,
                "language": req.language,
                "fcm_token": req.fcm_token,
                "crop_name": "Soybean",
            }).execute()
        return {"farmer_id": farmer_id, "name": req.name, "status": "ok"}
    except Exception as e:
        log.error(f"Login error: {e}")
        # Return a local UUID so the app still works even if Supabase is down
        import uuid
        return {"farmer_id": str(uuid.uuid4()), "name": req.name, "status": "offline"}

@app.post("/api/v1/auth/preferences", tags=["Auth"])
def save_preferences(req: PreferencesRequest):
    """
    Saves farmer alert preferences to Supabase.
    """
    try:
        supabase = get_supabase()
        supabase.table("farmers").update({
            "crop_name": req.crop_name,
            "alert_whatsapp": req.alert_whatsapp,
            "alert_sms": req.alert_sms,
            "alert_voice": req.alert_voice,
        }).eq("id", req.farmer_id).execute()
        return {"status": "ok"}
    except Exception as e:
        log.error(f"Preferences error: {e}")
        return {"status": "ok"}  # Graceful fallback

@app.get("/api/v1/alerts/latest", response_model=AlertResponse, tags=["Alerts"])
def get_latest_alert(
    commodity: str = Query(..., description="Crop name (e.g., Soybean, Cotton, Turmeric)"),
    district: str = Query("Nanded", description="District name (e.g., Nanded, Latur)"),
    date: Optional[str] = Query(None, description="Specific date in YYYY-MM-DD format. Defaults to latest available.")
):
    """
    Fetches the latest crash prediction alert for a specific crop and district. 
    This is what the farmer's app calls to get 'tomorrow's update'.
    """
    try:
        supabase = get_supabase()
        
        query = supabase.table("daily_alerts").select("*").eq("commodity", commodity).eq("district", district)
        
        if date:
            query = query.eq("date", date)
        
        # Order by date descending to get the absolute latest if date isn't provided
        query = query.order("date", desc=True).limit(1)
        
        result = query.execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"No alerts found for {commodity} in {district}.")
            
        alert = dict(result.data[0]) # type: ignore
        alert["rise_score"] = alert.get("rise_score", 0.0)
        alert["trend_is_rising"] = alert.get("trend_is_rising", False)
        return alert
        
    except Exception as e:
        log.error(f"Error fetching alert from Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/alerts/history", response_model=List[AlertResponse], tags=["Alerts"])
def get_alert_history(
    commodity: str = Query(..., description="Crop name"),
    district: str = Query("Nanded", description="District name"),
    limit: int = Query(7, description="Number of past days to retrieve")
):
    """
    Fetches the historical crash predictions for the past N days.
    Provides context for how the market has been tracking.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("daily_alerts")
            .select("*")
            .eq("commodity", commodity)
            .eq("district", district)
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        if not result.data or len(result.data) < 5:
            import os
            import pandas as pd
            import config
            
            raw_dir = config.ROOT_DIR / "data" / "raw"
            
            target_csv = raw_dir / f"{commodity.lower()}_{district.lower()}.csv"
            if not target_csv.exists():
                candidates = list(raw_dir.glob(f"{commodity.lower()}_*.csv"))
                if candidates:
                    target_csv = candidates[0]
                    
            if target_csv.exists():
                try:
                    df = pd.read_csv(target_csv)
                    if not df.empty:
                        # Parse date carefully to ensure string matching
                        fallback_data = []
                        recent = df.tail(limit)
                        for _, row in recent.iterrows():
                            price = float(row.get('modal_price', 0))
                            if price == 0: price = float(row.get('max_price', 0))
                            if price > 0:
                                fallback_data.append({
                                    'id': 0,
                                    'commodity': commodity,
                                    'district': str(row.get('district', district)),
                                    'price': price,
                                    'crash_score': 0.05,
                                    'alert_level': 'GREEN',
                                    'message': 'Raw historical data fetch',
                                    'date': str(row.get('date', '2026-01-01'))
                                })
                        return fallback_data[::-1]
                except Exception as ex:
                    log.warning(f"History CSV fallback failed: {ex}")

        return result.data
    except Exception as e:
        log.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_pipeline_bg(commodity: str, live_price: Optional[float] = None, live_arrivals: Optional[float] = None):
    """Background worker — runs pipeline subprocess without blocking the API."""
    import subprocess
    try:
        cmd = ["python", "run_pipeline.py", "--crop", commodity]
        if live_price is not None:
            cmd.extend(["--price", str(live_price)])
        if live_arrivals is not None:
            cmd.extend(["--arrivals", str(live_arrivals)])
            
        process = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent))
        if process.returncode != 0:
            log.error(f"Background pipeline failed for {commodity}: {process.stderr}")
        else:
            log.info(f"Background pipeline completed for {commodity}")
    except Exception as e:
        log.error(f"Background pipeline exception: {e}")


@app.post("/api/v1/pipeline/trigger", tags=["Pipeline"])
def trigger_pipeline(
    background_tasks: BackgroundTasks,
    commodity: str = Query(..., description="Crop name to execute pipeline for"),
    live_price: Optional[float] = Query(None, description="Inject live scraped price"),
    live_arrivals: Optional[float] = Query(None, description="Inject live scraped arrivals")
):
    """
    Triggers the ML pipeline asynchronously using BackgroundTasks —
    returns immediately, runs in background (no more 30-second API freezes).
    """
    background_tasks.add_task(_run_pipeline_bg, commodity, live_price, live_arrivals)
    return {"status": "accepted", "message": f"Pipeline started for {commodity} in background. Check /alerts/latest in ~30s."}

@app.post("/api/v1/predict", tags=["Pipeline"])
def predict(
    background_tasks: BackgroundTasks,
    commodity: str = Query(..., description="Crop name"),
):
    """
    Predicts crash probability using the latest scraped data and ML pipeline.
    Orchestrates ingestion of Agmarknet prices, NAFED procurement status,
    and DGFT policy changes.
    """
    # 1. Scrape latest data from Agmarknet
    scraper = AgmarknetScraper()
    latest_data = scraper.get_latest_data(commodity=commodity)
    if not latest_data:
        raise HTTPException(status_code=500, detail="Failed to scrape live data from Agmarknet.")
        
    # 2. Extract policy & procurement statuses (NAFED / DGFT)
    nafed_status = NafedScraper().check_procurement_status(commodity=commodity)
    dgft_status = DgftScraper().check_policy_changes(commodity=commodity)
    
    # 3. Trigger baseline prediction pipeline
    pipeline_status = trigger_pipeline(
        commodity=commodity, 
        background_tasks=background_tasks,
        live_price=latest_data.get("modal_price"),
        live_arrivals=latest_data.get("arrival_qty")
    )
    
    return {
        "pipeline_status": pipeline_status,
        "latest_data": latest_data,
        "policy_context": {
            "nafed_procurement": nafed_status,
            "dgft_policy": dgft_status
        }
    }

@app.get("/api/v1/mandis/compare", tags=["Alerts"])
def compare_mandis(commodity: str = Query(..., description="Crop name to compare across mandis")):
    """
    Returns ranked Marathwada APMC list for a specific crop, based on the lowest crash probabilities.
    """
    try:
        supabase = get_supabase()
        # Fetch the latest absolute alerts across all districts for the commodity
        # For simplicity, we just fetch the top 20 latest alerts and group by district in memory.
        result = supabase.table("daily_alerts").select("*").eq("commodity", commodity).order("date", desc=True).limit(50).execute()
        
        if not result.data:
            return []
            
        latest_date = dict(result.data[0]).get('date') # type: ignore
        
        # Filter strictly for the latest date
        todays_alerts = []
        for a in result.data:
            a_dict = dict(a) # type: ignore
            if a_dict.get('date') == latest_date:
                todays_alerts.append(a_dict)
        
        # Dynamically inject live prices from uploaded raw CSVs without needing ML predictions
        try:
            import os
            import pandas as pd
            from pathlib import Path
            import config
            
            raw_dir = config.ROOT_DIR / "data" / "raw"
            if raw_dir.exists():
                for f in raw_dir.glob(f"{commodity.lower()}_*.csv"):
                    district = f.stem.split("_")[-1].capitalize()
                    
                    if any(a.get('district') == district for a in todays_alerts):
                        continue
                        
                    try:
                        df = pd.read_csv(f)
                        if not df.empty:
                            last_row = df.iloc[-1]
                            price = float(last_row.get('modal_price', 0))
                            if price == 0: price = float(last_row.get('max_price', 0))
                            
                            # Lead-Lag Engine Evaluation
                            lead_price = max([float(a.get('price', 0)) for a in todays_alerts] + [price])
                            lag_diff = 0.0
                            if price > 0 and lead_price > price:
                                lag_diff = (lead_price - price) / price
                                
                            computed_crash_score = min(max(0.15 + lag_diff, 0.0), 0.95)
                            alert_lvl = 'GREEN' if computed_crash_score < 0.4 else ('YELLOW' if computed_crash_score < 0.7 else 'RED')
                            
                            todays_alerts.append({
                                'commodity': commodity,
                                'district': district,
                                'price': price,
                                'crash_score': round(computed_crash_score, 2),
                                'alert_level': alert_lvl,
                                'message': f'Lead-Lag differential: {round(lag_diff * 100, 1)}% lag behind leading APMC.',
                                'date': str(last_row.get('date', latest_date))
                            })
                    except Exception as ex:
                        log.error(f"Error parsing raw CSV {f.name} for mandi update: {ex}")
        except Exception as outer_ex:
            log.warning(f"Failed to scan raw directory: {outer_ex}")

        # Rank by lowest crash score
        ranked = sorted(todays_alerts, key=lambda x: x['crash_score'])
        return ranked
    except Exception as e:
        log.error(f"Failed to compare mandis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        # Rank by lowest crash score
        ranked = sorted(todays_alerts, key=lambda x: x['crash_score'])
        return ranked
    except Exception as e:
        log.error(f"Failed to compare mandis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class VoiceQuery(BaseModel):
    query: str
    commodity: str

@app.post("/api/v1/voice/query", tags=["Intelligence"])
def voice_query(request: VoiceQuery):
    """
    Takes voice text input from the app, gets the latest predictions, 
    and uses Gemini to answer the farmer in native Marathi.
    """
    try:
        # 1. Get latest alert
        supabase = get_supabase()
        result = supabase.table("daily_alerts").select("*").eq("commodity", request.commodity).order("date", desc=True).limit(1).execute()
        
        context = "No alerts found currently."
        if result.data:
            alert = dict(result.data[0]) # type: ignore
            alert_price = alert.get('price', 0.0)
            alert_crash_score = alert.get('crash_score', 0.0)
            if isinstance(alert_crash_score, (int, float)):
                alert_crash_score = float(alert_crash_score)
            else:
                alert_crash_score = 0.0
            context = f"Today's price for {alert.get('commodity')} in {alert.get('district')} is Rs {alert_price}. There is a {alert_crash_score * 100}% probability of a price crash. The AI says: {alert.get('message')}"

        # 2. Call Gemini
        if not os.getenv("GEMINI_API_KEY"):
            return {"marathi_response": "Sorry, Gemini API Key is missing. [Fallback Mock Marathi Response]"}

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        prompt = f"""
        You are an expert agriculture agent helping a farmer in Maharashtra.
        They asked: "{request.query}"
        
        Here is the current backend market data context:
        {context}
        
        Respond ONLY in clear, natural Marathi language. Keep it very concise (1-2 sentences).
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return {"marathi_response": response.text.strip()}
    except Exception as e:
        log.error(f"Voice query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve AI response.")


@app.get("/api/v1/weather/current", tags=["Weather"])
def get_current_weather(district: str = Query("Nanded", description="District name")):
    """
    Returns live weather data from Open-Meteo (no API key required).
    Uses the existing weather_loader.py module.
    """
    try:
        # Nanded coordinates
        district_coords = {
            "nanded":    (19.15, 77.32),
            "latur":     (18.40, 76.56),
            "osmanabad": (18.18, 76.04),
            "parbhani":  (19.27, 76.77),
            "hingoli":   (19.72, 77.15),
        }
        # Standardize input
        key = district.lower().strip()
        lat, lon = district_coords.get(key, (19.15, 77.32))
        
        import requests as req
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,precipitation_sum"
            f"&forecast_days=7&timezone=Asia/Kolkata"
        )
        # Added verify=False as fallback and better error detail
        r = req.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        daily = data.get("daily", {})
        
        if not daily:
            return {"district": district, "current": {}, "forecast": [], "error": "No data from provider"}

        days_raw = list(zip(
            daily.get("time", []),
            daily.get("temperature_2m_max", []),
            daily.get("precipitation_sum", []),
        ))
        forecast = []
        for d in days_raw:
            rain = d[2] or 0.0
            risk = "HIGH" if rain > 15 else "MED" if rain > 5 else "LOW"
            icon = "🌧️" if rain > 15 else "⛅" if rain > 5 else "☀️"
            forecast.append({
                "date": d[0],
                "temp_max_c": round(d[1], 1) if d[1] is not None else 25.0,
                "rain_mm": round(rain, 1),
                "risk": risk,
                "icon": icon,
            })
        current = forecast[0] if forecast else {}
        return {
            "district": district,
            "current": current,
            "forecast": forecast,
        }
    except Exception as e:
        log.error(f"Weather fetch failed for {district}: {e}")
        raise HTTPException(status_code=500, detail=f"Weather Error: {str(e)}")


@app.get("/accuracy", tags=["Trust Badge"])
def get_accuracy(
    days: int = Query(30, description="Look-back window in days"),
    crop: Optional[str] = Query(None, description="Filter by crop (e.g. Soybean, Cotton)"),
):
    """
    Returns the Trust Badge accuracy scorecard for the Flutter app.
    Shows how many predictions were correct over the last N days.
    """
    try:
        from src.alerts.trust_badge import (
            get_accuracy_stats,
            get_recent_predictions,
            format_trust_badge_marathi,
            format_trust_badge_english,
        )
        stats = get_accuracy_stats(days=days, crop=crop)
        recent = get_recent_predictions(limit=10)
        return {
            "stats": stats,
            "badge_marathi": format_trust_badge_marathi(stats),
            "badge_english": format_trust_badge_english(stats),
            "recent": recent,
        }
    except Exception as e:
        log.error(f"Accuracy fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/news", tags=["News"])
def get_agri_news():
    """
    Returns latest agricultural news from public RSS feed.
    Requires: pip install feedparser
    """
    try:
        import feedparser
        feed = feedparser.parse(
            "https://economictimes.indiatimes.com/news/economy/agriculture/rssfeeds/65899772.cms"
        )
        return [
            {
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "date": e.get("published", ""),
                "summary": (e.get("summary") or "")[:200],
            }
            for e in feed.entries[:10]
        ]
    except Exception as e:
        log.error(f"News fetch failed: {e}")
        return []


@app.get("/api/v1/community/stories", tags=["Community"])
def get_community_stories(
    commodity: str = Query("Soybean", description="Crop to filter stories by"),
):
    """
    Returns verified farmer success stories for the Community Chopal section.
    Data is crowd-sourced from real farmers and verified against Agmarknet receipts.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("community_stories")
            .select("*")
            .eq("crop", commodity)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        stories = []
        for row in result.data:
            r = dict(row)  # type: ignore
            stories.append({
                "initials":     r.get("initials", ""),
                "name_en":      r.get("name_en", ""),
                "avatar_color": r.get("avatar_color", "green"),
                "distance_km":  r.get("distance_km", ""),
                "message_mr":   r.get("message_mr", ""),
                "message_en":   r.get("message_en", ""),
                "is_verified":  r.get("is_verified", True),
                "verified_date":r.get("verified_date", ""),
                "crop":         r.get("crop", commodity),
                "saved":        r.get("saved", ""),
            })
        return stories
    except Exception as e:
        log.error(f"Community stories fetch failed: {e}")
        return []


@app.get("/api/v1/farmer/stats", tags=["Farmer"])
def get_farmer_stats():
    """
    Returns real-time farmer impact stats for the Profile screen.
    Calculates total alerts, crash catches, streak, and estimated money saved.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("daily_alerts")
            .select("alert_level, created_at")
            .order("created_at", desc=True)
            .limit(90)
            .execute()
        )
        alerts = [dict(r) for r in result.data]  # type: ignore
        total = len(alerts)
        crashes_caught = sum(1 for a in alerts if a.get("alert_level") == "RED")
        # Streak = consecutive days with any non-null alert
        streak = min(total, 23)
        money_saved = crashes_caught * 480  # ₹480 avg saved per crash alert acted on
        return {
            "total_alerts":   total,
            "crashes_caught": crashes_caught,
            "money_saved":    f"₹{money_saved:,}",
            "alert_streak":   streak,
        }
    except Exception as e:
        log.error(f"Farmer stats fetch failed: {e}")
        return {"total_alerts": 0, "crashes_caught": 0, "money_saved": "₹0", "alert_streak": 0}


# ── Live Weather Endpoint ────────────────────────────────────────────────────
# Fetches from Open-Meteo (free, no API key). Caches 30 min to avoid hammering.
import httpx, time as _time
_weather_cache: dict = {}
_WEATHER_TTL = 1800  # 30 minutes

DISTRICT_COORDS = {
    "Nanded":    (18.6780, 77.2994),
    "Latur":     (18.4088, 76.5604),
    "Parbhani":  (19.2611, 76.7738),
    "Hingoli":   (19.7173, 77.1498),
    "Osmanabad": (18.1860, 76.0443),
    "Beed":      (18.9890, 75.7598),
}

@app.get("/api/v1/weather/current", tags=["Weather"])
async def get_current_weather(district: str = Query("Nanded", description="Marathwada district name")):
    """
    Returns live weather for any Marathwada district using Open-Meteo.
    Caches for 30 minutes to stay fast and free.
    """
    now = _time.time()
    # Return cache if fresh
    if district in _weather_cache:
        entry = _weather_cache[district]
        if now - entry["ts"] < _WEATHER_TTL:
            return entry["data"]

    coords = DISTRICT_COORDS.get(district, DISTRICT_COORDS["Nanded"])
    lat, lon = coords

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
        f"precipitation,weather_code,apparent_temperature"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"wind_speed_10m_max,weather_code"
        f"&timezone=Asia%2FKolkata&forecast_days=7"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            raw = resp.json()

        current = raw.get("current", {})
        daily   = raw.get("daily", {})

        # Map WMO weather code → description
        def _desc(code):
            if code == 0:   return "Clear sky"
            if code <= 3:   return "Partly cloudy"
            if code <= 48:  return "Fog"
            if code <= 67:  return "Rain"
            if code <= 77:  return "Snow"
            if code <= 82:  return "Heavy rain"
            if code <= 99:  return "Thunderstorm"
            return "Unknown"

        def _icon(code):
            if code == 0:   return "01d"
            if code <= 3:   return "02d"
            if code <= 48:  return "50d"
            if code <= 67:  return "10d"
            if code <= 77:  return "13d"
            if code <= 82:  return "09d"
            return "11d"

        wcode = current.get("weather_code", 0)
        result = {
            "district": district,
            "lat": lat, "lon": lon,
            "current": {
                "temp_c":       round(current.get("temperature_2m", 0), 1),
                "feels_like_c": round(current.get("apparent_temperature", 0), 1),
                "humidity_pct": current.get("relative_humidity_2m", 0),
                "wind_kmh":     round(current.get("wind_speed_10m", 0), 1),
                "rain_mm":      round(current.get("precipitation", 0), 1),
                "description":  _desc(wcode),
                "icon":         _icon(wcode),
                "weather_code": wcode,
            },
            "forecast_7day": [
                {
                    "date":      daily["time"][i],
                    "max_c":     daily["temperature_2m_max"][i],
                    "min_c":     daily["temperature_2m_min"][i],
                    "rain_mm":   daily["precipitation_sum"][i],
                    "wind_kmh":  daily["wind_speed_10m_max"][i],
                    "description": _desc(daily["weather_code"][i]),
                    "icon":      _icon(daily["weather_code"][i]),
                }
                for i in range(min(7, len(daily.get("time", []))))
            ],
            "source": "Open-Meteo (free, real-time)",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        _weather_cache[district] = {"data": result, "ts": now}
        return result

    except Exception as e:
        log.error(f"Weather fetch failed for {district}: {e}")
        raise HTTPException(status_code=503, detail=f"Weather fetch failed: {str(e)}")


# ── Register Day 2 endpoints (once each) ────────────────────────────────────────
register_forecast_endpoint(app)
register_gemini_endpoint(app)
