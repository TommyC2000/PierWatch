from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from .cleaning import clean_time_series, clean_timestamp, replace_invalid_values, standardize_columns


def _read_sheet_raw(excel_path: str, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(excel_path, sheet_name=sheet_name, header=None, engine="openpyxl")


def _find_header_row(raw: pd.DataFrame, keywords: list[str], max_scan: int = 30) -> int:
    keys = [k.lower() for k in keywords]
    for i in range(min(max_scan, len(raw))):
        row_text = " ".join([str(x).lower() for x in raw.iloc[i].dropna().tolist()])
        if all(k in row_text for k in keys):
            return i
    return 0


def _find_column_by_keywords(columns: list[str], keyword_groups: list[tuple[str, ...]]) -> str | None:
    for col in columns:
        normalized = str(col).strip().lower()
        for group in keyword_groups:
            if all(keyword in normalized for keyword in group):
                return col
    return None


def load_river_stage(excel_path: str | Path, sheet_name: str = "River Stage 2000-2026") -> pd.DataFrame:
    """Load long-term river stage data into timestamp/stage_ft columns."""
    raw = _read_sheet_raw(excel_path, sheet_name)
    header = _find_header_row(raw, ["date", "stage"])
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header, engine="openpyxl")
    df = standardize_columns(df)

    columns = list(df.columns)
    timestamp_col = _find_column_by_keywords(
        columns,
        [
            ("date",),
            ("time",),
        ],
    )
    stage_col = _find_column_by_keywords(
        columns,
        [
            ("stage",),
            ("gage",),
            ("ft",),
        ],
    )

    if timestamp_col is None or stage_col is None:
        if len(columns) >= 2:
            timestamp_col = timestamp_col or columns[0]
            stage_col = stage_col or columns[1]
        else:
            raise ValueError(f"Could not identify timestamp and stage columns in sheet {sheet_name!r}: {columns}")

    out = pd.DataFrame(
        {
            "timestamp": df[timestamp_col],
            "stage_ft": df[stage_col],
        }
    )
    return clean_time_series(out, "timestamp", ["stage_ft"])[["timestamp", "stage_ft"]]


def load_gps_data(excel_path: str | Path, sheet_name: str = "GPS Data") -> pd.DataFrame:
    """Load grouped-wide GPS data for E1/E2/E3 into long format."""
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, engine="openpyxl")
    mappings = {
        "E1": (0, 1, 2),
        "E2": (4, 5, 6),
        "E3": (8, 9, 10),
    }
    records = []

    for pier_id, (timestamp_col, longitudinal_col, transverse_col) in mappings.items():
        if raw.shape[1] <= transverse_col:
            continue
        header_value = str(raw.iat[0, timestamp_col]).strip().upper() if pd.notna(raw.iat[0, timestamp_col]) else ""
        if header_value.replace("-", "") != pier_id:
            continue

        block = raw.iloc[1:, [timestamp_col, longitudinal_col, transverse_col]].copy()
        block.columns = ["timestamp", "longitudinal_in", "transverse_in"]
        block["pier_id"] = pier_id
        records.append(block)

    columns = ["timestamp", "pier_id", "longitudinal_in", "transverse_in"]
    if not records:
        return pd.DataFrame(columns=columns)

    out = pd.concat(records, ignore_index=True)
    out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    out["longitudinal_in"] = pd.to_numeric(out["longitudinal_in"], errors="coerce")
    out["transverse_in"] = pd.to_numeric(out["transverse_in"], errors="coerce")
    out = replace_invalid_values(out)
    out = out.dropna(subset=["timestamp", "longitudinal_in", "transverse_in"])
    out = out[columns]
    out = out.sort_values(["pier_id", "timestamp"])
    out = out.drop_duplicates(subset=["pier_id", "timestamp"], keep="first")
    return out.reset_index(drop=True)


def load_pp15_filter(excel_path: str | Path, sheet_name: str = "PP-15 Filter") -> pd.DataFrame:
    """Load PP-15 filtered jointmeter data from the confirmed sheet layout.

    Confirmed layout (3 header rows, data from row 3 onward):
      col 2: combined timestamp (datetime pre-parsed by openpyxl)
      col 3: measured_expansion_in  — Relative Measured Expansion, in
      col 4: temperature_f          — Temperature, F
      col 5: delta_temperature_f    — Delta Temperature, F
      col 6: calculated_expansion_in — Span Length (computed thermal component), in
      col 7: corrected_expansion_in  — Corrected (measured minus calculated), in
    """
    OUTPUT_COLS = [
        "timestamp",
        "measured_expansion_in",
        "temperature_f",
        "delta_temperature_f",
        "calculated_expansion_in",
        "corrected_expansion_in",
    ]
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, engine="openpyxl")
    if len(raw) < 4:
        return pd.DataFrame(columns=OUTPUT_COLS)

    data = raw.iloc[3:].reset_index(drop=True)

    def _safe_numeric(col_idx: int) -> pd.Series:
        if data.shape[1] > col_idx:
            return pd.to_numeric(data.iloc[:, col_idx], errors="coerce")
        return pd.Series(np.nan, index=data.index, dtype=float)

    out = pd.DataFrame({
        "timestamp": pd.to_datetime(data.iloc[:, 2], errors="coerce"),
        "measured_expansion_in": _safe_numeric(3),
        "temperature_f": _safe_numeric(4),
        "delta_temperature_f": _safe_numeric(5),
        "calculated_expansion_in": _safe_numeric(6),
        "corrected_expansion_in": _safe_numeric(7),
    })
    out = replace_invalid_values(out)
    out = out.dropna(subset=["timestamp"])
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="first")
    return out.reset_index(drop=True)


