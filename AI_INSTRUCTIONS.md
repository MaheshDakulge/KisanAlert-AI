# 🤖 AI Agent Instructions for KisanAlert

Welcome! You are assisting on the **KisanAlert** project, a "Decision Executor" system designed for farmers in Marathwada, India. This project helps farmers decide when to sell their crops (Soybean, Cotton, Turmeric) by predicting price crashes and market trends.

---

## 🎯 Project Core Objective
KisanAlert's goal is to prevent distress selling. Instead of just showing today's prices, it uses ML to provide a **4-Signal Alert System**:
- 🟢 **GREEN**: Safe to Sell (Price near peak/stable).
- 🟡 **AMBER**: Watch & Wait (Uncertainty, wait 2-3 days).
- 🔴 **RED**: Price Crash Warning (Sell immediately or hold if crash is starting).
- 🔵 **BLUE**: Hold for Rise (Price recovery predicted).

---

## 🛠 Tech Stack & Architecture

### Backend (Python/FastAPI) - Location: `/kisanalert`
- **Logic**: `run_pipeline.py` (The brain that orchestrates data loading, training, and prediction).
- **ML Models**: 
  - **XGBoost**: Classification model for price crashes.
  - **LSTM**: Time-series forecasting for 10-day trends.
  - **Ensemble**: Combines models + Rule Engine (NAFED/DGFT policies).
- **Database**: **Supabase** (PostgreSQL) for cloud data; **SQLite** for offline caching.
- **AI**: **Google Gemini 2.0 Flash** for Marathi voice Q&A and advisory generation.

### Frontend (Flutter) - Location: `/kisanalert_app`
- **Platform**: Supports Mobile (Android/iOS) and Web.
- **State Management**: Provider / ChangeNotifier.
- **Charts**: `fl_chart` for price trend visualization.
- **AI Integration**: Calls FastAPI endpoints for Gemini-powered Marathi advice.

---

## 📁 Key Directory Structure

```text
/Agri
├── /kisanalert              # Python Backend
│   ├── api.py               # FastAPI Endpoints (Main Entry)
│   ├── run_pipeline.py      # ML Pipeline Entry
│   ├── /src
│   │   ├── /data            # Data loaders & Scrapers
│   │   ├── /features        # Feature engineering (18 ML features)
│   │   ├── /models          # XGBoost, LSTM logic
│   │   ├── /alerts          # Alert generation & Edge cases
│   │   └── /voice           # Gemini AI Marathi voice logic
│   └── /data                # CSV Datasets (Agmarknet)
└── /kisanalert_app          # Flutter Frontend
    ├── /lib
    │   ├── /screens         # Home, Mandi, Weather, Predict
    │   ├── /state           # App state management
    │   └── /widgets         # Reusable UI components
```

---

## 🚀 How to Help (AI Tasks)

As an AI assistant, you should be ready to:

1.  **Debug the Pipeline**: If `run_pipeline.py` fails, check `src/data/loader.py` for CSV parsing issues or `src/features/engineer.py` for missing feature calculations.
2.  **API Enhancements**: Modify `api.py` to add new endpoints or improve current response structures for the Flutter app.
3.  **UI Iteration**: Help update Flutter screens in `lib/screens/`. Focus on the **Home Screen Hero Card** or the **10-Day Forecast Chart**.
4.  **AI Advisory Tuning**: Refine the Gemini system prompts in `src/voice/gemini_voice.py` or `src/alerts/gemini_marathi.py` to ensure high-quality Marathi advice.
5.  **Data Analysis**: Help analyze the CSVs in `kisanalert/data/` to identify why a certain prediction was made.

---

## 📝 Important Notes for AI
- **Language**: The project heavily uses **Marathi** for user-facing messages. Ensure any new messages follow the existing tone in `src/alerts/alert_engine.py`.
- **Environment**: Backend requires a `.env` file with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `GEMINI_API_KEY`.
- **Offline First**: The app is designed to work with minimal internet. Look into `src/data/cache_db.py` for how offline data is handled.
- **Lead-Lag Logic**: Moat #1 is predicting prices based on nearby hub mandis (e.g., Latur influencing Nanded).

---

## 🛠 Local Development & Testing

If you want to test the project locally, follow these steps:

### 1. Backend (FastAPI)
- **Start Command**: `cd kisanalert && python -m uvicorn api:app --reload`
- **URL**: [http://localhost:8000](http://localhost:8000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

### 2. Frontend (Flutter Web)
- **Development Mode**: `cd kisanalert_app && flutter run -d chrome`
- **Serving Build**: If serving from the `public/` directory:
  - **URL**: [http://localhost:8080](http://localhost:8080)
- **Note**: Ensure the Flutter app is configured to point to `localhost:8000` for API calls during local testing.

---

## 🚢 Deployment Guide (Production)

### 1. Frontend (Flutter Web)
- **Host**: Firebase Hosting (Project: `campusbazaar-84af8`)
- **Action**: Run `Agri/build_and_deploy.ps1` in PowerShell.
- **Process**: Builds the web app -> Copies files to `public/` -> Deploys to Firebase.

### 2. Backend API (FastAPI)
- **Host**: Google Cloud Run (`kisanalert-api`)
- **Region**: `asia-south1`
- **Action**: Run `Agri/kisanalert/deploy.bat`.
- **Environment**: Ensure the script has the correct `PROJECT_ID`. It injects `.env` variables directly during deployment.

### 3. ML Pipeline (Scheduled Jobs)
- **Host**: Google Cloud Run Jobs (`kisanalert-pipeline`)
- **Scheduler**: Google Cloud Scheduler (Triggers at 11:00 AM and 6:00 PM IST).
- **Action**: Run `Agri/kisanalert/deploy_gcp_pipeline.bat`.
- **Purpose**: Runs `run_pipeline.py` automatically to refresh price predictions twice daily.

---

## 📜 Relevant Documentation
- `KisanAlert_Project_Documentation.md`: Full deep dive into architecture.
- `HACKATHON_TECH_STACK.md`: High-level summary.
- `TESTING_GUIDE.md`: How to verify the system.

Good luck! Help the farmer make the right decision! 🌾🚀
