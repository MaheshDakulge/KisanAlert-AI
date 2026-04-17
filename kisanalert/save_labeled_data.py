"""
═══════════════════════════════════════════════════════════════════
KisanAlert — Generate & Save Labeled Data (FIXED for your pipeline)
═══════════════════════════════════════════════════════════════════

Uses YOUR actual function names:
  ✓ load_clean_data()
  ✓ engineer_features(df)
  ✓ create_labels(df) → (df, class_weight)

Usage:
    python save_labeled_data.py
═══════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import pandas as pd


def log(msg: str, color: str = "") -> None:
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
    }
    c = colors.get(color, "")
    r = colors["reset"]
    print(f"  {c}{msg}{r}")


print("\n" + "═" * 68)
print("  💾 KisanAlert — Generate & Save Labeled Data")
print("═" * 68 + "\n")


log("STEP 1: Importing your pipeline modules", "cyan")

try:
    sys.path.insert(0, ".")

    from src.data.loader import load_clean_data
    log("✓ Imported: load_clean_data", "green")

    from src.features.engineer import engineer_features
    log("✓ Imported: engineer_features", "green")

    from src.features.labels import create_labels
    log("✓ Imported: create_labels", "green")

except ImportError as e:
    log(f"✗ Import failed: {e}", "red")
    log("Check that your src/ folder has __init__.py files", "yellow")
    sys.exit(1)


log("\nSTEP 2: Running your pipeline", "cyan")

try:
    df_clean = load_clean_data()
    log(f"✓ load_clean_data(): {len(df_clean):,} rows × {len(df_clean.columns)} cols", "green")
    log(f"  Columns: {list(df_clean.columns)[:10]}", "")

    df_feat = engineer_features(df_clean)
    log(f"✓ engineer_features(): {len(df_feat):,} rows × {len(df_feat.columns)} cols", "green")

    result = create_labels(df_feat)

    if isinstance(result, tuple):
        df, class_weight = result
        log(f"✓ create_labels(): {len(df):,} rows × {len(df.columns)} cols", "green")
        log(f"  Class weight: {class_weight}", "")
    else:
        df = result
        log(f"✓ create_labels(): {len(df):,} rows × {len(df.columns)} cols", "green")

    if "label" in df.columns:
        crash_rate = df["label"].mean()
        log(f"  Crash rate: {crash_rate*100:.1f}% ({int(df['label'].sum())} crashes / {len(df)} days)", "")
    else:
        log("✗ No 'label' column in output!", "red")
        sys.exit(1)

except Exception as e:
    log(f"✗ Pipeline error: {e}", "red")
    print("\n" + "─" * 68)
    traceback.print_exc()
    print("─" * 68 + "\n")
    sys.exit(1)


log("\nSTEP 3: Saving labeled data", "cyan")

Path("data/processed").mkdir(parents=True, exist_ok=True)
output_path = "data/processed/features_labeled.csv"

df.to_csv(output_path, index=False)
log(f"✓ Saved to: {output_path}", "green")
log(f"  Size: {Path(output_path).stat().st_size // 1024} KB", "")


print("\n" + "═" * 68)
print("  ✅ DONE! Now run the AUC doctor:")
print("═" * 68)
print(f"\n    python auc_doctor.py\n")
print(f"  When prompted for path, type:")
print(f"\n    data/processed/features_labeled.csv\n")
print("═" * 68 + "\n")

print(f"  {len(df):,} rows × {len(df.columns)} columns saved")
if "date" in df.columns:
    print(f"  Date range: {pd.to_datetime(df['date']).min().date()} → "
          f"{pd.to_datetime(df['date']).max().date()}")
print(f"  Crash rate: {df['label'].mean()*100:.1f}%")
feature_cols = [c for c in df.columns if c not in ('date', 'label')][:10]
print(f"  Features (first 10): {feature_cols}")
print()
