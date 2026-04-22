# KisanAlert v2.0 - Flutter Frontend & AI Delivery

The ultimate goal of KisanAlert is to take billions of data points and translate them into a screen that a rural farmer can understand in 5 seconds. This document covers the Frontend (Flutter) design logic and the off-platform Gemini messaging pipelines.

## 1. The Mobile UX (`home_screen.dart`)

The Flutter application architecture prioritizes visual hierarchy and instantaneous decision-making over raw data tables. The UI is built around the "Decision Engine Paradigm".

### The Hero Decision Card (`_HeroDecisionCard`)
Instead of prioritizing the current price like a standard stock dashboard, the top of the interface is the **AI Alert**.
-   **Color-Coded Backgrounds:** `RED`, `BLUE`, `GREEN`, and `AMBER` states tint the entire top card dynamically using an interpolation class.
-   **Price Spreads:** A standard "Today's Price" is placed next to a "10-Day Forecast" box.
-   **The BLUE Profit Banner:** If the ML model or NCDEX signals a price increase (BLUE state), a specialized visual banner injects the *Exact Expected Profit per Quintal* (e.g., "+₹345 net"). This translates a mathematical prediction into a tangible financial incentive for the farmer to hold.
-   **NCDEX Signal Overlay:** Farmers are also shown the upstream Indian Futures market data so they can see *why* the AI made the decision it did (Trust transparency).

### The Mandi Inter-District Board (`MandiCard`)
Farmers are not restricted to their home district. The UI automatically displays the arbitrage spread between nearby markets (e.g., Nanded vs. Latur vs. Osmanabad). It subtracts an estimated transport/freight cost parameter to output a "Net Gain" score, highlighting the optimal destination.

### Live Architecture (`app_data.dart`, `app_state.dart`)
State management bridges the HTTP payload into strongly typed Dart classes (`CropData`). Refreshing the screen instantly re-polls the `/latest` endpoint, maintaining near real-time synchronized alerts.

## 2. Gemini-Powered Advisory (`whatsapp_notifier.py`, `gemini_voice.py`)

Mobile apps face adoption hurdles in deep rural zones. KisanAlert circumvents the app entirely using autonomous push pipelines.

### The WhatsApp Broadcaster
-   When `run_pipeline.py` executes successfully and triggers an alert change, the backend offloads the payload to the `whatsapp_notifier`.
-   Instead of sending a robotic template, we use **Google Gemini (flash-lite / flash-2.0)** to *write* the WhatsApp message.
-   **Context Injection:** Gemini is fed the current price, the ML crash score, the NCDEX contango expectation, and the 4-color alert level.
-   **Localization:** Gemini translates all of this context into polite, hyper-localized Marathi dialect ("शेतकरी बंधूंनो...").
-   **Fallback Chain:** If the primary Gemini model hits a `RESOURCE_EXHAUSTED` rate limit, the system gracefully falls back to a secondary model, and finally defaults to a hardcoded string template to guarantee message delivery regardless of API quotas.

### Voice & IVR Intelligence
Similar to the text pipeline, voice input (via Flutter microphones or hypothetical Twilio phone lines) is routed to `/voice/ask`. Gemini processes the audio intent, queries the SQL limits, and generates an automated audio response translating the predictive pipeline into a human conversation.
