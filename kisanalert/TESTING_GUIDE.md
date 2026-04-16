# KisanAlert — Complete Manual Testing & Deployment Guide

This guide contains the exact commands you need to run to update the pipeline, handle the data properly, train the machine learning model, and execute the final backend alerts. Every time you download new historical data, you can refer to this document.

---

## 1. Preparing the Data

Whenever you download new `monthly` files from Agmarknet (whether it's for 2019-2022 to cover historical data, or a new month in 2026), you simply place those `.csv` files into `kisanalert/data/raw/monthly/`. 

Once uploaded, you MUST run the combiner script to extract the actual tables and build your master dataset.

**Command to run:**
```powershell
# Run this from the root kisanalert directory
python combine_csvs.py
```

*What this does:* It skips Agmarknet's strange headers, maps the market names to the rows, drops any blank lines, and saves the final flat file as `data/raw/soybean_nanded.csv`.

---

## 2. Checking Data Integrity (Phase 1 Test)

Before training models, it is very good practice to test if the data loader properly normalizes your newly merged dataset.

**Command to run:**
```powershell
python src/data/loader.py
```

*What to expect:* It should output `Phase 1 complete. Final shape: ...` and list that there are absolutely zero Null values.

---

## 3. Training the Machine Learning Model (Phase 1–5)

To predict crashes, the XGBoost model must be fully trained on your historical data. As per your configuration (`config.py`), the model will use Jan 2023–Dec 2024 as training data, and 2025–2026 as validation/testing. 

**Command to run:**
```powershell
python run_pipeline.py --train
```

*What this does:*
1. Cleans the data and engineers the features (like `price_velocity` and `arrival_ratio`).
2. Creates the forward-looking labels (did it crash 15% in the next 7 days?).
3. Trains the `XGBoost` model and saves the trained weights into `models/saved/xgb_v1.json`.
4. Tests the model against 2026 data and outputs its precision and F1 score mathematically.

> **Note:** Only run this when you add a large batch of new historical data. You do not need to retrain the model every single day.

---

## 4. Running the Daily Alert Backend (Phase 6–7)

Once the model is trained, this is the command you (or a cron job / scheduled task) will run **every single day** to actually generate the prediction and alert message for the most recent day in your dataset.

**Command to run:**
```powershell
python run_pipeline.py
```

*What this does:*
1. Loads the very last row of your dataset (treats it as "today").
2. Loads the saved model `xgb_v1.json` from the disk.
3. Generates a crash probability score.
4. Generates a Red, Amber, or Green alert message in Marathi.
5. Saves this alert history to `logs/alerts.json`.

---

### Summary Checklist for Updates
If you download a brand new month of data (e.g., May 2026):
1. Put `may_2026.csv` in `kisanalert/data/raw/monthly/`.
2. Run `python combine_csvs.py`.
3. Run `python run_pipeline.py`.
(No need to retrain the model, just run the daily inference pipeline to generate the alert for the last day of May!)