def load_e2_pp15(excel_path: str, sheet_name: str = "E2-PP15") -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name=sheet_name, engine="openpyxl")
    df = standardize_columns(df)
    date_col = next((c for c in df.columns if "time" in c.lower() or "date" in c.lower()), df.columns[0])
    val_col = next((c for c in df.columns if "pp15" in c.lower() or "e2" in c.lower()), df.columns[-1])
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df[date_col], errors="coerce"),
        "e2_pp15_in": pd.to_numeric(df[val_col], errors="coerce"),
    })
    return replace_invalid_values(out).dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)


# ── R1 Primary device sheet loader ────────────────────────────────────────────

_DEVICE_DATA_ROW_START = 8   # 0-indexed: first 8 rows are headers
_SENTINEL_VALUES = [-7999, -9999, -7999.0, -9999.0]


def load_device_sheet(
    excel_path: str | Path,
    sheet_name: str,
    device_id: str,
) -> pd.DataFrame:
    """
    Parse a primary R1 device sheet (W2, PP 15, E2, or E3) into a clean DataFrame.

    R1 confirmed layout (8 header rows; data from iloc[8:]):
    - W2:   col A=Date, col B=Time, col C=measured_expansion_in,
            col D=temperature_f, col E=delta_temperature_f,
            col F=calculated_expansion_in, col G=corrected_expansion_in.
            NO combined timestamp column.
    - PP 15 / E2:  col A=Date, col B=Time, col C=combined_timestamp (USE),
                   col D=measured_expansion_in, col E=temperature_f,
                   col F=delta_temperature_f, col G=calculated_expansion_in,
                   col H=corrected_expansion_in.
    - E3:   same as PP 15/E2, plus:
            col I=calculated_expansion_alt_in (540 ft behavioral span),
            col J=corrected_expansion_alt_in.

    Returns columns: timestamp, device_id, measured_expansion_in,
    temperature_f, delta_temperature_f, calculated_expansion_in,
    corrected_expansion_in [, calculated_expansion_alt_in,
    corrected_expansion_alt_in for E3].
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, engine="openpyxl")
    if len(raw) < 9:
        return pd.DataFrame(columns=["timestamp", "device_id"])

    data = raw.iloc[_DEVICE_DATA_ROW_START:].reset_index(drop=True)

    def _safe_num(col_idx: int) -> pd.Series:
        if data.shape[1] <= col_idx:
            return pd.Series(np.nan, index=data.index, dtype=float)
        s = pd.to_numeric(data.iloc[:, col_idx], errors="coerce")
        for sv in _SENTINEL_VALUES:
            s = s.mask(s == sv, np.nan)
        return s

    is_w2 = (sheet_name == "W2")

    if is_w2:
        # Combine Date (col 0) + Time (col 1) — no pre-combined timestamp column
        date_series = pd.to_datetime(data.iloc[:, 0], errors="coerce")
        time_str = data.iloc[:, 1].astype(str).str.strip()
        # Handle timedelta repr: "0 days 06:00:34" → "06:00:34"
        time_str = time_str.str.replace(r"^\d+ days\s+", "", regex=True)
        ts_combined = date_series.dt.strftime("%Y-%m-%d") + " " + time_str
        timestamps = pd.to_datetime(ts_combined, errors="coerce")
        c_meas, c_temp, c_dtemp, c_calc, c_corr = 2, 3, 4, 5, 6
    else:
        # PP 15, E2, E3: col 2 is the pre-combined timestamp
        timestamps = pd.to_datetime(data.iloc[:, 2], errors="coerce")
        c_meas, c_temp, c_dtemp, c_calc, c_corr = 3, 4, 5, 6, 7

    out = pd.DataFrame({
        "timestamp": timestamps,
        "device_id": device_id,
        "measured_expansion_in": _safe_num(c_meas),
        "temperature_f": _safe_num(c_temp),
        "delta_temperature_f": _safe_num(c_dtemp),
        "calculated_expansion_in": _safe_num(c_calc),
        "corrected_expansion_in": _safe_num(c_corr),
    })

    # E3 only: two additional calculated/corrected columns using 540 ft behavioral span
    if sheet_name == "E3":
        out["calculated_expansion_alt_in"] = _safe_num(8)
        out["corrected_expansion_alt_in"] = _safe_num(9)

    out = replace_invalid_values(out)
    out = out.dropna(subset=["timestamp"])
    out = out.sort_values("timestamp").drop_duplicates(
        subset=["device_id", "timestamp"], keep="first"
    )
    return out.reset_index(drop=True)


def load_all_primary_device_data(excel_path: str | Path) -> pd.DataFrame:
    """Load and combine W2, PP15, E2, E3 primary device sheets into one long-format DataFrame."""
    device_map = [
        ("W2",    "W2"),
        ("PP 15", "PP15"),
        ("E2",    "E2"),
        ("E3",    "E3"),
    ]
    frames = []
    for sheet_name, device_id in device_map:
        try:
            df = load_device_sheet(excel_path, sheet_name, device_id)
            if not df.empty:
                frames.append(df)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame(columns=["timestamp", "device_id"])
    return pd.concat(frames, ignore_index=True)
