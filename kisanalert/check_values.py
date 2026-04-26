import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://localhost:8000"
SEP  = "-" * 45

def get(url, params=None):
    try:
        r = requests.get(f"{BASE}{url}", params=params, timeout=8)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

print("=" * 45)
print("  KisanAlert — Backend Values Checker")
print("  Compare with frontend @ localhost:8080")
print("=" * 45)

# ── 1. Soybean Alert ──────────────────────────────
d = get("/api/v1/alerts/latest", {"commodity": "Soybean", "district": "Nanded"})
print(f"\n[SOYBEAN ALERT]")
print(f"  date        : {d.get('date')}")
print(f"  price       : Rs.{d.get('price')}")
print(f"  crash_score : {d.get('crash_score')}")
print(f"  alert_level : {d.get('alert_level')}")

# ── 2. Cotton Alert ───────────────────────────────
d = get("/api/v1/alerts/latest", {"commodity": "Cotton", "district": "Nanded"})
print(f"\n[COTTON ALERT]")
print(f"  date        : {d.get('date')}")
print(f"  price       : Rs.{d.get('price')}")
print(f"  crash_score : {d.get('crash_score')}")
print(f"  alert_level : {d.get('alert_level')}")

# ── 3. Turmeric Alert ─────────────────────────────
d = get("/api/v1/alerts/latest", {"commodity": "Turmeric", "district": "Nanded"})
print(f"\n[TURMERIC ALERT]")
print(f"  date        : {d.get('date')}")
print(f"  price       : Rs.{d.get('price')}")
print(f"  crash_score : {d.get('crash_score')}")
print(f"  alert_level : {d.get('alert_level')}")

# ── 4. Weather ────────────────────────────────────
d = get("/api/v1/weather/current", {"district": "Nanded"})
cur = d.get("current", {})
print(f"\n[WEATHER - Nanded]")
print(f"  temp_c      : {cur.get('temp_c')}")
print(f"  rain_mm     : {cur.get('rain_mm')}")
print(f"  description : {cur.get('description')}")

# ── 5. Forecast ───────────────────────────────────
d = get("/api/v1/forecast/multi-day", {"commodity": "Soybean", "district": "Nanded"})
print(f"\n[FORECAST - Soybean]")
print(f"  current_price   : Rs.{d.get('current_price')}")
print(f"  trend           : {d.get('trend')}")
print(f"  day_3_predicted : Rs.{d.get('day_3_predicted')} ({d.get('day_3_change_pct')}%)")
print(f"  day_10_predicted: Rs.{d.get('day_10_predicted')} ({d.get('day_10_change_pct')}%)")

# ── 6. Mandi Compare ──────────────────────────────
mandis = get("/api/v1/mandis/compare", {"commodity": "Soybean"})
print(f"\n[MANDI COMPARE - Soybean]")
if isinstance(mandis, list):
    for m in mandis[:4]:
        print(f"  {m.get('district'):12s}: Rs.{m.get('price')}  score:{m.get('crash_score')}  [{m.get('alert_level')}]")

# ── 7. Farmer Stats ───────────────────────────────
d = get("/api/v1/farmer/stats")
print(f"\n[FARMER STATS]")
print(f"  total_alerts   : {d.get('total_alerts')}")
print(f"  crashes_caught : {d.get('crashes_caught')}")
print(f"  money_saved    : {d.get('money_saved')}")
print(f"  alert_streak   : {d.get('alert_streak')}")

# ── 8. Trust Badge ────────────────────────────────
d = get("/accuracy", {"days": 30})
stats = d.get("stats", {})
print(f"\n[TRUST BADGE]")
print(f"  total      : {stats.get('total')}")
print(f"  correct    : {stats.get('correct')}")
print(f"  accuracy   : {stats.get('accuracy')}")
print(f"  badge_en   : {d.get('badge_english', '')[:50]}")

# ── 9. Voice Query ────────────────────────────────
try:
    r = requests.post(f"{BASE}/api/v1/voice/query",
        json={"query": "soybean price", "commodity": "Soybean", "district": "Nanded"},
        timeout=8)
    d = r.json()
    print(f"\n[VOICE/AI]")
    print(f"  source   : {d.get('source')}")
    print(f"  response : {str(d.get('marathi_response',''))[:60]}...")
except Exception as e:
    print(f"\n[VOICE/AI]  error: {e}")

print(f"\n{'=' * 45}")
print("  Copy above values & verify on localhost:8080")
print("=" * 45)
