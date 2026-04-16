# -*- coding: utf-8 -*-
"""
Phase 13: Google Gemini API Integration
Generates dynamic, hyper-localized Marathi advice for the alerts based on current ML scores and macro data.
Uses the new `google.genai` SDK (v1.0+) with gemini-2.0-flash.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Load .env explicitly — resolve 3 levels up from src/alerts/
ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_client = None

def _get_client():
    """Lazy-initialize the Gemini client."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY not found in .env. Falling back to static messages.")
            return None
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            log.error("Failed to initialize Gemini client: %s", e)
            return None
    return _client


def generate_marathi_explanation(
    commodity: str,
    district: str,
    price_today: float,
    crash_score: float,
    alert_level: str,
    rain_mm: float = 0.0,
    temp_max_c: float = 30.0,
    macro_reason: str = None
) -> str:
    """
    Calls Gemini 2.0 Flash API to generate a 1-2 sentence Marathi alert.
    Returns None on failure so alert_engine falls back to static message.
    """
    client = _get_client()
    if not client:
        return None

    log.info("Generating dynamic Marathi alert with Gemini 2.0 Flash...")

    prompt = f"""You are an expert Maharashtrian agricultural advisor for {district} district.
You are advising a local farmer about {commodity} prices today.

Today's Market Price: Rs. {price_today:,.0f}/quintal.
Today's Weather: Rain = {rain_mm:.1f} mm, Max Temp = {temp_max_c:.1f}°C.
AI Crash Probability: {crash_score * 100:.1f}%.
Alert Level: {alert_level}.
Macro Warning: {macro_reason if macro_reason else 'None.'}

Your task:
Write exactly 1-2 short, clear sentences in natural rural Marathi dialect telling the farmer what to do TODAY.
Rules:
- RED alert: Tell them firmly NOT to sell. If macro warning exists, mention it briefly.
- AMBER alert: Tell them to wait 2-3 days and watch conditions.
- GREEN alert: Tell them it is a good time to sell.
- Use only Marathi. No English words. No brackets. No translations.
- Output ONLY the Marathi text, nothing else."""

    try:
        from google import genai
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        text = response.text.replace("\n", " ").strip()
        log.info("Gemini response: %s", text)
        return text
    except Exception as e:
        log.error("Gemini API call failed: %s", e)
        return None
