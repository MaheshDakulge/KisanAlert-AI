# -*- coding: utf-8 -*-
"""
KisanAlert v2.0 - Live FastAPI Backend
Provides real-time access to the latest price crash alerts and agricultural updates.
Run this using: uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Import Supabase client
from src.supabase_client import get_supabase
import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="KisanAlert Live API",
    description="Real-time Crop Price Crash Prediction and Decision Executor for Marathwada Farmers",
    version="2.0.0",
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
    import subprocess
    try:
        # Run the pipeline script as a subprocess
        cmd = ["python", "run_pipeline.py", "--crop", commodity]
        # We run it synchronously here so the API caller knows when it's done. 
        # For a truly scalable app, this should be a background task using Celery or FastAPI BackgroundTasks.
        process = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent))
        
        if process.returncode != 0:
            log.error(f"Pipeline failed: {process.stderr}")
            raise HTTPException(status_code=500, detail="Pipeline execution failed.")
            
        return {"status": "success", "message": f"Pipeline successfully executed for {commodity}. New alerts generated."}
    except Exception as e:
        log.error(f"Subprocess error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start the pipeline.")
