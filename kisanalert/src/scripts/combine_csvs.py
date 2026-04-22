# -*- coding: utf-8 -*-
"""
Agmarknet Monthly CSV Combiner  (v2 — with Variety/Category support)
=====================================================================
Combines month-by-month Agmarknet downloads into a single master CSV,
now preserving ALL 6 columns from the raw file:

  Arrival Date  |  Arrivals (MT)  |  Variety  |  Min Price  |  Max Price  |  Modal Price

Soybean varieties found in the data:
  - Yellow   (the main traded variety)
  - Other    (catch-all for unlabelled lots)
  - Black    (occasionally reported)
  - (any new variety is picked up automatically)

The master CSV is written to: kisanalert/data/raw/soybean_nanded.csv

Usage:
    python combine_csvs.py                 # combines all files in data/raw/monthly/
    python combine_csvs.py --show-varieties  # also prints a variety breakdown table
"""

import sys
import argparse
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ROOT_DIR    = Path(__file__).resolve().parent
MONTHLY_DIR = ROOT_DIR / "data" / "raw" / "monthly"
OUTPUT_FILE = ROOT_DIR / "data" / "raw" / "soybean_nanded.csv"

# ── Column names that map to the 6 CSV positions ────────────────────────────
#    pos 0        pos 1           pos 2     pos 3      pos 4      pos 5
COL_NAMES = ["date", "arrival_qty", "variety", "min_price", "max_price", "modal_price"]


def parse_agmarknet_csv(filepath: Path) -> pd.DataFrame:
    """
    Parse a single Agmarknet 'Date-wise Prices' CSV.

    The file has a quirky nested structure:
        Line 0  : title row (skip)
        Line 1  : commodity/state header (skip)
        Line 2  : blank (skip)
        Line 3  : column header row (skip — we use COL_NAMES)
        Line N  : "Market Name : <name>"  → sets current_market
        Line N+ : comma-separated data rows (exactly 6 fields)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1") as f:
            lines = f.readlines()

    parsed_rows = []
    current_market = "Unknown"

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # ── skip metadata / title rows ──────────────────────────────────────
        if (
            line.startswith('"Date Wise Prices')
            or line.startswith('"Commodity :')
            or ("Arrival Date" in line and "Modal Price" in line)   # column header
        ):
            continue

        # ── market sub-header ───────────────────────────────────────────────
        if line.startswith("Market Name :"):
            current_market = line.replace("Market Name :", "").strip().strip('"')
            continue

        # ── data row: must have exactly 6 comma-separated fields ────────────
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) != 6:
            continue  # skip any malformed row silently

        date_val = parts[0]
        # Quick sanity check: dates look like DD/MM/YYYY or YYYY-MM-DD
        if not (len(date_val) >= 8 and ("/" in date_val or "-" in date_val)):
            continue

        parsed_rows.append({
            "date"        : date_val,
            "market"      : current_market,
            "variety"     : parts[2] if parts[2] else "Unknown",
            "arrival_qty" : parts[1],
            "min_price"   : parts[3],
            "max_price"   : parts[4],
            "modal_price" : parts[5],
        })

    if not parsed_rows:
        log.warning("No rows parsed from %s", filepath.name)
        return pd.DataFrame()

    return pd.DataFrame(parsed_rows)


def combine_monthly_files(show_varieties: bool = False) -> pd.DataFrame:
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(MONTHLY_DIR.glob("*.csv"))

    if not files:
        log.error("❌ No CSV files found in %s", MONTHLY_DIR)
        sys.exit(1)

    log.info("Found %d monthly file(s) to combine.", len(files))
    dataframes = []

    for file in files:
        try:
            df = parse_agmarknet_csv(file)
            if not df.empty:
                log.info("✅  %-60s  →  %d rows", file.name, len(df))
                dataframes.append(df)
            else:
                log.warning("⚠️   No valid rows extracted from %s", file.name)
        except Exception as exc:
            log.error("❌  Failed to process %s: %s", file.name, exc)

    if not dataframes:
        log.error("Could not extract any data from any file. Exiting.")
        sys.exit(1)

    master = pd.concat(dataframes, ignore_index=True)

    # ── coerce numeric columns ───────────────────────────────────────────────
    for col in ["modal_price", "min_price", "max_price", "arrival_qty"]:
        master[col] = pd.to_numeric(master[col], errors="coerce")

    # ── drop rows where key fields are missing ───────────────────────────────
    before = len(master)
    master = master.dropna(subset=["modal_price", "arrival_qty", "date"])
    dropped = before - len(master)
    if dropped:
        log.warning("Dropped %d rows with missing price/qty/date.", dropped)

    # ── normalise variety labels (strip whitespace, title-case) ─────────────
    master["variety"] = master["variety"].str.strip().str.title()
    master["variety"] = master["variety"].replace({"": "Unknown", "nan": "Unknown"})

    # ── add commodity / district identifiers ────────────────────────────────
    master["commodity"] = "Soybean"
    master["district"]  = "Nanded"

    # ── final column order ───────────────────────────────────────────────────
    master = master[[
        "date", "market", "variety",
        "arrival_qty", "min_price", "max_price", "modal_price",
        "commodity", "district",
    ]]

    # ── save ─────────────────────────────────────────────────────────────────
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    master.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")

    log.info("━" * 60)
    log.info("🎉  Combined %d file(s) → %d total rows", len(dataframes), len(master))
    log.info("    Saved to : %s", OUTPUT_FILE)

    # ── variety breakdown ────────────────────────────────────────────────────
    variety_summary = (
        master.groupby("variety", sort=False)
        .agg(
            rows       = ("date", "count"),
            avg_modal  = ("modal_price", "mean"),
            avg_min    = ("min_price",   "mean"),
            avg_max    = ("max_price",   "mean"),
            total_qty  = ("arrival_qty", "sum"),
        )
        .sort_values("rows", ascending=False)
        .reset_index()
    )

    log.info("━" * 60)
    log.info("📦  Soybean varieties found:")
    log.info("\n%s", variety_summary.to_string(index=False))
    log.info("━" * 60)

    if show_varieties:
        print("\n" + "═" * 70)
        print("  SOYBEAN VARIETY / CATEGORY BREAKDOWN")
        print("═" * 70)
        print(variety_summary.to_string(index=False))
        print("═" * 70 + "\n")

    return master


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine Agmarknet monthly CSVs")
    parser.add_argument(
        "--show-varieties", action="store_true",
        help="Print a detailed per-variety breakdown after combining."
    )
    args = parser.parse_args()
    combine_monthly_files(show_varieties=args.show_varieties)
