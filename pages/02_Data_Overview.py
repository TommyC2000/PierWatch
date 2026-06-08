import pandas as pd
import streamlit as st

from src.config import EXCEL_PATH, DATA_MODE
from src.excel_inspector import inspect_workbook
from src.data_sources import show_mode_banner, is_data_available


@st.cache_data(show_spinner=False)
def cached_inspect_workbook(excel_path: str, file_mtime: float) -> dict:
    return inspect_workbook(excel_path)


def first_rows_dataframe(sheet_info: dict) -> pd.DataFrame:
    rows = []
    for row in sheet_info.get("first_rows", []):
        record = {"row_number": row.get("row_number")}
        for idx, value in enumerate(row.get("values", []), start=1):
            record[f"col_{idx}"] = value
        rows.append(record)
    return pd.DataFrame(rows)


st.title("Data Overview")
st.caption("Engineering Question: What workbook sheets are available, and where do headers appear to begin?")

show_mode_banner()

st.info(
    "**Primary data sources for this prototype:** "
    "The four primary device / monitoring sheets are **W2**, **PP 15**, **E2**, and **E3**. "
    "The primary hydrology record is **River Stage 2000-2026**. "
    "The standalone **GPS Data** sheet is used as the standalone GPS movement source (R1) — "
    "it is not the primary device data table. "
    "Jointmeter data from the four primary device sheets is integrated on the Primary Device Comparison page."
)

if DATA_MODE == "demo":
    st.info("Workbook structure inspection is not available in demo mode. Switch to local mode with the R1 workbook.")
    st.stop()

if not EXCEL_PATH.exists():
    st.error(f"Excel file not found: {EXCEL_PATH}")
    st.stop()

st.write(f"Workbook: `{EXCEL_PATH}`")
info = cached_inspect_workbook(str(EXCEL_PATH), EXCEL_PATH.stat().st_mtime)

if "workbook_error" in info:
    st.error("Workbook inspection failed.")
    st.code(info["workbook_error"])
    st.stop()

sheet_names = info.get("sheet_names", [])
st.metric("Sheets found", len(sheet_names))

summary_rows = []
for sheet_name in sheet_names:
    sheet = info["sheets"].get(sheet_name, {})
    dimensions = sheet.get("dimensions", {})
    summary_rows.append(
        {
            "sheet_name": sheet_name,
            "rows": dimensions.get("max_row"),
            "columns": dimensions.get("max_column"),
            "guessed_header_row": sheet.get("guessed_header_row"),
            "merged_ranges": sheet.get("merged_range_count"),
            "sampled_columns": sheet.get("sampled_column_count"),
            "inspection_error": sheet.get("inspection_error"),
        }
    )

st.subheader("Workbook Structure")
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

selected_sheet = st.selectbox("Inspect sheet", sheet_names)
selected_info = info["sheets"][selected_sheet]

st.subheader(f"First 10 Rows: {selected_sheet}")
if selected_info.get("truncated_columns"):
    st.info(f"Showing the first {selected_info['sampled_column_count']} columns for readability.")
st.dataframe(first_rows_dataframe(selected_info), use_container_width=True, hide_index=True)

with st.expander("Raw inspection metadata", expanded=False):
    st.json(selected_info)

st.info("Milestone 2 only inspects workbook structure. River stage, GPS, and jointmeter parsing are intentionally not run on this page yet.")
