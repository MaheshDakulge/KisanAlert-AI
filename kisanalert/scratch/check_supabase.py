import sys
sys.path.insert(0, '.')
from src.supabase_client import get_supabase
import json

sb = get_supabase()
try:
    res = sb.table("daily_alerts").select("*").limit(5).execute()
    print("DAILY ALERTS SAMPLE:")
    print(json.dumps(res.data, indent=2))
    
    # Check count for Soybean Nanded
    res2 = sb.table("daily_alerts").select("count").eq("commodity", "Soybean").eq("district", "Nanded").execute()
    print(f"\nSoybean Nanded count: {res2.data}")
    
except Exception as e:
    print(f"Error: {e}")
