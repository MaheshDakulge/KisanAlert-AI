# KisanAlert v2.0 - Backend API & Cloud Sync

The nervous system of KisanAlert is a highly robust Python FastAPI backend that bridges the Machine Learning predictive models with the Flutter Mobile Application and external messaging relays.

## 1. FastAPI Infrastructure (`api.py`)

The application is hosted on `uvicorn` (FastAPI). It serves a suite of JSON REST endpoints designed for fast, low-latency mobile consumption. Key endpoints include:

-   `GET /api/v1/alerts/latest`: The core endpoint. Combines all ML calculations, API scrapes (NCDEX), and caching logic into a single `AlertResponse` payload for the mobile home screen. It outputs transparent metadata, indicating if data is `LIVE` or sourced from `CACHE`.
-   `GET /api/v1/mandis/compare`: The inter-mandi spatial comparison system, returning nearby mandi price spreads.
-   `GET /api/v1/forecast`: Provides standard ML multi-day predictive charting limits.
-   `POST /api/v1/voice/ask`: Relays a voice transcript back to Google Gemini for real-time agricultural advisory.

## 2. Supabase Integration (`src.supabase_client.py`)

KisanAlert relies on **Supabase (PostgreSQL)** for distributed cloud storage and historical data retrieval.

-   **Why Supabase?** Provides secure RESTful row-level security while offering high-speed timeseries querying for the ML pipeline.
-   **The `historical_prices` table:** Stores years of historical Agmarknet baseline data. The ML pipeline pulls trailing windows (last 90 days) from Supabase on-the-fly to calculate rolling averages and wave functions.

## 3. The Fallback Mechanism (Resilience Architecture)

A core requirement for KisanAlert is **Zero-Downtime Resilience**, critical for hackathons and rural connectivity gaps. To prevent "Zero Price" UI crashes, the API uses a robust fallback ladder:

1.  **Tier 1 (Optimal):** Fetch strictly live, real-time prices from `data.gov.in` + NCDEX scrapers. Calculate ML scores immediately. 
2.  **Tier 2 (Database Level):** If government APIs timeout or rate limit, fall back to the last known Supabase SQL row for that commodity/district.
3.  **Tier 3 (Local DB):** If the network to Supabase completely drops (`credentials not found` or DNS fail), fall back to `offline_cache.db` (SQLite) or raw `.csv` historical files bundled into the backend build.
4.  **Tier 4 (Hardcoded Guardrails):** Failsafe values designed to keep the UI from crashing, rendering placeholders cleanly.

This guarantees that the farmer *always* sees a price and a UI, even when upstream government servers are under maintenance.

## 4. Background Chron Jobs
Within the FastAPI application lifecycle (`BackgroundTasks`), the system natively triggers scheduled pipelines (`run_pipeline.py`) hourly to ingest new data, update the cache tables, calculate predictions autonomously, and prepare the Firebase event relays without a user needing to open the app.
