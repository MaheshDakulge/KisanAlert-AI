# KisanAlert v2.0 - Core Architecture & Data Ingestion

KisanAlert is a predictive agricultural intelligence platform. It ingests massive amounts of real-time and historical commodity data to detect early signs of price crashes (and price rises), translating them into actionable, farmer-friendly alerts (RED/BLUE/GREEN/AMBER).

This document covers the **Foundational Layer**: Where data comes from and how it enters the system.

## 1. High-Level System Architecture

KisanAlert operates on a 5-layer autonomous pipeline:
1.  **Ingestion Layer**: Pulls data from mandis, global markets, and government policies.
2.  **Feature Factory**: Transforms raw prices into waves, volatility windows, and lead-lag scores.
3.  **AI Engine**: Evaluates features through specialized XGBoost models and deterministic rules to output probabilities.
4.  **Decision & API Layer**: `alert_engine.py` turns model probabilities into one of 4 discrete signals, exposed via a FastAPI REST interface.
5.  **Delivery Layer**: A Flutter mobile dashboard for complex data visualization and an automated Gemini WhatsApp broadcaster for accessibility.

## 2. Real-Time Data Sources

The accuracy of KisanAlert's models depends on high-quality, diverse data streams. We rely on the following deterministic scrapers and APIs (`src.pipeline.scrapers` and `src.data.ncdex_fetcher`):

### A. Spot Market Data (Agmarknet / data.gov.in)
-   **What it does:** Fetches physical, on-the-ground mandi prices (min, max, modal) for crops like Soybean, Cotton, and Turmeric across key districts (e.g., Nanded, Latur).
-   **Why it matters:** This forms the "Current Price" baseline. Everything is modeled against these spot values.
-   **Mechanics:** Handled by `AgmarknetScraper`. It caches responses heavily to avoid `429 Too Many Requests` from the government API.

### B. Domestic Futures (NCDEX / MCX via yfinance & Scrapers)
-   **What it does:** Fetches real-time futures pricing for Indian commodities.
-   **Why it matters:** **This is our 48-Hour Competitive Edge.** Institutional traders use futures to "bet" on prices. If NCDEX Soybean for next month is trading 5% *higher* than today's Nanded spot price, it means the market anticipates a supply squeeze. We calculate this "contango" (premium) or "backwardation" (discount) to preempt physical mandi movements.
-   **Mechanics:** Uses Yahoo Finance global equivalents (CBOT for Soybean, NY Cotton for Cotton) and localized web scrapers to gather precise signals via `fetch_ncdex_futures`.

### C. Macro-Economic & Global Markets (CBOT & USD/INR)
-   **What it does:** Ingests Chicago Board of Trade prices and foreign exchange rates.
-   **Why it matters:** Indian Soybean meal exports live or die by the USD exchange rate and Brazilian/US harvests. If global Soybean crashes, Indian ports stop buying, leading to a local glut 15 days later.
-   **Mechanics:** Loaded via `macro_loader.py`. 

### D. Government Policy Overrides (NAFED / DGFT)
-   **What it does:** Scrapes government portals for Minimum Export Price (MEP) bans, import tariff cuts, or strategic NAFED buying.
-   **Why it matters:** Machine learning cannot predict surprise government decrees. An overnight export ban immediately orphans the domestic supply.
-   **Mechanics:** Handled by `DgftScraper` and `NafedScraper`. If an export ban is detected, it acts as a "Hard Rule" in the Decision engine, instantly overriding ML models to issue a RED alert.

## 3. Data Flow

1.  Background cron jobs (`run_pipeline.py`) wake up hourly.
2.  Live spot prices and NCDEX data are retrieved.
3.  Stored historical data is fetched from Supabase (or offline SQLite cache if offline).
4.  Data is merged into a single comprehensive Pandas DataFrame, ready for the Feature Engineering layer.
