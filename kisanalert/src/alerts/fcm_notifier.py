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
        base_dir = Path(__file__).resolve().parent.parent.parent
        cert_path = base_dir / "firebase-adminsdk.json"
        
        if not cert_path.exists():
            log.warning(f"Firebase credentials not found at {cert_path}. Push notifications disabled.")
            return None

        cred = credentials.Certificate(str(cert_path))
        return firebase_admin.initialize_app(cred)

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

