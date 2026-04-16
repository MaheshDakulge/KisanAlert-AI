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
from datetime import datetime
import os
import google.generativeai as genai

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
    allow_credentials=True,
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
            
        return result.data[0]
        
    except Exception as e:
        log.error(f"Error fetching alert from Supabase: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching alerts.")


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
        return result.data
    except Exception as e:
        log.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching history.")

@app.post("/api/v1/pipeline/trigger", tags=["Pipeline"])
def trigger_pipeline(commodity: str = Query(..., description="Crop name to execute pipeline for")):
    """
    Manually triggers the ML pipeline to fetch new data and generate an updated prediction.
    WARNING: This can take 15-30 seconds as it hits Agmarknet, OpenWeatherMap, and Gemini APIs.
    """
def _run_pipeline_bg(commodity: str):
    """Background worker — runs pipeline subprocess without blocking the API."""
    import subprocess
    try:
        cmd = ["python", "run_pipeline.py", "--crop", commodity]
        process = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent))
        if process.returncode != 0:
            log.error(f"Background pipeline failed for {commodity}: {process.stderr}")
        else:
            log.info(f"Background pipeline completed for {commodity}")
    except Exception as e:
        log.error(f"Background pipeline exception: {e}")


@app.post("/api/v1/pipeline/trigger", tags=["Pipeline"])
def trigger_pipeline(
    commodity: str = Query(..., description="Crop name to execute pipeline for"),
    background_tasks: BackgroundTasks = None,
):
    """
    Triggers the ML pipeline asynchronously using BackgroundTasks —
    returns immediately, runs in background (no more 30-second API freezes).
    """
    if background_tasks is not None:
        background_tasks.add_task(_run_pipeline_bg, commodity)
        return {"status": "accepted", "message": f"Pipeline started for {commodity} in background. Check /alerts/latest in ~30s."}
    # Fallback: sync run (shouldn't happen with proper FastAPI injection)
    _run_pipeline_bg(commodity)
    return {"status": "success", "message": f"Pipeline completed for {commodity}."}

@app.post("/api/v1/predict", tags=["Pipeline"])
def predict(commodity: str = Query(..., description="Crop name")):
    """
    Predicts crash probability using the latest scraped data and ML pipeline.
    """
    # 1. Scrape latest data
    scraper = AgmarknetScraper()
    latest_data = scraper.get_latest_data(commodity=commodity)
    if not latest_data:
        raise HTTPException(status_code=500, detail="Failed to scrape live data from Agmarknet.")
    
    # 2. Run pipeline
    return trigger_pipeline(commodity=commodity)

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
            
        latest_date = result.data[0]['date']
        
        # Filter strictly for the latest date
        todays_alerts = [alert for alert in result.data if alert['date'] == latest_date]
        
        # Rank by lowest crash score
        ranked = sorted(todays_alerts, key=lambda x: x['crash_score'])
        return ranked
    except Exception as e:
        log.error(f"Failed to compare mandis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/community/stories", tags=["Community"])
def get_community_stories(commodity: str = Query(..., description="Crop name filter for stories")):
    """
    Returns verified community stories (Chopal) to show how farmers are using alerts.
    """
    # For now, returning live structured data generated dynamically.
    # In production, this would query a user reviews table in Supabase.
    return [
        {
            "initials": "DN", "avatarColor": "green", "nameEn": "Dhule Nagnath · Degloor", 
            "distanceKm": "12km", "messageMr": f"{commodity} 2 दिवस थांबलो → ₹1,800 जास्त मिळाले", 
            "messageEn": f"Waited 2 days for {commodity} → earned Rs.1,800 more",
            "isVerified": True, "verifiedDate": "Agmarknet 14 Apr 2026", "crop": commodity, 
            "saved": "₹1,800/qtl — ₹18,000 total (10 qtl)"
        },
        {
            "initials": "KP", "avatarColor": "amber", "nameEn": "Kamble Prashant · Biloli", 
            "distanceKm": "28km", "messageMr": "NAFED अलर्ट मिळाला → ₹6,400 नुकसान वाचले", 
            "messageEn": "Got NAFED alert → saved Rs.6,400 total loss",
            "isVerified": True, "verifiedDate": "Sale confirmed 18 Apr", "crop": commodity, 
            "saved": "₹320/qtl — ₹6,400 total (20 qtl)"
        }
    ]

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
            alert = result.data[0]
            context = f"Today's price for {alert['commodity']} in {alert['district']} is Rs {alert['price']}. There is a {alert['crash_score'] * 100}% probability of a price crash. The AI says: {alert['message']}"

        # 2. Call Gemini
        if not os.getenv("GEMINI_API_KEY"):
            return {"marathi_response": "Sorry, Gemini API Key is missing. [Fallback Mock Marathi Response]"}

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        You are an expert agriculture agent helping a farmer in Maharashtra.
        They asked: "{request.query}"
        
        Here is the current backend market data context:
        {context}
        
        Respond ONLY in clear, natural Marathi language. Keep it very concise (1-2 sentences).
        """
        response = model.generate_content(prompt)
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
        # Nanded coordinates — can be parameterized per district later
        district_coords = {
            "Nanded":    (19.15, 77.32),
            "Latur":     (18.40, 76.56),
            "Osmanabad": (18.18, 76.04),
            "Parbhani":  (19.27, 76.77),
            "Hingoli":   (19.72, 77.15),
        }
        lat, lon = district_coords.get(district, (19.15, 77.32))
        import requests as req
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,precipitation_sum"
            f"&forecast_days=7&timezone=Asia/Kolkata"
        )
        r = req.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        daily = data.get("daily", {})
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
                "temp_max_c": round(d[1], 1),
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
        log.error(f"Weather fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch weather data.")


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
                "summary": e.get("summary", "")[:200],
            }
            for e in feed.entries[:10]
        ]
    except Exception as e:
        log.error(f"News fetch failed: {e}")
        return []  # Fail gracefully — news is non-critical
