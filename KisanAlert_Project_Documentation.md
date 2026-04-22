# KisanAlert v2.0 — Complete Project Documentation
## Google Solution Challenge 2026 | Smart Supply Chains | Build with AI

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Solution Architecture](#3-solution-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Data Pipeline (ML Backend)](#5-data-pipeline-ml-backend)
6. [Machine Learning Models](#6-machine-learning-models)
7. [Feature Engineering](#7-feature-engineering)
8. [Alert System — 4-Signal Engine](#8-alert-system--4-signal-engine)
9. [API Endpoints (FastAPI Backend)](#9-api-endpoints-fastapi-backend)
10. [Flutter Mobile App](#10-flutter-mobile-app)
11. [5 Competitive Moats](#11-5-competitive-moats)
12. [Database Design (Supabase)](#12-database-design-supabase)
13. [Edge Case Handling](#13-edge-case-handling)
14. [Trust Badge System](#14-trust-badge-system)
15. [Gemini AI Voice Integration](#15-gemini-ai-voice-integration)
16. [Competitor Analysis](#16-competitor-analysis)
17. [SDG Alignment](#17-sdg-alignment)
18. [Project Structure](#18-project-structure)
19. [How to Run](#19-how-to-run)
20. [Future Roadmap](#20-future-roadmap)
21. [Team](#21-team)

---

## 1. Project Overview

**Project Name:** KisanAlert — Decision Executor for Marathwada Farmers

**Tagline:** "From Data Provider to Decision Executor"

**Competition:** Google Solution Challenge 2026

**Theme:** Smart Supply Chains / Build with AI

**Core Idea:** KisanAlert is NOT just another agri-tech price information app. It is a **Decision Executor** — it doesn't just show the farmer today's mandi price and weather. It tells the farmer **exactly when to load the truck** to make the most money before a price crash hits.

**Target Region:** Marathwada, Maharashtra, India (8 districts: Nanded, Latur, Osmanabad, Parbhani, Hingoli, Beed, Jalna, Sambhajinagar)

**Target Users:** Smallholder farmers growing Soybean, Cotton, and Turmeric in Marathwada

**Key Statistics:**
- 2,706 farmer suicides in Marathwada in 2024
- 48-hour lead time before price crash detection
- 0G (Zero internet) needed for offline AI mode
- 5 unique competitive moats vs. government and private apps

---

## 2. Problem Statement

### The Crisis
Marathwada is one of the most drought-prone and economically distressed agricultural regions in India. Farmers here face a devastating cycle:

1. **Price Information Gap:** Farmers sell their crops at the local mandi without knowing whether prices are about to crash in the next 2-3 days.
2. **No Crash Prediction:** Existing apps (MahaVISTAAR, BharatAgri, Kisan Suvidha) show TODAY's price but NEVER predict TOMORROW's crash.
3. **Weather-Price Disconnect:** Weather apps and price apps are separate. No app tells farmers: "Rain is coming AND price is currently high → sell NOW before quality loss AND price crash."
4. **Lead-Lag Arbitrage Blindness:** When prices drop in hub mandis (Latur, Vashi), satellite mandis (Nanded, Beed) follow 24-48 hours later. No app warns farmers of this incoming wave.
5. **Connectivity Barriers:** Rural Marathwada has poor 4G. Most apps crash or show "Internet error."

### The Human Cost
When a farmer sells on the wrong day, they lose ₹500–2,000 per quintal. For a 10-quintal load, that's ₹5,000–20,000 lost — often the difference between repaying a loan and defaulting.

---

## 3. Solution Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
│  Agmarknet CSVs │ Open-Meteo API │ CBOT/NCDEX │ NAFED   │
└────────┬─────────────────┬──────────────┬────────────────┘
         │                 │              │
         ▼                 ▼              ▼
┌──────────────────────────────────────────────────────────┐
│              PHASE 1: DATA FOUNDATION                    │
│  loader.py → normalise → parse_dates → filter → reindex │
│  + Lead-Lag merge (surrounding districts)                │
│  + Macro merge (CBOT, USD/INR)                           │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│           PHASE 2: FEATURE ENGINEERING                   │
│  18 ML features: price_trend_30d, msp_gap, drawdown_7,  │
│  arrival_ratio, weather_shock, lead-lag scores,          │
│  CBOT parity, harvest timing, BLUE signal features       │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│           PHASE 3: LABEL CREATION                        │
│  crash_label = 1 if price drops ≥ 7% in next 7 days     │
│  + minimum ₹100 absolute drop (noise filter)             │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│           PHASE 4: ML MODEL LAYER                        │
│  Layer 1: XGBoost (crash_score)     — AUC 0.76           │
│  Layer 2: LSTM (temporal patterns)  — 30-day lookback    │
│  Layer 3: Rule Engine (NAFED/DGFT)  — policy overrides   │
│  Layer 4: BLUE Signal Model         — rise detection     │
│                                                          │
│  Ensemble: 0.60×XGB + 0.30×LSTM + 0.10×Rule             │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│           PHASE 6: ALERT ENGINE (4 Signals)              │
│  🔴 RED    — "Sell TODAY"  (crash imminent, score ≥ 0.65)│
│  🟡 AMBER  — "Watch & Wait" (0.35 ≤ score < 0.65)       │
│  🟢 GREEN  — "Safe to Sell" (score < 0.35, near peak)   │
│  🔵 BLUE   — "Hold for Rise" (rise_score ≥ 0.60)        │
│  + Edge Case Handler (6 fallback scenarios)              │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│           PHASE 8: OUTPUT LAYER                          │
│  → Supabase Cloud DB (daily_alerts table)                │
│  → SQLite Offline Cache (on-device)                      │
│  → FastAPI REST API (real-time access)                   │
│  → Trust Badge (accuracy tracker)                        │
│  → Firebase Push Notifications                           │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│           FLUTTER MOBILE APP                             │
│  🏠 Home Screen (Hero card + 10-day forecast chart)      │
│  📍 Mandi Map (all 8 Marathwada districts)               │
│  🌧 Weather Screen (7-day forecast + crop impact)        │
│  📊 Predict Screen (detailed analysis)                   │
│  👤 Profile Screen (farmer settings)                     │
│  🎤 Voice AI (Marathi conversational Gemini)             │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Tech Stack

### Backend (Python ML Pipeline)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| ML Framework | XGBoost 1.7+ | Crash prediction (classification) |
| Deep Learning | TensorFlow/Keras (LSTM) | Temporal pattern recognition |
| Data Processing | Pandas, NumPy | Data cleaning, feature engineering |
| API Framework | FastAPI + Uvicorn | REST API for mobile app |
| Database | Supabase (PostgreSQL) | Cloud storage for alerts |
| Offline Cache | SQLite | On-device data persistence |
| AI Voice | Google Gemini 2.0 Flash | Marathi conversational AI |
| Web Scraping | BeautifulSoup, Feedparser | Agmarknet data, news RSS |
| Visualization | Matplotlib, Seaborn | Data analysis and reports |

### Frontend (Flutter Mobile App)
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Framework | Flutter 3.x (Dart) | Cross-platform mobile app |
| Charts | fl_chart | Price trend visualization |
| Typography | Google Fonts | Premium UI (Syne, Inter) |
| HTTP Client | http package | API communication |
| Offline DB | sqflite | Local data storage |
| URL Launcher | url_launcher | External links |
| State Mgmt | ChangeNotifier (Provider) | Reactive state management |

### Cloud & DevOps
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Database | Supabase (PostgreSQL + RLS) | Serverless cloud backend |
| Push Notifs | Firebase Cloud Messaging | Daily 8 PM Marathi alerts |
| Weather API | Open-Meteo (free, no key) | 7-day weather forecast |
| AI API | Google Gemini API (free tier) | Voice Q&A in Marathi |
| Data Source | Agmarknet (govt portal) | 5-year historical prices |
| Macro Data | CBOT soybean futures | International price signals |

---

## 5. Data Pipeline (ML Backend)

### Phase 1: Data Foundation (`src/data/loader.py`)

**Input:** Raw Agmarknet CSV files from `data/raw/` and `data/yearly/` directories

**Steps:**
1. **Load Raw CSV** — handles UTF-8/Latin-1 encoding
2. **Normalise Columns** — lowercase, strip whitespace
3. **Parse Dates** — tries 4 date formats (DD/MM/YYYY, YYYY-MM-DD, etc.)
4. **Filter Crop & District** — keeps only target commodity (e.g., Soybean) and district (e.g., Nanded)
5. **Pick Price/Qty Columns** — standardises to `modal_price` and `arrival_qty`
6. **Aggregate Multiple Markets** — averages prices across APMCs, sums arrivals per day
7. **Reindex to Daily** — creates continuous daily time series (2021-01-01 to 2026-04-30), forward-fills gaps
8. **Flag Outliers** — warns about prices > 3× the 30-day rolling median
9. **Validate** — asserts no nulls, monotonic dates, reasonable price range

**Lead-Lag Engine Integration:**
- Automatically finds surrounding district CSVs (e.g., `soybean_latur.csv`, `soybean_hingoli.csv`)
- Merges as `surrounding_price` column (average of all satellite mandis)
- This powers the Lead-Lag Predictive Engine (Moat #1)

**Macro Data Merge:**
- Fetches CBOT soybean futures and USD/INR exchange rate
- Merges historically for ML training features

**Output:** Clean DataFrame with columns: `date`, `modal_price`, `arrival_qty`, `min_price`, `max_price`, `surrounding_price`, `cbot_close`, `usd_inr`, `cbot_weekly_change`

### Phase 2: Feature Engineering (`src/features/engineer.py`)

### Phase 3: Label Creation (`src/features/labels.py`)

**Crash Label Definition:**
- `crash_label = 1` if price drops ≥ 7% within next 7 days
- Minimum absolute drop of ₹100 (filters out noise on low-priced days)
- Historical crash rate: ~18% in training data (2021–2023)

### Phase 4: Model Training (`src/models/xgb_model.py`)

### Phase 6: Alert Generation (`src/alerts/alert_engine.py` + `edge_handler.py`)

### Phase 8: Output (Supabase + SQLite + Trust Badge)

---

## 6. Machine Learning Models

### Model 1: XGBoost Crash Predictor (Primary)

**Purpose:** Predicts the probability of a ≥7% price crash in the next 7 days

**Architecture:**
- XGBClassifier with binary:logistic objective
- max_depth=5, learning_rate=0.04, n_estimators=600
- eval_metric=aucpr (AUC-PR handles severe class imbalance)
- Soft confirmation: 0.7 × today's probability + 0.3 × yesterday's probability

**Training:**
- Training set: 2021–2023 (3 years)
- Validation set: 2024
- Test set: 2025

**Performance:** AUC 0.76 on crash predictions

### Model 2: LSTM Price Forecaster (Layer 2)

**Purpose:** Captures temporal patterns that XGBoost misses

**Architecture:**
- 30-day lookback window
- Keras LSTM with 80 epochs, batch_size=32
- EarlyStopping on val_AUC with patience=12

### Model 3: BLUE Signal Model (Rise Detector)

**Purpose:** Detects price recovery/rise opportunities

**Unique Features (9 additional):**
1. `up_days_streak_7` — consecutive up days in last 7
2. `days_since_low_30` — days since 30-day minimum
3. `bounce_from_low_30` — recovery from 30-day low
4. `price_vs_30d_min` — current price vs 30-day minimum
5. `price_accel_3d` — acceleration of price velocity
6. `price_change_14d` — 14-day price change %
7. `cbot_momentum_7d` — CBOT 7-day momentum
8. `cbot_momentum_14d` — CBOT 14-day momentum
9. `is_recovering` — boolean: price rising from below 7-day MA

**AUC:** 0.70

### Ensemble Formula (v2)

```
final_crash_score = 0.60 × XGBoost + 0.30 × LSTM + 0.10 × Rule Engine
```

**Rule Engine Overrides:**
- NAFED procurement active → force GREEN floor
- DGFT export ban → force RED ceiling
- These override the ML ensemble after scoring

---

## 7. Feature Engineering

18 ML features engineered from raw price and weather data:

| # | Feature Name | Description | Signal |
|---|-------------|-------------|--------|
| 1 | `price_trend_30d` | (price - 30d MA) / 30d MA | Sustained downtrend |
| 2 | `month` | Calendar month (1-12) | Seasonal crash patterns (Oct-Nov) |
| 3 | `msp_gap` | modal_price - MSP | Distress selling zone when negative |
| 4 | `distance_from_min` | price - 7-day rolling minimum | Weak market signal |
| 5 | `trend_strength` | (7d MA - 30d MA) / 30d MA | Trend direction confirmation |
| 6 | `drawdown_7` | (price - 7d max) / 7d max | High-signal crash indicator |
| 7 | `arrival_ratio` | today_arrivals / 7d avg arrivals | Supply flood detection |
| 8 | `price_vs_7d_avg` | price / 7d avg - 1 | Short-term momentum |
| 9 | `rain_7d_sum` | Cumulative rainfall in last 7 days | Weather impact on quality |
| 10 | `temp_7d_avg` | Average temperature last 7 days | Heat stress signal |
| 11 | `is_raining_today` | Binary rainfall flag | Immediate weather impact |
| 12 | `weather_shock_flag` | Extreme weather event detection | Quality risk signal |
| 13 | `year_norm` | (year - 2021) / 5, normalized 0-1 | Temporal regime drift |
| 14 | `surrounding_price` | Avg price of nearby districts | Lead-Lag source signal |
| 15 | `price_wave_lag_score` | (surrounding - local) / local | Inter-district arbitrage |
| 16 | `cbot_price_inr` | CBOT soybean in INR/quintal | International price parity |
| 17 | `cbot_7day_trend` | CBOT weekly % change | International trend direction |
| 18 | `days_from_harvest_start` | Days since harvest season start / 365 | Harvest timing signal |

**Zero-Arrival Crop Handling:**
- For Cotton and Turmeric (no arrival data in yearly CSVs), `arrival_ratio` is replaced by `price_spread_ratio` = (max - min) / modal price as a supply-side proxy.

---

## 8. Alert System — 4-Signal Engine

### Signal Definitions

| Signal | Condition | Action for Farmer | Marathi Message |
|--------|-----------|-------------------|-----------------|
| 🔴 RED | crash_score ≥ 0.65 | "DO NOT sell today! Price crash coming" | "सोयाबीन आज विकू नका! भाव पडण्याची शक्यता आहे." |
| 🟡 AMBER | 0.35 ≤ score < 0.65 | "Watch & wait 2-3 days" | "सावध राहा. पुढील 2-3 दिवस थांबा." |
| 🟢 GREEN | score < 0.35, near peak | "Safe to sell today" | "आज सोयाबीन विकणे सुरक्षित आहे." |
| 🔵 BLUE | rise_score ≥ 0.60, crash < 0.35 | "Hold — price rising soon" | "थांबा — भाव वाढतील." |

### Threshold Configuration
- `ALERT_GREEN_MAX = 0.35` — below this → GREEN
- `ALERT_RED_MIN = 0.65` — above this → RED
- `BLUE_THRESHOLD = 0.60` — rise score above this + low crash → BLUE
- `PEAK_THRESHOLD = 0.97` — price ≥ 97% of 30-day max → GREEN

### Climate-to-Cash Fusion (Moat #2)
The alert engine doesn't just use price. It **merges weather and price into one actionable alert:**

```
Rain forecast 38mm + Price currently at 30d high + Harvest window open
→ COMBINED URGENCY: "Sell immediately — rain will destroy crop AND price will drop"
```

---

## 9. API Endpoints (FastAPI Backend)

### Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check — returns API status |
| GET | `/docs` | Swagger API documentation |
| GET | `/api/v1/alerts/latest` | Latest crash alert for a specific crop+district |
| GET | `/api/v1/alerts/history` | Past N days of alerts (default 7) |
| POST | `/api/v1/pipeline/trigger` | Trigger ML pipeline in background |
| POST | `/api/v1/predict` | Full predict with scraping + policy checks |
| GET | `/api/v1/mandis/compare` | Compare prices across all Marathwada mandis |
| GET | `/api/v1/weather/current` | 7-day weather forecast from Open-Meteo |
| GET | `/api/v1/news` | Agricultural news from RSS feed |
| GET | `/accuracy` | Trust badge accuracy scorecard |
| GET | `/api/v1/forecast/multi-day` | 10-day LSTM price forecast |
| POST | `/api/v1/voice/query` | Gemini Marathi voice Q&A |
| GET | `/api/v1/community/stories` | Community Chopal verified stories |

### Example API Calls

**Get latest alert:**
```
GET /api/v1/alerts/latest?commodity=Soybean&district=Nanded
```

**Response:**
```json
{
  "date": "2026-04-19",
  "commodity": "Soybean",
  "district": "Nanded",
  "price": 5352.0,
  "crash_score": 0.44,
  "rise_score": 0.28,
  "trend_is_rising": false,
  "alert_level": "AMBER",
  "message": "सावध राहा. पुढील 2-3 दिवस थांबा आणि परिस्थिती पाहा."
}
```

**Voice query:**
```
POST /api/v1/voice/query
Body: {"query": "सोयाबीन कधी विकायचे?", "commodity": "Soybean"}
```

**Response:**
```json
{
  "marathi_response": "आजचा भाव ₹5,352 आहे. Signal AMBER आहे — 2-3 दिवस थांबा.",
  "source": "gemini",
  "model": "gemini-2.0-flash"
}
```

---

## 10. Flutter Mobile App

### 5 Main Screens

#### 1. Home Screen (`home_screen.dart`)
- **Hero Alert Card** — shows today's 4-signal alert (RED/AMBER/GREEN/BLUE) with Marathi message
- **10-Day Forecast Chart** — past 7 days (solid green) + next 10 days (dashed blue) using fl_chart
- **Trust Badge** — live accuracy display ("8/10 correct — 80%")
- **Quick Crop Switcher** — toggle between Soybean, Cotton, Turmeric

#### 2. Mandi Map Screen (`mandi_screen.dart`)
- **Interactive SVG Map** — all 8 Marathwada districts plotted
- **Live Prices** — real-time mandi prices with GREEN/AMBER/RED status
- **Distance Information** — km from farmer's home district
- **Ranking** — mandis ranked by lowest crash score

#### 3. Weather Screen (`weather_screen.dart`)
- **7-Day Forecast** — from Open-Meteo API (free, no key)
- **Crop Impact Analysis** — rain risk HIGH/MED/LOW per day
- **Climate-to-Cash Link** — weather alerts fused with price signals

#### 4. Predict Screen (`predict_screen.dart`)
- **Detailed Analysis** — shows full crash/rise score breakdown
- **Pipeline Trigger** — user can manually trigger new prediction
- **NAFED/DGFT Policy Context** — shows government policy impact

#### 5. Profile Screen (`profile_screen.dart`)
- **Farmer Settings** — home district, default crop, language
- **Alert History** — past predictions with correct/incorrect badges
- **App Settings** — notification preferences

### Voice AI Feature
- **Press and Speak** — hold button, speak in Marathi
- **Gemini-Powered** — answers use live market data context
- **Rule-Based Fallback** — works offline when Gemini is unavailable
- **Example:** "लातूर मध्ये उद्या सोयाबीनचा भाव काय असेल?"

---

## 11. 5 Competitive Moats

### Moat 1: Lead-Lag Predictive Engine
**What:** When Latur hub mandi drops today, KisanAlert predicts Nanded satellite mandi will drop 24-48 hours later.

**Tech:** LSTM trained on inter-district price correlations from 5-year Agmarknet history. The `surrounding_price` feature captures the average price of nearby districts, and `price_wave_lag_score` measures the differential.

**Competitors:** Show prices side by side but draw no connection. Farmer must figure it out.

### Moat 2: Climate-to-Cash Risk Logic
**What:** Merges weather forecast + current price + harvest timing into ONE actionable alert.

**Example:** "पाऊस 24 तासांत येणार आणि भाव आत्ता जास्त आहेत — आत्ताच काढा आणि विका"
(Rain in 24hrs + price currently high = harvest and sell immediately)

**Tech:** Rule fusion engine: `rain_forecast_mm × harvest_window_flag × current_price_vs_30day_avg → combined_urgency_score → Gemini generates Marathi action`

### Moat 3: Offline-First Edge Computing
**What:** Works in remote areas (Gadchiroli) with zero 4G signal.

**Tech:** TensorFlow Lite for pest detection (8MB), SQLite offline cache for last 48-hour predictions, Firebase offline persistence for sync.

### Moat 4: Community Chopal
**What:** Peer-to-peer verified success stories from nearby PIN codes.

**Example:** "Dhule Nagnath (Degloor) waited 2 days for Soybean → earned ₹1,800 more" — verified by Agmarknet transaction data.

**Tech:** Firebase Firestore for PIN-code scoped feed, mandi receipt photo verification, Gemini summarizes in Marathi.

### Moat 5: Voice-First Marathi GPT
**What:** Zero learning curve — farmer holds button, speaks in Marathi, gets spoken answer back.

**Tech:** Android SpeechRecognizer (Marathi locale) → Gemini API with live Agmarknet context → TTS in Marathi. Also works as WhatsApp voice note reply.

---

## 12. Database Design (Supabase)

### Table: `daily_alerts`

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT (auto) | Primary key |
| date | DATE | Prediction date |
| commodity | TEXT | Crop name (Soybean, Cotton, Turmeric) |
| district | TEXT | District name (Nanded, Latur, etc.) |
| price | NUMERIC | Modal price in ₹/quintal |
| crash_score | NUMERIC | Ensemble crash probability (0-1) |
| alert_level | TEXT | RED, AMBER, GREEN, or BLUE |
| message | TEXT | Marathi advisory message |
| created_at | TIMESTAMP | Auto-generated timestamp |

**Unique Constraint:** `(date, commodity, district)` — one alert per crop per district per day

### Table: `pipeline_runs`

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT (auto) | Primary key |
| run_date | TIMESTAMP | When pipeline ran |
| status | TEXT | SUCCESS or FAILURE |
| logs | TEXT | Pipeline execution logs |

### Security: Row Level Security (RLS) enabled
- **Read:** Public access (any app can read alerts)
- **Write:** Only via SERVICE_ROLE key (Python pipeline)

---

## 13. Edge Case Handling

The `edge_handler.py` wraps the alert engine with 6 production-safe fallbacks:

| # | Edge Case | Fallback |
|---|-----------|----------|
| 1 | NCDEX market closed (Sunday/holiday) | Use yesterday's cached alert + "Market closed" flag |
| 2 | New farmer (< 3 alerts) | Onboarding mode with safe AMBER signal + educational tips |
| 3 | Data API down / features missing | Use cached alert if < 12 hours old, else AMBER |
| 4 | Prediction too old (> 12 hours) | Trigger re-run + staleness warning |
| 5 | Model confidence very low | Suppress alert — don't spam farmer with noise |
| 6 | Market price missing | Fetch fallback from nearest mandi or AMBER |

### NCDEX Holiday Calendar (2026)
Republic Day (Jan 26), Holi (Mar 6), Ram Navami (Mar 25), Ambedkar Jayanti (Apr 14), Labour Day (May 1), Independence Day (Aug 15), Gandhi Jayanti (Oct 2), Diwali (Oct 24), Children's Day (Nov 14), Christmas (Dec 25)

---

## 14. Trust Badge System

**File:** `src/alerts/trust_badge.py`

### How it works:
1. **Log every prediction** — timestamp, crop, signal, price, crash_score
2. **Wait 7 days** — let the actual price unfold
3. **Verify automatically** — compare predicted signal vs actual price change
4. **Display accuracy** — "Last 30 days: 8/10 correct (80%)"

### Correctness Rules:
- **RED correct** if price dropped ≥ 3%
- **BLUE correct** if price rose ≥ 3%
- **GREEN correct** if price dropped ≤ 2% (selling was smart)
- **AMBER correct** if price changed < 3% (stable)

### Display in App:
| Accuracy | Badge | Marathi Label |
|----------|-------|---------------|
| ≥ 80% | ⭐⭐⭐⭐⭐ | उत्कृष्ट (Excellent) |
| ≥ 70% | ⭐⭐⭐⭐ | चांगले (Good) |
| ≥ 60% | ⭐⭐⭐ | समाधानकारक (Satisfactory) |
| < 60% | ⭐⭐ | शिकत आहोत (Learning) |

---

## 15. Gemini AI Voice Integration

**File:** `src/voice/gemini_voice.py`

### Architecture:
1. Farmer speaks in Marathi → Android SpeechRecognizer
2. Text sent to `/api/v1/voice/query` endpoint
3. Live context fetched from Supabase (latest price + signal)
4. Gemini 2.0 Flash generates Marathi response with market context
5. Response read back via TTS

### System Prompt (sent to Gemini):
- Always respond in Marathi (Devanagari)
- Keep under 3 sentences
- Mention specific prices (₹) and mandis
- Focus on actionable advice: sell, hold, or wait
- NEVER make up prices

### Rule-Based Fallback (when Gemini API is unavailable):
Handles 7 query categories offline:
1. MSP queries → returns exact MSP with comparison
2. Sell/buy queries → uses current signal (RED/GREEN/BLUE)
3. Price queries → returns today's price
4. Weather queries → redirects to weather tab
5. NAFED queries → explains procurement impact
6. Mandi queries → suggests nearby alternatives
7. Default → returns current price + signal

---

## 16. Competitor Analysis

| Feature | MahaVISTAAR (Govt) | BharatAgri | Kisan Suvidha | KisanAlert v2 |
|---------|-------------------|-----------|---------------|---------------|
| Today's mandi price | ✓ | ✓ | ✓ | ✓ |
| Weather forecast | ✓ | ✓ (3 days) | ✓ (5 days) | ✓ (7 days) |
| Price crash prediction | ✗ | ✗ | ✗ | ✓ (1/3/7 day) |
| Lead-Lag arbitrage | ✗ | ✗ | ✗ | ✓ Inter-district |
| Climate-to-Cash alert | ✗ (separate tabs) | ✗ | ✗ | ✓ Single fused |
| Offline AI | ✗ (app breaks) | ✗ | ✗ | ✓ TFLite on-device |
| Community verified stories | ~ Basic | ✗ | ✗ | ✓ Chopal feed |
| Voice AI in Marathi | ~ Hindi only | ✗ | ✗ | ✓ Gemini |
| Interactive Mandi Map | ~ Static list | ✗ | ~ Text only | ✓ Interactive map |
| Compare all mandis | ✗ | ✗ | ✗ | ✓ 8 districts |
| Hyper-local model | ✗ (state-level) | ✗ (national) | ✗ | ✓ Nanded-specific |
| WhatsApp alerts | ✗ | ~ Limited | ✗ | ✓ 8 PM daily |
| **Fundamental role** | Data provider | Input seller | Data provider | **Decision Executor** |

---

## 17. SDG Alignment

| SDG | How KisanAlert Contributes |
|-----|--------------------------|
| **SDG 1: No Poverty** | Prevents ₹5,000-20,000 losses per transaction by warning about price crashes |
| **SDG 2: Zero Hunger** | Helps farmers make better selling decisions, securing their income for food |
| **SDG 8: Decent Work** | Reduces distress selling that forces farmers into debt cycles |
| **SDG 9: Innovation** | LSTM + XGBoost ensemble AI applied to rural agriculture |
| **SDG 10: Reduced Inequalities** | Voice-first Marathi AI makes technology accessible to semi-literate farmers |
| **SDG 13: Climate Action** | Climate-to-Cash fusion helps farmers adapt to weather shocks |

---

## 18. Project Structure

```
KisanAlert-AI/
├── kisanalert/                     # 🧠 ML Backend (Python)
│   ├── api.py                      # FastAPI server (13 endpoints)
│   ├── config.py                   # Central configuration
│   ├── run_pipeline.py             # Main ML pipeline runner
│   ├── src/
│   │   ├── data/
│   │   │   ├── loader.py           # Phase 1: Data foundation
│   │   │   ├── cache_db.py         # SQLite offline cache
│   │   │   ├── macro_loader.py     # CBOT/USD data fetcher
│   │   │   └── weather_loader.py   # Open-Meteo weather data
│   │   ├── features/
│   │   │   ├── engineer.py         # Phase 2: 18 ML features
│   │   │   ├── labels.py           # Phase 3: Crash labels
│   │   │   └── weather_features.py # Weather feature engineering
│   │   ├── models/                 # XGBoost, LSTM, ensemble
│   │   ├── alerts/
│   │   │   ├── alert_engine.py     # 4-signal alert generator
│   │   │   ├── edge_handler.py     # 6 edge case fallbacks
│   │   │   ├── trust_badge.py      # Accuracy tracking system
│   │   │   └── gemini_marathi.py   # Gemini Marathi prompts
│   │   ├── forecasting/
│   │   │   └── multi_day_forecast.py # 10-day LSTM forecast
│   │   ├── voice/
│   │   │   └── gemini_voice.py     # Gemini AI voice Q&A
│   │   ├── pipeline/
│   │   │   ├── scrapers.py         # Agmarknet/NAFED/DGFT scrapers
│   │   │   └── firebase_sync.py    # Push notification sync
│   │   └── supabase_client.py      # Cloud DB client
│   ├── data/
│   │   ├── raw/                    # Raw Agmarknet CSVs per district
│   │   ├── yearly/                 # Yearly combined CSVs
│   │   ├── processed/              # Feature-engineered data
│   │   └── cache/                  # Offline alert cache + trust badge log
│   ├── models/saved/               # Trained model files (.json, .keras)
│   └── requirements.txt            # Python dependencies
│
├── kisanalert_app/                 # 📱 Flutter Mobile App
│   ├── lib/
│   │   ├── main.dart               # App entry point
│   │   ├── data/app_data.dart      # Data models + API service
│   │   ├── state/app_state.dart    # Reactive state management
│   │   ├── screens/
│   │   │   ├── home_screen.dart    # Hero card + forecast chart
│   │   │   ├── mandi_screen.dart   # Interactive mandi map
│   │   │   ├── weather_screen.dart # Weather + crop impact
│   │   │   ├── predict_screen.dart # Detailed analysis
│   │   │   └── profile_screen.dart # Farmer settings
│   │   ├── theme/                  # App theme & colors
│   │   └── widgets/                # Shared UI components
│   ├── pubspec.yaml                # Flutter dependencies
│   └── android/ ios/ web/          # Platform-specific code
│
├── supabase_setup.sql              # Database schema
├── requirements.txt                # Root Python requirements
└── kisanalert_v2 (2).html          # Interactive dashboard mockup
```

---

## 19. How to Run

### Prerequisites
- Python 3.11+
- Flutter 3.x (for mobile app)
- Supabase account (free tier)
- (Optional) Gemini API key for voice AI

### Backend Setup
```bash
# 1. Install dependencies
cd kisanalert
pip install -r requirements.txt

# 2. Create .env file
copy .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY

# 3. Setup database
# Run supabase_setup.sql in Supabase SQL Editor

# 4. Train models (first time only)
python run_pipeline.py --train

# 5. Start API server
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000

# 6. Run daily predictions
python run_pipeline.py
```

### Flutter App Setup
```bash
cd kisanalert_app
flutter pub get
flutter run -d chrome   # for web
flutter run              # for connected device
```

### Environment Variables (.env)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_ANON_KEY=your-anon-key
GEMINI_API_KEY=your-gemini-key
```

---

## 20. Future Roadmap

### v3.0 (Planned)
- **Real-time Agmarknet scraping** — automated daily data ingestion
- **Multi-state expansion** — Vidarbha, Western Maharashtra, Karnataka
- **Commodity futures integration** — NCDEX live API
- **WhatsApp Business API** — automated daily alerts at 8 PM
- **Regional language support** — Hindi, Kannada, Telugu

### v4.0 (Vision)
- **Satellite imagery integration** — crop health monitoring via Sentinel-2
- **Yield prediction** — combine weather + satellite for yield forecasting
- **Direct mandi booking** — book trader slots from the app
- **Microfinance connection** — connect farmers with crop insurance

---

## 21. Team

**Team Name:** KisanAlert Team

**Competition:** Google Solution Challenge 2026

**University:** [Your University Name]

---

*Document generated on: April 19, 2026*
*Version: 2.0*
*For Google Solution Challenge 2026 Judges*
