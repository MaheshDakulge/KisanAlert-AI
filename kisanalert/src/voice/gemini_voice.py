# -*- coding: utf-8 -*-
"""
Gemini Voice Q&A — Real Marathi AI advisor for farmers.
Uses Google Gemini API (FREE tier: 60 requests/minute).

Setup:
  1. Get API key: https://aistudio.google.com/app/apikey
  2. Add to .env:   GEMINI_API_KEY=your_key_here
  3. pip install google-generativeai

Registered in api.py via register_gemini_endpoint(app).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# ── MSP constants (2024-25 season) ─────────────────────────────────
MSP = {
    "Soybean":  4892,
    "Cotton":   7121,
    "Turmeric": 12000,
}

SYSTEM_PROMPT = """\
You are KisanAlert, an AI advisor for Marathi farmers in Maharashtra, India.

RULES:
1. ALWAYS respond in Marathi (Devanagari script). Keep responses under 3 sentences.
2. Be specific: mention prices (₹), mandis, or days when possible.
3. Use simple Marathi that rural farmers understand (avoid English jargon).
4. If asked about crops: focus on Soybean (सोयाबीन), Cotton (कापूस), Turmeric (हळद).
5. Key mandis: Nanded, Latur, Hingoli, Parbhani, Osmanabad.
6. Current MSP: Soybean ₹4,892 | Cotton ₹7,121 | Turmeric ₹12,000.
7. NEVER make up prices. If unsure, say "मंडीत चौकशी करा".
8. End with actionable advice: sell, hold, or wait.

