from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]  # repo root
DATA_RAW = BASE_DIR / "data" / "raw" / "survey.csv"
DATA_PROCESSED = BASE_DIR / "data" / "processed" / "cleaned.parquet"
REPORT_EDA = BASE_DIR / "reports" / "eda_summary.md"
