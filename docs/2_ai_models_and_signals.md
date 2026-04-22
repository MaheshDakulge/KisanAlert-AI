# KisanAlert v2.0 - AI Models & Signal Logic

Once raw data is ingested, KisanAlert relies on a sophisticated ML pipeline to predict risk and profitability. This document outlines the Feature Engineering, Model Training, and the final 4-Color Signal Engine.

## 1. Feature Engineering (`src.features.engineer`)
Raw prices are noisy. We transform them into predictive mathematical properties:
-   **Temporal Waves:** We calculate distance to 30-day and 90-day moving averages (MAs) to detect overbought/oversold regimes.
-   **Volatility Bands:** Rolling standard deviations measuring whether price changes are unusually violent.
-   **Lead-Lag (Inter-district):** The pipeline compares prices between Latur and Nanded. If Latur prices drop today, it is highly likely Nanded prices will drop tomorrow. The system calculates a spatial lag score.
-   **NCDEX Signals:** NCDEX Contango Flags and Basis percentages are attached directly to the feature matrix.
-   **Macro Links:** USD/INR exchange ratios and CBOT lagging variations are appended.

## 2. The Predictive Ensemble
We use extreme gradient boosting (XGBoost) due to its superior handling of tabular financial data and immunity to scale discrepancies.

The system utilizes TWO parallel models:
1.  **The Crash Model (`xgb_v3_best.json`):**
    -   *Target:* Detect severe price drops (>7% within upcoming 7-14 days).
    -   *Performance:* **0.7632 Test AUC**. This is highly reliable for agricultural commodities, minimizing false positives.
2.  **The Rise Model (`xgb_blue_signal.json`):**
    -   *Target:* Detect significant upswings allowing farmers to maximize profit by holding.
    -   *Performance:* **0.6972 Test AUC**. Boosted through strict labeling thresholds to provide credible "wait" signals.

*(Note: We originally explored an LSTM neural network, but XGBoost proved far more robust to sudden market regime changes without suffering from data leakage or catastrophic forgetting).*

## 3. The 4-Signal Alert Engine (`src.alerts.alert_engine`)

The physical output of the system is the `classify_signal` function, which maps ML probabilities and market context to four highly deterministic states:

### 🔴 RED (Crash Warning / DO NOT SELL)
**Triggered if:** 
`crash_score >= 0.65` OR `NCDEX backwardation <= -5%`
**Action:** Warns the farmer that the market is about to collapse. Recommends halting all sales immediately.

### 🔵 BLUE (Profit Opportunity / HOLD)
**Triggered if either of two autonomous paths validate:**
1.  **The 48-Hour NCDEX Lead:** `NCDEX contango >= +3%`. Institutional buyers are betting higher. Spot prices *will* follow.
2.  **The ML Pattern:** `rise_score >= 0.60` AND the 7-day trend is strictly rising.
*(Note: BLUE will abort if `crash_score >= 0.35` for safety).*
**Action:** Computes exact expected 48-hour price and tells the farmer exactly how many Rupees/Quintal they will gain by holding onto their crop.

### 🟢 GREEN (Optimal Exit / SELL TODAY)
**Triggered if:**
`at 97% of 30-day peak` AND `crash_score < 0.35`.
**Action:** Notifies the farmer that prices have peaked safely. Optimal time to liquidate inventory.

### 🟡 AMBER (Stable / AT WILL)
**Triggered if:**
No other clear threshold is met. Market is flat.
**Action:** Tells the farmer to sell based purely on personal financial needs rather than market speculation.
