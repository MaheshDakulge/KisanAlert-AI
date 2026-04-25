# KisanAlert AI - Hackathon Technical Documentation

## 🚀 Project Overview
KisanAlert AI is a real-time decision-support system for farmers. It uses Machine Learning to predict crop prices and Generative AI to provide actionable advice, helping farmers decide when to sell their produce for maximum profit.

---

## 🛠 The Tech Stack

### 1. Frontend (The User Interface)
- **Framework:** **Flutter Web**
- **Language:** Dart
- **Key Features:**
  - Responsive Dashboard with real-time price cards.
  - Interactive charts for 10-day price forecasting.
  - Multi-language support (Marathi & English).
  - Google Maps integration for Mandi location tracking.
- **Web Fix:** Optimized for browser by bypassing mobile-only dependencies (`sqflite`, `path_provider`) to ensure 100% uptime on the web.

### 2. Backend (The Brain)
- **Framework:** **FastAPI (Python)**
- **Host:** **Render** (Auto-scaled cloud environment).
- **Core Logic:**
  - Handles real-time API requests from the Flutter frontend.
  - Integrates with **Google Gemini Pro** to generate "AI Advisory" messages in Marathi.
  - Implements **Prophet/ML Models** for price prediction.
  - **CORS Configured:** To allow secure communication between Firebase Hosting and Render.

### 3. Database (The Memory)
- **Provider:** **Supabase (PostgreSQL)**
- **Data Tables:**
  - `daily_alerts`: Stores real-time prices, crash scores, and alert levels.
  - `mandi_prices`: Stores comparison data across different APMCs.
  - `farmer_profiles`: Handles login and user statistics.

### 4. AI & Data Intelligence
- **LLM:** **Google Gemini API** (Used for analyzing market trends and providing context-aware advice).
- **Forecasting:** Time-series analysis for 10-day price predictions.
- **Alert System:** 
  - **GREEN:** High price, Sell Now.
  - **AMBER:** Stable, Hold.
  - **RED:** Price Crash Warning, Sell Immediately or wait for recovery.

---

## 🔄 Data Flow (How it works)
1. **Request:** The Flutter Web app sends an HTTPS request to the FastAPI backend (e.g., `/alerts/latest?commodity=Soybean`).
2. **Processing:** The Backend queries **Supabase** for historical data and **External APIs** for live market rates.
3. **AI Enhancement:** The backend passes this raw data to **Gemini AI** to generate a human-friendly advisory in Marathi.
4. **Response:** Backend returns a optimized **JSON** response.
5. **Display:** Flutter parses the JSON and updates the UI instantly (Price, Chart, Alert Dot).

---

## ☁️ Deployment Architecture
- **Web Hosting:** **Firebase Hosting** (Chosen for fast global CDN and SSL security).
- **Backend Hosting:** **Render** (Connected via Git for CI/CD).
- **Deployment Script:** A custom PowerShell script (`build_and_deploy.ps1`) automates the 3-step process:
  1. `flutter build web` (Compiles code to optimized JS).
  2. `robocopy` (Mirrors the build to the public directory).
  3. `firebase deploy` (Pushes the live update to the URL).

---

## 🌟 Key Innovations for Judges
- **Edge Compatibility:** Fixed common "MissingPluginException" in Flutter Web by implementing platform-aware code.
- **Low Latency:** Optimized API calls with extended timeouts (45s) to handle cloud "cold starts" effectively.
- **Actionable AI:** Not just raw data, but AI-driven decisions (Sell/Hold) tailored to local languages.

---
**Live URL:** [https://kisanalert-ai.web.app](https://kisanalert-ai.web.app)
**Backend API:** [https://kisanalert-ai.onrender.com](https://kisanalert-ai.onrender.com)
