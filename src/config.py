import os
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_DEMO = ROOT_DIR / "data" / "demo"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
DATA_REFERENCE = ROOT_DIR / "data" / "reference"
EXCEL_PATH = DATA_RAW / "Jointmeters w GPS R1.xlsx"
REPORT_PATH = DATA_RAW / "Pier_Monitoring_Report_private.docx"
THRESHOLDS_PATH = DATA_REFERENCE / "engineering_thresholds.yaml"

# DATA_MODE controls which data source the app uses.
# "local" — use real R1 workbook from data/raw/  (default, private/local use only)
# "demo"  — use sanitized synthetic CSVs from data/demo/ (for public portfolio/GitHub)
# To run in demo mode: PIERWATCH_DATA_MODE=demo streamlit run app.py
DATA_MODE: str = os.getenv("PIERWATCH_DATA_MODE", "local")


def load_thresholds(path: Path = THRESHOLDS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
