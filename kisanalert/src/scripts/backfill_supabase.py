# -*- coding: utf-8 -*-
"""
Backfill historical predictions into Supabase.
Runs inference on the test set (e.g., 2025-2026) and pushes the records
so the frontend dashboard has graph data.
"""

import sys
import logging
import time
from pathlib import Path

# Force UTF-8 on Windows
import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
import config
from src.data.loader import load_clean_data
from src.features.engineer import engineer_features, FEATURE_COLUMNS
from src.models.xgb_model import load_model
from src.alerts.alert_engine import generate_alert
from src.supabase_client import push_daily_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

def backfill():
    log.info("Starting backfill to Supabase...")
    
    # 1. Load data & engineer features
    log.info("Loading and processing data...")
    df_clean = load_clean_data()
    df_features = engineer_features(df_clean)
    
    # 2. Filter to just the recent period (e.g., test set start to current)
    # config.TEST_START is typically '2025-01-01'
    mask = df_features["date"] >= pd.Timestamp(config.TEST_START)
    df_recent = df_features[mask].copy().reset_index(drop=True)
    
    log.info("Found %d days to backfill.", len(df_recent))
    if df_recent.empty:
        log.warning("No data found to backfill.")
        return
        
    # 3. Load model
    model = load_model()
    
    # 4. Predict
    X = df_recent[FEATURE_COLUMNS]
    probs = model.predict_proba(X)[:, 1]
    
    # 5. Calculate soft scores
    probs_yesterday = np.roll(probs, 1)
    probs_yesterday[0] = probs[0]  # fill first row
    
    if config.USE_SOFT_CONFIRMATION:
        soft_scores = (
            config.SOFT_CONFIRMATION_TODAY_WEIGHT * probs
            + config.SOFT_CONFIRMATION_PREV_WEIGHT * probs_yesterday
        )
    else:
        soft_scores = probs
        
    # 6. Push to Supabase
    success_count = 0
    log.info("Beginning push to Supabase (this may take a minute)...")
    
    for i, row in df_recent.iterrows():
        date_str = str(row["date"].date())
        price = float(row["modal_price"])
        score = float(soft_scores[i])
        
        # Determine alert level and message
        alert = generate_alert(crash_score=score, date=date_str, price=price)
        
        try:
            push_daily_alert(
                date=date_str,
                price=price,
                crash_score=score,
                alert_level=alert["alert_level"],
                message=alert["marathi_message"]
            )
            success_count += 1
            if success_count % 50 == 0:
                log.info("Pushed %d of %d records...", success_count, len(df_recent))
        except Exception as e:
            log.error("Failed on date %s: %s", date_str, e)
            
    log.info("✅ Backfill complete! Successfully pushed %d records.", success_count)

if __name__ == "__main__":
    backfill()
