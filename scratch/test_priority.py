import sys
from pathlib import Path

# Add kisanalert to path
ROOT = Path(__file__).parent.parent / "kisanalert"
sys.path.insert(0, str(ROOT))

from src.alerts.alert_engine import classify_signal

def test_priority():
    print("Testing Signal Priority Logic Swap...")
    print("-" * 40)
    
    # Scenario: Today is at peak AND AI predicts a rise
    # Previously: returned GREEN
    # Now: should return BLUE
    
    crash_score = 0.15 # Low risk
    rise_score = 0.75  # High rise probability
    current_price = 5150
    price_30d_max = 5200
    trend_is_rising = True
    
    signal = classify_signal(
        crash_score=crash_score,
        rise_score=rise_score,
        current_price=current_price,
        price_30d_max=price_30d_max,
        trend_is_rising=trend_is_rising
    )
    
    print(f"Inputs: crash={crash_score}, rise={rise_score}, at_peak=True, trend_rising=True")
    print(f"Resulting Signal: {signal}")
    
    if signal == "BLUE":
        print("✅ SUCCESS: BLUE took priority over GREEN.")
    else:
        print("❌ FAILURE: GREEN still took priority.")

if __name__ == "__main__":
    test_priority()
