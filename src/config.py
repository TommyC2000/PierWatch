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
# "local" — use real R1 workbook from data/raw/  (private/local use only)
# "demo"  — use sanitized synthetic CSVs from data/demo/ (public portfolio/GitHub)
# To run in demo mode: PIERWATCH_DATA_MODE=demo streamlit run PierWatch.py
_REQUESTED_MODE: str = os.getenv("PIERWATCH_DATA_MODE", "local")
PRIVATE_WORKBOOK_AVAILABLE: bool = EXCEL_PATH.exists()

# Effective mode: fall back to demo when the private workbook is absent so that
# public Streamlit Cloud deployments (where data/raw/ is never present) always
# load synthetic demo data rather than crashing with a missing-file error.
DATA_MODE: str = (
    _REQUESTED_MODE
    if (_REQUESTED_MODE == "demo" or PRIVATE_WORKBOOK_AVAILABLE)
    else "demo"
)

# True when the caller requested local mode but we silently fell back to demo.
DEMO_FALLBACK: bool = (DATA_MODE == "demo") and (_REQUESTED_MODE != "demo")


def load_thresholds(path: Path = THRESHOLDS_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
