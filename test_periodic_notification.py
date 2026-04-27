# -*- coding: utf-8 -*-
"""
TEST PERIODIC NOTIFICATION
Tests the new Morning/Evening greeting logic.
"""

import sys
import os
from pathlib import Path

# Add kisanalert to path
sys.path.insert(0, str(Path(__file__).parent / "kisanalert"))

from src.alerts.fcm_notifier import broadcast_periodic_update

def test_periodic():
    print("Triggering Periodic Market Update Notification...")
    
    # You can change these for testing
    commodity = "Soybean"
    price = 5450.0
    
    try:
        broadcast_periodic_update(commodity, price)
        print("\nNotification sent successfully!")
        print("Check your phone. The message will change based on your CURRENT local time (IST).")
        print("   - Before 12 PM: Good Morning (Subh Prabhat)")
        print("   - 12 PM to 6 PM: Afternoon Update")
        print("   - After 6 PM: Evening Report")
    except Exception as e:
        print(f"Error sending notification: {e}")

if __name__ == "__main__":
    test_periodic()
