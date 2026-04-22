# -*- coding: utf-8 -*-
"""
Agmarknet Yearly CSV Combiner
==============================
Combines the 'Daily Price Report' yearly CSV files (2021–2026) downloaded
from Agmarknet into a single master CSV.

Input  : kisanalert/data/yearly/*.csv
Output : kisanalert/data/raw/soybean_nanded.csv

Yearly CSV format (12 columns):
  State | District | Market | Commodity Group | Commodity | Variety | Grade |
  Min Price | Max Price | Modal Price | Price Unit | Price Date

The prices are quoted with commas  e.g.  "4,200.00"  → handled automatically.

Categories / Varieties found in Soyabean data:
  - Yellow   (the dominant variety)
  - Other    (unlabelled lots)
  - Black    (rare, occasionally reported)
  (any new variety is captured automatically)

Usage:
    python combine_yearly_csvs.py                  # combine all yearly files
    python combine_yearly_csvs.py --show-varieties  # also print variety table
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT_DIR    = Path(__file__).resolve().parent
YEARLY_DIR  = ROOT_DIR / "data" / "yearly"
OUTPUT_DIR  = ROOT_DIR / "data" / "raw"

# Exact column names after we rename them from the raw header
EXPECTED_RAW_COLS = [
    "state", "district", "market", "commodity_group",
    "commodity", "variety", "grade",
    "min_price", "max_price", "modal_price",
    "price_unit", "date",
]

def standardize_commodity(name: str) -> str:
    n = str(name).strip().lower()
    if n in ["soyabean", "soybean", "soya bean"]: return "Soybean"
    if n in ["cotton", "kapas"]: return "Cotton"
    if n in ["turmeric"]: return "Turmeric"
    return None


def load_arrival_data() -> pd.DataFrame:
    """
    Load and combine all 'Daily Arrival Report' CSVs.
    Returns a DataFrame with columns: date, arrival_qty (sum of all markets per day).
    Arrival unit is Metric Tonnes — kept as-is.
    """
    files = sorted(YEARLY_DIR.rglob("Daily Arrival*.csv"))
    if not files:
        log.warning("No arrival CSVs found in %s — arrival_qty will be 0.", YEARLY_DIR)
        return pd.DataFrame(columns=["date", "arrival_qty"])

    frames = []
    for f in files:
        try:
            df = pd.read_csv(f, header=1, encoding="utf-8", dtype=str)
        except UnicodeDecodeError:
            df = pd.read_csv(f, header=1, encoding="latin-1", dtype=str)

        # Normalise columns
        df.columns = (
            df.columns.str.strip().str.lower()
            .str.replace(r"\s+", "_", regex=True)
            .str.replace(r"[^a-z0-9_]", "", regex=True)
        )
        if "arrival_date" in df.columns:
            df = df.rename(columns={"arrival_date": "date"})

        if "commodity" in df.columns:
            df["commodity"] = df["commodity"].apply(standardize_commodity)
            df = df.dropna(subset=["commodity"])

        if df.empty or "arrival_quantity" not in df.columns:
            continue

        # Parse qty and date
        df["arrival_qty"] = pd.to_numeric(
            df["arrival_quantity"].str.replace(",", "", regex=False).str.strip(),
            errors="coerce"
        ).fillna(0.0)
        df["date"] = pd.to_datetime(
            df["date"].str.strip(), format="%d-%m-%Y", errors="coerce"
        )
        df = df.dropna(subset=["date"])
        frames.append(df[["date", "arrival_qty"]])
        log.info("Arrival: %-65s -> %d rows", f.name, len(df))

    if not frames:
        return pd.DataFrame(columns=["date", "arrival_qty"])

    combined = pd.concat(frames, ignore_index=True)
    if "commodity" not in combined.columns:
        combined["commodity"] = "Soybean" # Fallback if missing
        
    # Sum arrival across all markets per day per crop
    daily = combined.groupby(["date", "commodity"], as_index=False)["arrival_qty"].sum()
    log.info("Arrival data: %d unique dates across crops.", len(daily))
    return daily


def parse_yearly_csv(filepath: Path) -> pd.DataFrame:
    """
    Parse a single 'Daily Price Report' yearly CSV.

    Row 0  : title / report name  → skip
    Row 1  : column headers       → use to build DataFrame
    Row 2+ : data rows            → extract all

    Prices are formatted as  "4,200.00"  — pandas read_csv handles the
    quoting automatically; we only need to strip the embedded commas.
    """
    try:
        # header=1 skips the title row and uses row-1 as column names
        df = pd.read_csv(filepath, header=1, encoding="utf-8", dtype=str)
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, header=1, encoding="latin-1", dtype=str)

    if df.empty:
        log.warning("Empty file: %s", filepath.name)
        return pd.DataFrame()

    # ── normalise column names ───────────────────────────────────────────────
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )

    # Rename "price_date" → "date" if needed
    if "price_date" in df.columns:
        df = df.rename(columns={"price_date": "date"})

    log.debug("Columns in %s: %s", filepath.name, list(df.columns))

    # ── keep only rows for allowed commodities ───────────────────────
    if "commodity" in df.columns:
        df["commodity"] = df["commodity"].apply(standardize_commodity)
        df = df.dropna(subset=["commodity"])
        
        if df.empty:
            log.warning("No valid crop rows in %s", filepath.name)
            return pd.DataFrame()

    # ── strip commas from price columns (e.g. "4,200.00" → "4200.00") ───────
    for col in ["min_price", "max_price", "modal_price"]:
        if col in df.columns:
            df[col] = df[col].str.replace(",", "", regex=False).str.strip()

    # ── select and rename final columns ─────────────────────────────────────
    col_map = {}
    available = set(df.columns)

    for want in EXPECTED_RAW_COLS:
        if want in available:
            col_map[want] = want       # already correctly named

    df = df[list(col_map.keys())].copy()

    log.info("✅  %-70s  →  %d rows", filepath.name, len(df))
    return df


def combine_yearly_files(show_varieties: bool = False) -> pd.DataFrame:
    YEARLY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(YEARLY_DIR.rglob("*.csv"))

    # only process 'Daily Price*' files
    files = [f for f in files if "Daily Price" in f.name]

    if not files:
        log.error("❌ No CSV files found in %s", YEARLY_DIR)
        sys.exit(1)

    log.info("Found %d yearly file(s).", len(files))
    dataframes = []

    for file in files:
        try:
            df = parse_yearly_csv(file)
            if not df.empty:
                dataframes.append(df)
            else:
                log.warning("⚠️   No valid rows from %s", file.name)
        except Exception as exc:
            log.error("❌  Failed to process %s: %s", file.name, exc)

    if not dataframes:
        log.error("No data extracted from any file. Exiting.")
        sys.exit(1)

    master = pd.concat(dataframes, ignore_index=True)

    # ── coerce numeric columns ───────────────────────────────────────────────
    for col in ["min_price", "max_price", "modal_price"]:
        if col in master.columns:
            master[col] = pd.to_numeric(master[col], errors="coerce")

    # ── parse dates  (format: DD-MM-YYYY) ───────────────────────────────────
    master["date"] = pd.to_datetime(
        master["date"].str.strip(), format="%d-%m-%Y", errors="coerce"
    )

    # ── drop rows missing critical values ────────────────────────────────────
    before = len(master)
    master = master.dropna(subset=["date", "modal_price"])
    if len(master) < before:
        log.warning("Dropped %d rows with missing date or modal_price.", before - len(master))

    # ── normalise variety / grade labels ─────────────────────────────────────
    if "variety" in master.columns:
        master["variety"] = (
            master["variety"]
            .str.strip()
            .str.title()
            .fillna("Unknown")
            .replace("", "Unknown")
        )
    if "grade" in master.columns:
        master["grade"] = master["grade"].str.strip().str.upper().fillna("Unknown")

    # ── normalise market / district names ───────────────────────────────────
    if "market" in master.columns:
        master["market"] = master["market"].str.strip()
    if "district" in master.columns:
        master["district"] = master["district"].str.strip()

    # ── arrival_qty: merge real data from arrival CSVs ───────────────────────
    arrivals = load_arrival_data()
    if arrivals.empty:
        master["arrival_qty"] = 0.0
        log.warning("No arrival data found — arrival_qty set to 0.")
    else:
        master = master.merge(arrivals, on=["date", "commodity"], how="left")
        filled = master["arrival_qty"].isna().sum()
        master["arrival_qty"] = master["arrival_qty"].fillna(0.0)
        log.info("Merged arrival_qty: %d rows filled 0", filled)

    # ── final column order ───────────────────────────────────────────────────
    final_cols = [
        "date", "market", "district", "variety", "grade",
        "arrival_qty", "min_price", "max_price", "modal_price",
        "commodity",
    ]
    master = master[[c for c in final_cols if c in master.columns]]

    # ── sort chronologically ─────────────────────────────────────────────────
    master = master.sort_values("date").reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Ensure there is a district column
    if "district" not in master.columns:
        master["district"] = "nanded"
        
    for crop in master["commodity"].unique():
        for dist in master["district"].unique():
            df_slice = master[(master["commodity"] == crop) & (master["district"] == dist)]
            if df_slice.empty:
                continue
                
            district_name = str(dist).lower().replace(" ", "_")
            out_file = OUTPUT_DIR / f"{crop.lower()}_{district_name}.csv"
            df_slice.to_csv(out_file, index=False, encoding="utf-8")
            log.info("Saved %s (%s) -> %s (%d rows)", crop, dist, out_file.name, len(df_slice))

    log.info("━" * 70)
    log.info("🎉  Combined %d file(s)  →  %d total rows", len(dataframes), len(master))
    log.info("    Date range : %s  →  %s",
             master["date"].min().date(), master["date"].max().date())

    # ── variety breakdown ─────────────────────────────────────────────────────
    if "variety" in master.columns:
        variety_summary = (
            master.groupby("variety", sort=False)
            .agg(
                rows      = ("date",        "count"),
                avg_modal = ("modal_price", "mean"),
                avg_min   = ("min_price",   "mean"),
                avg_max   = ("max_price",   "mean"),
                markets   = ("market",      "nunique"),
            )
            .sort_values("rows", ascending=False)
            .reset_index()
        )
        variety_summary["avg_modal"] = variety_summary["avg_modal"].round(0).astype(int)
        variety_summary["avg_min"]   = variety_summary["avg_min"].round(0).astype(int)
        variety_summary["avg_max"]   = variety_summary["avg_max"].round(0).astype(int)

        log.info("━" * 70)
        log.info("📦  Soybean varieties / categories found:\n%s",
                 variety_summary.to_string(index=False))
        log.info("━" * 70)

        if show_varieties:
            print("\n" + "=" * 72)
            print("  SOYBEAN VARIETY / CATEGORY BREAKDOWN")
            print("=" * 72)
            print(variety_summary.to_string(index=False))
            print("=" * 72 + "\n")

    return master


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Combine Agmarknet yearly 'Daily Price Report' CSVs"
    )
    parser.add_argument(
        "--show-varieties", action="store_true",
        help="Print a detailed per-variety/category breakdown."
    )
    args = parser.parse_args()
    combine_yearly_files(show_varieties=args.show_varieties)
