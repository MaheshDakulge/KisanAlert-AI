# -*- coding: utf-8 -*-
"""
Twilio WhatsApp Webhook for KisanAlert v2.0.
Connects the farmer's WhatsApp text to Gemini AI.
URL: /api/v1/whatsapp/webhook
"""

import logging
from fastapi import APIRouter, Form, Request, Response
from src.voice.gemini_voice import answer_query
from src.supabase_client import get_supabase

log = logging.getLogger(__name__)

whatsapp_router = APIRouter()

@whatsapp_router.post("/api/v1/whatsapp/webhook", tags=["WhatsApp"])
async def twilio_whatsapp_webhook(
    Body: str = Form(default=""),
    From: str = Form(default="")
):
    """
    Twilio webhook for incoming WhatsApp messages.
    """
    log.info(f"Incoming WhatsApp message from {From}: {Body}")
    
    # 1. Fetch latest Soybean context
    context = {}
    try:
        supabase = get_supabase()
        result = supabase.table("daily_alerts").select("*").eq("commodity", "Soybean").order("date", desc=True).limit(1).execute()
        if result.data:
            context = result.data[0]
    except Exception as e:
        log.warning(f"Failed to fetch context for WhatsApp webhook: {e}")

    # 2. Get AI translation & decision
    # If the user typed nothing, we just say hi
    if not Body.strip():
        Body = "सध्याचा भाव काय आहे?"

    reply_dict = answer_query(query=Body, commodity="Soybean", context=context) # type: ignore
    reply_text = reply_dict.get("marathi_response", "मला तुमची विनंती समजली नाही. कृपया पुन्हा प्रयत्न करा.")

    # 3. Construct TwiML XML
    # TwiML requires standard XML tags
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{reply_text}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")

def register_whatsapp_endpoint(app):
    app.include_router(whatsapp_router)
