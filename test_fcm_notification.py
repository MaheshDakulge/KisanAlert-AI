# -*- coding: utf-8 -*-
"""
🧪 DUMMY FCM NOTIFICATION TEST SCRIPT
Sends a test notification to verify Firebase Cloud Messaging setup.

Usage:
  python test_fcm_notification.py --type data_refresh
  python test_fcm_notification.py --type red_alert
  python test_fcm_notification.py --type custom --message "Your custom message"
"""

import sys
import os
import logging
from pathlib import Path
import argparse
from datetime import datetime

# Add kisanalert to path
sys.path.insert(0, str(Path(__file__).parent / "kisanalert"))

import config
from src.alerts.fcm_notifier import (
    get_firebase_app,
    broadcast_data_refresh,
    broadcast_crash_alert,
    broadcast_market_update
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("test_fcm")


def test_firebase_init():
    """Test if Firebase is properly initialized."""
    log.info("🔍 Testing Firebase initialization...")
    app = get_firebase_app()
    if app:
        log.info("✅ Firebase initialized successfully!")
        return True
    else:
        log.error("❌ Firebase initialization failed!")
        log.error("Make sure FIREBASE_ADMIN_SDK_JSON environment variable is set.")
        return False


def send_test_data_refresh():
    """Send a test DATA_REFRESH notification."""
    log.info("📱 Sending TEST DATA_REFRESH notification...")
    try:
        broadcast_data_refresh(
            commodity="Soybean",
            price=7500.00,
            alert_level="AMBER",
            message_mr="🧪 Test notification - आपके फोन पर यह संदेश आ रहा है!",
        )
        log.info("✅ DATA_REFRESH notification sent successfully!")
        return True
    except Exception as e:
        log.error(f"❌ Failed to send DATA_REFRESH: {e}")
        return False


def send_test_red_alert():
    """Send a test RED alert notification."""
    log.info("🚨 Sending TEST RED ALERT notification...")
    try:
        broadcast_crash_alert(
            commodity="Cotton",
            price=6200.00,
            alert_message="🧪 TEST: कपास की कीमत में तेज गिरावट! कृपया तुरंत कार्रवाई करें।",
        )
        log.info("✅ RED ALERT notification sent successfully!")
        return True
    except Exception as e:
        log.error(f"❌ Failed to send RED ALERT: {e}")
        return False


def send_custom_notification(message: str, alert_level: str = "GREEN", price: float = 7800.0):
    """Send a custom test notification."""
    log.info(f"🎯 Sending CUSTOM notification: {message}")
    try:
        is_alert = alert_level == "RED"
        broadcast_market_update(
            commodity="Turmeric",
            price=price,
            message=message,
            is_alert=is_alert,
        )
        log.info("✅ Custom notification sent successfully!")
        return True
    except Exception as e:
        log.error(f"❌ Failed to send custom notification: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Test KisanAlert FCM Push Notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test DATA_REFRESH (silent reload)
  python test_fcm_notification.py --type data_refresh
  
  # Test RED ALERT (loud notification)
  python test_fcm_notification.py --type red_alert
  
  # Send custom message
  python test_fcm_notification.py --type custom --message "Haldi rate badh gaya!"
  
  # Check Firebase setup
  python test_fcm_notification.py --check-firebase
        """
    )
    
    parser.add_argument(
        "--type",
        choices=["data_refresh", "red_alert", "custom"],
        help="Type of test notification to send",
    )
    parser.add_argument(
        "--message",
        type=str,
        help="Custom message for --type custom",
    )
    parser.add_argument(
        "--check-firebase",
        action="store_true",
        help="Only check if Firebase is initialized (don't send notification)",
    )
    parser.add_argument(
        "--price",
        type=float,
        default=7800.0,
        help="Price to include in notification (default: 7800)",
    )
    
    args = parser.parse_args()
    
    # Check Firebase
    if args.check_firebase or not args.type:
        if not test_firebase_init():
            sys.exit(1)
        if args.check_firebase:
            log.info("\n✨ Firebase is ready for testing!")
            sys.exit(0)
    
    # Send appropriate notification
    if args.type == "data_refresh":
        if not send_test_data_refresh():
            sys.exit(1)
    elif args.type == "red_alert":
        if not send_test_red_alert():
            sys.exit(1)
    elif args.type == "custom":
        if not args.message:
            log.error("❌ --message required for --type custom")
            sys.exit(1)
        if not send_custom_notification(args.message, price=args.price):
            sys.exit(1)
    
    log.info("\n" + "=" * 50)
    log.info("✅ Test notification sent!")
    log.info("=" * 50)
    log.info("\n📲 Check your device for the notification.")
    log.info("   Make sure the app is subscribed to 'market_alerts' topic.\n")


if __name__ == "__main__":
    main()
