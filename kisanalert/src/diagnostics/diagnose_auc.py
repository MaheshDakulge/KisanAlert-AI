# -*- coding: utf-8 -*-
"""
Diagnostic: Check label distribution per year and real AUC on test set.
Run: python diagnose_auc.py
"""
import sys
sys.path.insert(0, ".")
import config
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score

config.TARGET_COMMODITY = "Soybean"

from src.data.loader import load_clean_data
from src.data.weather_loader import get_weather_data
from src.features.engineer import engineer_features
from src.features.labels import create_labels
from src.models.xgb_model import load_model, split_data, get_xy

print("Loading data...")
df = load_clean_data()
dw = get_weather_data()
df = pd.merge(df, dw, on="date", how="left")
df["rain_mm"] = df["rain_mm"].fillna(0.0)
df["temp_max_c"] = df["temp_max_c"].fillna(30.0)
df = engineer_features(df)
df, cw = create_labels(df)

print("\n--- LABEL DISTRIBUTION BY YEAR ---")
by_year = df.groupby(df["date"].dt.year)["label"].agg(
    crashes="sum", total="count", rate="mean"
)
print(by_year.to_string())

train, val, test = split_data(df)
print(f"\nTrain  label rate : {train['label'].mean():.3f}  ({train['label'].sum()} crashes / {len(train)} days)")
print(f"Val    label rate : {val['label'].mean():.3f}  ({val['label'].sum()} crashes / {len(val)} days)")
print(f"Test   label rate : {test['label'].mean():.3f}  ({test['label'].sum()} crashes / {len(test)} days)")

print("\nLoading model...")
model = load_model()
X_test, y_test = get_xy(test)
proba = model.predict_proba(X_test)[:, 1]

print(f"\nProb stats -> min: {proba.min():.3f}  max: {proba.max():.3f}  mean: {proba.mean():.3f}")

unique_classes = np.unique(y_test)
print(f"Unique labels in test set: {unique_classes}  (need both 0 and 1 for AUC)")

if len(unique_classes) < 2:
    print("AUC: NOT COMPUTABLE — only one class present in test set!")
    print(">>> ROOT CAUSE: Test year has zero crash events. Model cannot be AUC-evaluated.")
else:
    auc = roc_auc_score(y_test, proba)
    print(f"AUC-ROC: {auc:.4f}")
    if auc < 0.65:
        print(">>> LOW AUC DETECTED. Checking for regime shift...")
        # Compare train vs test crash rate
        if abs(train["label"].mean() - test["label"].mean()) > 0.10:
            print(f">>> REGIME SHIFT: train crash rate={train['label'].mean():.2%}  test crash rate={test['label'].mean():.2%}")
            print("    Model trained on different market dynamics than it is being tested on.")
        if proba.max() < 0.5:
            print(">>> MODEL SUPPRESSED: max probability is below 0.5 — model never fires RED.")
            print("    Likely cause: scale_pos_weight too low, or label imbalance not balanced.")

# Feature importances
print("\n--- FEATURE IMPORTANCES (if base XGBoost) ---")
try:
    base = model  # might be calibrated
    if hasattr(model, "base_estimator"):
        base = model.base_estimator
    elif hasattr(model, "calibrated_classifiers_"):
        base = model.calibrated_classifiers_[0].estimator
    imps = dict(zip(get_xy(train)[0].columns, base.feature_importances_))
    for feat, imp in sorted(imps.items(), key=lambda x: -x[1]):
        print(f"  {feat:<25} {imp:.4f}")
except Exception as e:
    print(f"  Could not extract importances: {e}")
