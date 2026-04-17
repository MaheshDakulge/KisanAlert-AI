"""
═══════════════════════════════════════════════════════════════════
KisanAlert — CBOT Feature Diagnostic
═══════════════════════════════════════════════════════════════════

Before scraping NCDEX, check if your EXISTING CBOT features are 
actually working. Your diagnostic showed 0% importance — likely 
a bug that's FREE to fix!

Usage:
    python diagnose_cbot.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


class C:
    R = "\033[0m"
    B = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"


def banner(text, color=C.CYAN):
    print(f"\n{color}{C.B}{'═' * 68}{C.R}")
    print(f"{color}{C.B}  {text}{C.R}")
    print(f"{color}{C.B}{'═' * 68}{C.R}\n")


def ok(msg):
    print(f"  {C.GREEN}✓{C.R} {msg}")


def fail(msg):
    print(f"  {C.RED}✗{C.R} {msg}")


def warn(msg):
    print(f"  {C.YELLOW}⚠{C.R} {msg}")


def info(msg):
    print(f"  {C.CYAN}→{C.R} {msg}")


DATA_PATH = "data/processed/features_labeled.csv"

banner("🔬 CBOT Feature Diagnostic — Before You Build NCDEX Scraper")

info(f"Loading {DATA_PATH}")
df = pd.read_csv(DATA_PATH)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)
ok(f"Loaded {len(df):,} rows")


# ═══════════════════════════════════════════════════════════════════
# Check 1: Do CBOT columns exist?
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 1: CBOT columns present?", C.YELLOW)

cbot_columns = [c for c in df.columns if "cbot" in c.lower()]

if not cbot_columns:
    fail("No CBOT columns found!")
    info(f"All columns: {list(df.columns)}")
    sys.exit(1)

ok(f"Found {len(cbot_columns)} CBOT columns: {cbot_columns}")


# ═══════════════════════════════════════════════════════════════════
# Check 2: Are they actually filled with data?
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 2: Data quality per CBOT column", C.YELLOW)

for col in cbot_columns:
    s = df[col]

    non_null = s.notna().sum()
    nulls = s.isna().sum()
    unique = s.nunique()
    stats = s.describe()

    print(f"\n  {C.B}{col}:{C.R}")
    print(f"    Non-null: {non_null:,} / {len(df):,} ({100 * non_null / len(df):.1f}%)")
    print(f"    Nulls:    {nulls:,}")
    print(f"    Unique:   {unique:,}")
    print(f"    Min/Max:  {stats.get('min', 'N/A')} / {stats.get('max', 'N/A')}")
    print(f"    Mean:     {stats.get('mean', 'N/A')}")
    print(f"    Std dev:  {stats.get('std', 'N/A')}")

    # Diagnose issues
    if nulls > len(df) * 0.5:
        fail(f"    >50% NULL — data loader is BROKEN!")
    elif unique == 1:
        fail(f"    Only 1 unique value — CONSTANT, useless to model")
    elif unique < 20:
        warn(f"    Very few unique values ({unique}) — low variance")
    elif s.std() < 0.01 and s.mean() > 10:
        warn(f"    Tiny std dev relative to mean — barely changes")
    else:
        ok(f"    Looks healthy")


# ═══════════════════════════════════════════════════════════════════
# Check 3: Visualize the time series
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 3: Does CBOT actually CHANGE over time?", C.YELLOW)

for col in cbot_columns:
    s = df[col].dropna()
    if len(s) == 0:
        fail(f"{col}: all NaN!")
        continue

    # Sample 10 evenly-spaced values across time
    n_samples = min(10, len(s))
    indices = np.linspace(0, len(s) - 1, n_samples).astype(int)

    print(f"\n  {C.B}{col} over time:{C.R}")
    for idx in indices:
        row_idx = s.index[idx]
        date_val = df.loc[row_idx, "date"]
        val = s.iloc[idx]

        if isinstance(val, (int, float)):
            bar_len = int(abs(val) / 100) if abs(val) > 1 else int(abs(val) * 100)
            bar_len = min(bar_len, 40)
            bar = "█" * bar_len
            print(f"    {date_val.date()}  {val:>10.2f}  {C.CYAN}{bar}{C.R}")


# ═══════════════════════════════════════════════════════════════════
# Check 4: Correlation with modal_price
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 4: Does CBOT correlate with Nanded modal_price?", C.YELLOW)

for col in cbot_columns:
    try:
        corr = df[col].corr(df["modal_price"])
        if pd.isna(corr):
            fail(f"{col}: correlation is NaN (all zeros?)")
        else:
            if abs(corr) > 0.3:
                ok(f"{col}: corr with modal_price = {corr:+.3f} (meaningful)")
            elif abs(corr) > 0.1:
                warn(f"{col}: corr with modal_price = {corr:+.3f} (weak)")
            else:
                fail(f"{col}: corr with modal_price = {corr:+.3f} (essentially zero)")
    except Exception as e:
        fail(f"{col}: error computing correlation - {e}")


# ═══════════════════════════════════════════════════════════════════
# Check 5: Lagged correlations (CBOT leading Nanded by 1-14 days)
# ═══════════════════════════════════════════════════════════════════

banner("CHECK 5: Does CBOT LEAD Nanded prices?", C.YELLOW)

info("Testing if CBOT today correlates with Nanded price 1-14 days AHEAD")

for col in cbot_columns:
    s_cbot = df[col]
    if s_cbot.notna().sum() < 100:
        continue

    print(f"\n  {C.B}{col} → modal_price (future):{C.R}")
    best_lag = None
    best_corr = 0

    for lag in [1, 3, 5, 7, 10, 14]:
        future_price = df["modal_price"].shift(-lag)
        try:
            corr = s_cbot.corr(future_price)
            if pd.notna(corr):
                if abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_lag = lag
                marker = "← best" if abs(corr) > 0.2 else ""
                print(f"    Lag {lag:2d}d: {corr:+.3f}  {marker}")
        except Exception:
            pass

    if best_lag and abs(best_corr) > 0.2:
        ok(f"  Best lag: {best_lag} days with corr={best_corr:.3f}")
    else:
        warn(f"  No strong lagged signal found")


# ═══════════════════════════════════════════════════════════════════
# VERDICT
# ═══════════════════════════════════════════════════════════════════

banner("💊 VERDICT", C.GREEN)

issues = []

for col in cbot_columns:
    s = df[col]
    if s.isna().sum() > len(df) * 0.5:
        issues.append(f"{col} has >50% nulls")
    elif s.nunique() < 10:
        issues.append(f"{col} has <10 unique values")
    elif s.std() < 0.01 * abs(s.mean()) and abs(s.mean()) > 1:
        issues.append(f"{col} has near-zero variance")

if issues:
    print(f"  {C.RED}{C.B}CBOT data is BROKEN:{C.R}")
    for issue in issues:
        print(f"    ✗ {issue}")
    print()
    print(f"  {C.YELLOW}{C.B}Good news: This is a FREE fix!{C.R}")
    print(f"  {C.YELLOW}Check your src/data/macro_loader.py to fix the data source.{C.R}")
    print(f"  {C.YELLOW}No scraping NCDEX needed — just fix the loader!{C.R}")
else:
    print(f"  {C.GREEN}{C.B}CBOT data looks OK.{C.R}")
    print(f"  {C.CYAN}If correlations are weak, CBOT genuinely doesn't help much.{C.R}")
    print(f"  {C.CYAN}Then NCDEX (if you can scrape it) might actually add signal.{C.R}")

print()
