# -*- coding: utf-8 -*-
"""
Firebase Cloud Messaging (FCM) Integration for KisanAlert.
Pushes RED alerts to farmers' phones via the 'market_alerts' topic.
"""

import os
import logging
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, messaging

log = logging.getLogger(__name__)

def get_firebase_app():
    """Initializes and returns the generic Firebase App instance."""
    try:
        # Avoid initializing multiple times
        return firebase_admin.get_app()
    except ValueError:
        # App is not initialized, let's initialize it
        
        # 1. Try to load from Environment Variable (Best for GitHub Actions)
        import json
        import os
        firebase_json = os.environ.get("FIREBASE_ADMIN_SDK_JSON")
        if firebase_json:
            try:
                # Clean the string if it has extra quotes
                if firebase_json.startswith("'") and firebase_json.endswith("'"):
                    firebase_json = firebase_json[1:-1]
                
                cred_dict = json.loads(firebase_json)
                cred = credentials.Certificate(cred_dict)
                log.info("Firebase initialized from environment variable.")
                return firebase_admin.initialize_app(cred)
            except Exception as e:
                log.error(f"Failed to initialize Firebase from environment variable: {e}")
        
        # 2. Try to load from local file
        base_dir = Path(__file__).resolve().parent.parent.parent
        cert_path = base_dir / "firebase-adminsdk.json"
        
        if cert_path.exists():
            cred = credentials.Certificate(str(cert_path))
            log.info(f"Firebase initialized from local file: {cert_path}")
            return firebase_admin.initialize_app(cred)
        
        log.warning("Firebase credentials not found (tried env var 'FIREBASE_ADMIN_SDK_JSON' and file). Push notifications will be skipped.")
        return None

def broadcast_crash_alert(commodity: str, price: float, alert_message: str):
    """
    Broadcasts a real-time RED alert push notification to all devices.
    """
    return broadcast_market_update(commodity, price, alert_message, is_alert=True)

def broadcast_market_update(commodity: str, price: float, message: str, is_alert: bool = False):
    """
    Broadcasts the daily AI decision summary to all devices subscribed to 'market_alerts'.
    """
    app = get_firebase_app()
    if not app:
        return
        
    topic = "market_alerts"
    
    if is_alert:
        title = f"🚨 {commodity} Price Crash Alert!"
        type_str = "RED_ALERT"
    else:
        title = f"📈 {commodity} Market Updated!"
        type_str = "MARKET_UPDATE"
        
    body = f"₹{price:.0f}/qtl — {message}"

    fcm_message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data={
            "commodity": commodity,
            "price": str(price),
            "type": type_str,
        },
        topic=topic,
    )
    
    try:
        response = messaging.send(fcm_message)
        log.info(f"Successfully broadcasted FCM push notification [{type_str}]: {response}")
    except Exception as e:
        log.error(f"Failed to send push notification: {e}")


def broadcast_data_refresh(
    commodity: str,
    price: float,
    alert_level: str,
    message_mr: str = "",
):
    """
    ⭐ KEY: Sends a DATA_REFRESH FCM message that triggers Flutter's auto-reload.
    Flutter's _setupFCMListener() in app_state.dart watches for type='DATA_REFRESH'
    and calls fetchData() silently — all screens update without farmer tapping anything.

    Payload keys are intentionally kept under FCM's 4KB data limit.
    """
    app = get_firebase_app()
    if not app:
        log.warning("[FCM] Firebase not initialized — DATA_REFRESH not sent for %s", commodity)
        return

    from datetime import datetime
    updated_at = datetime.now().strftime("%H:%M IST")

    level_emoji = {"RED": "🚨", "BLUE": "💎", "GREEN": "✅", "AMBER": "⚠️"}.get(alert_level, "📊")
    title = f"{level_emoji} KisanAlert: {commodity} अपडेट ({updated_at})"
    body = f"₹{price:.0f}/qtl — {message_mr[:80]}" if message_mr else f"₹{price:.0f}/qtl — Market updated"

    fcm_message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={
            "type": "DATA_REFRESH",             # Flutter listener key
            "commodity": commodity,
            "price": str(round(price)),
            "alert_level": alert_level,
            "updated_at": updated_at,
        },
        # Android: high priority so the notification wakes the app
        android=messaging.AndroidConfig(priority="high"),
        topic="market_alerts",
    )

    try:
        response = messaging.send(fcm_message)
        log.info("[FCM] DATA_REFRESH sent for %s [%s] → %s", commodity, alert_level, response)
    except Exception as e:
        log.error("[FCM] DATA_REFRESH failed for %s: %s", commodity, e)


def broadcast_periodic_update(commodity: str, price: float):
    """
    Sends a friendly notification for morning/evening updates.
    """
    from datetime import datetime
    import pytz

    # IST timezone logic
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    hour = now_ist.hour

    if 5 <= hour < 12:
        title = "🌅 शुभ प्रभात! बाजार भाव अपडेट"
        body = f"आजचे {commodity} चे ताजे भाव: ₹{price:.0f}/qtl. मार्केट उघडले आहे!"
    elif 12 <= hour < 18:
        title = "🌇 दुपारचे मार्केट अपडेट"
        body = f"{commodity} अपडेट: आताचा भाव ₹{price:.0f}/qtl आहे."
    else:
        title = "🌙 सायंकाळचे मार्केट रिपोर्ट"
        body = f"आजचे मार्केट क्लोजिंग: {commodity} ₹{price:.0f}/qtl."

    app = get_firebase_app()
    if not app:
        log.warning("[FCM] Firebase not initialized - Skipping periodic update for %s", commodity)
        return

    fcm_message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data={
            "type": "MARKET_UPDATE",
            "commodity": commodity,
            "price": str(round(price)),
        },
        android=messaging.AndroidConfig(priority="high"),
        topic="market_alerts",
    )

    try:
        messaging.send(fcm_message)
        log.info(f"[FCM] Periodic update sent for {hour}:00 IST")
    except Exception as e:
        log.error(f"[FCM] Failed periodic update: {e}")