CONTEXT (today's live data):
- Crop: {commodity}
- Today's price: ₹{price}/quintal (Nanded APMC)
- Signal: {level} — {signal_meaning}
- MSP: ₹{msp}/quintal
- Date: {date}

Farmer's question: {question}

Your answer in Marathi (max 3 sentences):"""


def _rule_based_answer(query: str, commodity: str, context: dict) -> str:
    """Fast offline fallback answers using hard-coded rules."""
    q = query.lower()
    price = context.get("price", 0)
    level = context.get("alert_level", "AMBER")
    msp   = MSP.get(commodity, 5000)

    if any(kw in q for kw in ["msp", "किमान", "समर्थन"]):
        return (
            f"{commodity} चा MSP ₹{msp}/क्विंटल आहे. "
            f"आजचा बाजार भाव ₹{price:.0f} आहे, "
            f"{'MSP पेक्षा जास्त' if price > msp else 'MSP पेक्षा कमी'}."
        )

    if any(kw in q for kw in ["विकू", "विकणे", "sell", "बेच"]):
        if level == "GREEN":
            return f"होय! आज {commodity} विकण्यास उत्तम वेळ आहे. भाव ₹{price:.0f} — ३० दिवसांतील सर्वोच्च."
        elif level == "RED":
            return f"नाही, आज {commodity} विकू नका. भाव पडण्याचा अंदाज आहे. थोडे दिवस थांबा."
        elif level == "BLUE":
            return f"{commodity} थांबा — भाव येत्या दिवसांत वाढण्याचा अंदाज आहे. ₹{price:.0f} पेक्षा जास्त मिळेल."
        else:
            return f"{commodity} चा भाव ₹{price:.0f} आहे. बाजार स्थिर आहे. गरजेनुसार निर्णय घ्या."

    if any(kw in q for kw in ["भाव", "price", "किमती", "rate"]):
        return f"आज {commodity} चा भाव ₹{price:.0f}/क्विंटल आहे (नांदेड मंडी). Signal: {level}."

    if any(kw in q for kw in ["हवामान", "पाऊस", "weather", "rain"]):
        return "हवामान माहितीसाठी Weather tab उघडा. जोरदार पाऊस असल्यास काढणी पुढे ढकला."

    if any(kw in q for kw in ["nafed", "नाफेड", "सरकार"]):
        return "NAFED सरकारचा साठा बाजारात आणतो त्यामुळे भाव पडतो. नवीन NAFED टेंडर असल्यास RED अलर्ट मिळेल."

    if any(kw in q for kw in ["मंडी", "mandi", "बाजार", "जवळची"]):
        return "Mandi Map tab मध्ये जवळच्या सार्‍या मंडींचे भाव पहा. हिंगोली आणि लातूर चांगले पर्याय आहेत."

    return (
        f"आपला प्रश्न समजला. {commodity} बद्दल: आजचा भाव ₹{price:.0f}, "
        f"Signal: {level}. अधिक माहितीसाठी Predict tab पहा."
    )


def answer_query(query: str, commodity: str = "Soybean", context: Optional[dict] = None) -> dict:
    """
    Answer a farmer's voice query in Marathi.
    Uses Gemini if API key is set, else falls back to rule-based.
    """
    if context is None:
        context = {}

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")

    if gemini_key:
        try:
            import google.genai as genai
            client = genai.Client(api_key=gemini_key)

            price = context.get("price", 0)
            level = context.get("alert_level", "AMBER")
            msp   = MSP.get(commodity, 5000)
            signal_meaning = {
                "RED":   "DO NOT SELL — crash incoming",
                "BLUE":  "HOLD — price rising soon",
                "GREEN": "SELL TODAY — peak price",
                "AMBER": "Stable market",
            }.get(level, "Check KisanAlert app")

            prompt = SYSTEM_PROMPT.format(
                commodity=commodity,
                price=price,
                level=level,
                signal_meaning=signal_meaning,
                msp=msp,
                date=datetime.now().strftime("%Y-%m-%d"),
                question=query,
            )

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )

            marathi_text = response.text.strip() if response.text else ""
            return {
                "marathi_response": marathi_text,
                "english_response": "",
                "source": "gemini",
                "model": "gemini-2.0-flash",
                "commodity": commodity,
                "error": None,
            }

        except ImportError:
            log.warning("google-genai not installed — run: pip install google-genai")
        except Exception as e:
            log.warning("Gemini failed (%s) — using rule-based fallback", e)

    # Rule-based fallback
    answer = _rule_based_answer(query, commodity, context)
    return {
        "marathi_response": answer,
        "english_response": "",
        "source": "rule_based",
        "model": "fallback_rules",
        "commodity": commodity,
        "error": None,
    }


# ═══════════════════════════════════════════════════════════════════
# FastAPI endpoint registration
# ═══════════════════════════════════════════════════════════════════

def register_gemini_endpoint(app):
    """Call from api.py: register_gemini_endpoint(app)"""
    from fastapi import HTTPException
    from pydantic import BaseModel

    class VoiceQuery(BaseModel):
        query: str
        commodity: str = "Soybean"
        district: str = "Nanded"

    @app.post("/api/v1/voice/query", tags=["Voice"])
    def voice_query(payload: VoiceQuery):
        """Answer a farmer's voice query in Marathi using Gemini or rule-based fallback."""
        try:
            # Fetch live context from Supabase (best-effort — no crash if it fails)
            context: dict = {}
            try:
                from src.supabase_client import get_supabase
                sb = get_supabase()
                result = (
                    sb.table("daily_alerts")
                    .select("price,alert_level,crash_score,rise_score")
                    .eq("commodity", payload.commodity)
                    .eq("district", payload.district)
                    .order("date", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data and isinstance(result.data[0], dict):
                    context = dict(result.data[0])
            except Exception:
                pass  # Fallback with empty context — rule-based will still work

            return answer_query(payload.query, payload.commodity, context)

        except Exception as e:
            log.error("Voice endpoint failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Standalone test — run: python gemini_voice.py
    print("\n" + "=" * 60)
    print("  Gemini Voice Q&A Test")
    print("=" * 60)

    test_context = {"price": 5352, "alert_level": "AMBER", "crash_score": 0.44}

    test_questions = [
        "सोयाबीन कधी विकायचे?",
        "आज सर्वोत्तम मंडी कुठे?",
        "MSP किती आहे?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        result = answer_query(q, "Soybean", test_context)
        print(f"A: {result['marathi_response']}")
        print(f"   (source: {result['source']})")
