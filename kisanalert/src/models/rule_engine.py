# -*- coding: utf-8 -*-
"""
Phase 10: Deterministic Macro Rule Engine
Evaluates hard rules that override ML soft-scores in emergency situations.
"""

import logging
import pandas as pd
from datetime import datetime

log = logging.getLogger(__name__)

# Hardcoded Historical Dates for NAFED/Export Bans overrides
# In production, these might be populated via a GUI/Admin Panel
MACRO_SHOCKS = {
    # e.g., "2024-09-10": "NAFED Dump"
}

def evaluate_macro_rules(date_str: str, df_macro: pd.DataFrame, today_row: pd.Series = None) -> dict:
    """
    Evaluates macro indicators and specific rule thresholds for a specific date.
    Returns:
        {"override_level": "RED"|"GREEN"|None, "reason": str|None}
    """
    target_date = pd.to_datetime(date_str)
    
    # 1. Manual Historical/News Interventions
    formatted_date = target_date.strftime("%Y-%m-%d")
    if formatted_date in MACRO_SHOCKS:
        event = MACRO_SHOCKS[formatted_date]
        log.warning("MACRO OVERRIDE: Hard event %s triggered for %s", event, date_str)
        return {
            "override_level": "RED",
            "reason": f"Government Intervention: {event}. Markets likely to crash."
        }
        
    if df_macro is None or df_macro.empty:
        return {"override_level": None, "reason": None}

    # Find the nearest macro data row (markets might be closed on weekends)
    past_macro = df_macro[df_macro["date"] <= target_date]
    if past_macro.empty:
        return {"override_level": None, "reason": None}
        
    macro_today = past_macro.iloc[-1]
    
    # 2. CBOT Plunge (Global Crash)
    if macro_today.get("cbot_weekly_change", 0.0) < -0.05: # > 5% drop in a week
        log.warning("MACRO OVERRIDE: CBOT Futures plunged %s%%", round(macro_today["cbot_weekly_change"]*100, 2))
        return {
            "override_level": "RED",
            "reason": "Global Soybean market crash (CBOT). Indian prices generally follow."
        }
    
    # 3. Supply Shocks directly from today_row
    if today_row is not None:
        commodity = today_row.get("commodity", getattr(df_macro, "TARGET_COMMODITY", "Soybean"))
        from src.data.macro_loader import fetch_dgft_export_ban_flag, fetch_nafed_release_flag
        
        # Rule R01: DGFT Export Ban Active
        if fetch_dgft_export_ban_flag(commodity) == 1.0:
            log.warning("RULE ENGINE (R01): DGFT Export Ban Active for %s", commodity)
            return {
                "override_level": "RED",
                "reason": "सरकारी निर्यात बंदी लागू! (Govt Export Ban Active. Local supply will surge)."
            }

        # Rule R03 / R02 Combined: NAFED Dump + Massive Arrival Surge (>3x normal)
        arrival_ratio = today_row.get("arrival_ratio", 0.0)
        
        # NAFED Dump check
        if fetch_nafed_release_flag(commodity) == 1.0 and arrival_ratio > 2.0:
            log.warning("RULE ENGINE (NAFED): Gov stockpiles released + arrival > 2x")
            return {
                "override_level": "RED",
                "reason": "नाफेड कडून बाजारात माल आला आहे, आवक दुप्पट! (NAFED Stockpile Released. Crash imminent)."
            }
            
        # Using 3.0 as threshold specified in PDF
        if arrival_ratio > 3.0:
            log.warning("RULE ENGINE (R03): arrival_ratio is %.2f (> 3.0)", arrival_ratio)
            return {
                "override_level": "RED",
                "reason": "आवक ३ पटीने वाढली आहे. बाजार कोसळण्याची दाट शक्यता आहे. (Arrivals are 3x normal, high crash risk)."
            }
            
        # Rule R04: Severe Price Velocity Crash
        velocity = today_row.get("price_velocity", 0.0)
        if velocity < -0.15:
            log.warning("RULE ENGINE (R04): price_velocity is %.2f (< -0.15)", velocity)
            return {
                "override_level": "RED",
                "reason": "गेल्या ३ दिवसांत भाव १५ टक्क्यांनी पडले आहेत. (Price has dropped 15% in 3 days. Do not sell today)."
            }
            
        # Rule R05 Plugin: If Surrounding markets (Lead markets) crashed heavily
        lag_score = today_row.get("price_wave_lag_score", 0.0)
        if lag_score < -0.10: # Surrounding dropped 10% below Nanded yesterday
            log.warning("RULE ENGINE (R05): Surrounding markets dropped significantly (lag_score: %.2f)", lag_score)
            return {
                "override_level": "AMBER",
                "reason": "आसपासच्या मार्केटमध्ये भाव १०% पडले आहेत. ३६ तासात इथेही परिणाम दिसेल. (Surrounding markets dropped 10%. Price wave hitting Nanded within 36 hrs)."
            }
            
    return {"override_level": None, "reason": None}
