from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path


QUALITY_COLUMNS = [
    "source_name",
    "sensor_id",
    "start_time",
    "end_time",
    "record_count",
    "valid_record_count",
    "missing_value_count",
    "missing_value_rate",
    "duplicate_timestamp_count",
    "data_span_days",
    "expected_record_count",
    "completeness_rate",
    "recent_availability_rate",
    "outlier_count",
    "outlier_rate",
    "flatline_count",
    "flatline_rate",
    "noise_indicator",
    "confidence_score",
    "confidence_label",
]

_MIN_RECORDS_FOR_STATS = 10
_FLATLINE_EPS = 1e-6
_IQR_MULTIPLIER = 3.0


def _iqr_outlier_mask(series: pd.Series) -> pd.Series:
    """Return boolean mask of outliers using Q1/Q3 ± 3*IQR."""
    vals = pd.to_numeric(series, errors="coerce")
    valid = vals.dropna()
    if len(valid) < 4:
        return pd.Series(False, index=series.index)
    q1, q3 = float(valid.quantile(0.25)), float(valid.quantile(0.75))
    iqr = q3 - q1
    if iqr == 0:
        return pd.Series(False, index=series.index)
    lo, hi = q1 - _IQR_MULTIPLIER * iqr, q3 + _IQR_MULTIPLIER * iqr
    return (vals < lo) | (vals > hi)


def _flatline_count(series: pd.Series) -> int:
    """Count consecutive repeated values (|diff| < _FLATLINE_EPS)."""
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if len(vals) < 2:
        return 0
    return int((vals.diff().abs() < _FLATLINE_EPS).sum())


def _confidence_label(score: float, valid_record_count: int) -> str:
    if valid_record_count < _MIN_RECORDS_FOR_STATS:
        return "Insufficient Data"
    if np.isnan(score):
        return "Insufficient Data"
    if score >= 0.80:
        return "High"
    if score >= 0.60:
        return "Medium"
    if score >= 0.40:
        return "Low"
    return "Poor"


def compute_series_quality(
    df: pd.DataFrame,
    timestamp_col: str,
    value_cols: list[str],
    source_name: str,
    sensor_id: str | None = None,
    expected_freq: str | None = None,
) -> dict:
    """Compute screening-level data quality metrics for one monitoring data stream.

    Parameters
    ----------
    df : source dataframe (may contain other columns)
    timestamp_col : name of timestamp column
    value_cols : list of numeric value columns to evaluate (usually one)
    source_name : display name for the data source
    sensor_id : optional sub-identifier within the source
    expected_freq : pandas offset string for expected sampling rate ("D", "6h", etc.)
        If None, completeness_rate is computed as valid_record_count / record_count.

    Returns a dict with all QUALITY_COLUMNS as keys.
    """
    _nan = float("nan")
    base = {c: _nan for c in QUALITY_COLUMNS}
    base["source_name"] = source_name
    base["sensor_id"] = sensor_id if sensor_id is not None else source_name
    base["expected_record_count"] = _nan

    # ── Validate columns ─────────────────────────────────────────────────────
    if df.empty or timestamp_col not in df.columns:
        base["record_count"] = 0
        base["valid_record_count"] = 0
        base["confidence_label"] = "Insufficient Data"
        base["confidence_score"] = 0.0
        return base

    present_value_cols = [c for c in value_cols if c in df.columns]
    if not present_value_cols:
        base["record_count"] = len(df)
        base["valid_record_count"] = 0
        base["confidence_label"] = "Insufficient Data"
        base["confidence_score"] = 0.0
        return base

    # ── Parse timestamps ──────────────────────────────────────────────────────
    tmp = df[[timestamp_col] + present_value_cols].copy()
    tmp[timestamp_col] = pd.to_datetime(tmp[timestamp_col], errors="coerce")
    record_count = len(tmp)

    dup_count = int(tmp[timestamp_col].duplicated().sum())
    tmp = tmp.drop_duplicates(subset=[timestamp_col], keep="first")
    tmp = tmp.dropna(subset=[timestamp_col]).sort_values(timestamp_col).reset_index(drop=True)

    if tmp.empty:
        base["record_count"] = record_count
        base["valid_record_count"] = 0
        base["duplicate_timestamp_count"] = dup_count
        base["confidence_label"] = "Insufficient Data"
        base["confidence_score"] = 0.0
        return base

    start_time = tmp[timestamp_col].min()
    end_time = tmp[timestamp_col].max()
    data_span_days = max(0.0, float((end_time - start_time).total_seconds() / 86400))

    # ── Missing values ────────────────────────────────────────────────────────
    for col in present_value_cols:
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce")

    total_cells = len(tmp) * len(present_value_cols)
    missing_value_count = int(sum(tmp[c].isna().sum() for c in present_value_cols))
    missing_value_rate = missing_value_count / max(1, total_cells)

    # valid_record_count = rows where ALL present value_cols are non-NaN
    valid_mask = tmp[present_value_cols].notna().all(axis=1)
    valid_record_count = int(valid_mask.sum())

    # ── Expected count and completeness ──────────────────────────────────────
    expected_record_count = _nan
    if expected_freq is not None and data_span_days >= 1:
        try:
            expected_idx = pd.date_range(
                start_time.normalize(), end_time.normalize(), freq=expected_freq
            )
            expected_record_count = float(len(expected_idx))
        except Exception:
            expected_record_count = _nan

    if not np.isnan(expected_record_count) and expected_record_count > 0:
        completeness_rate = min(1.0, valid_record_count / expected_record_count)
    else:
        completeness_rate = valid_record_count / max(1, record_count)

    # ── Recent availability (relative to dataset end, last 90 days) ──────────
    recent_start = end_time - pd.Timedelta(days=90)
    recent_window = tmp[tmp[timestamp_col] >= recent_start]
    if not recent_window.empty:
        recent_valid = recent_window[present_value_cols].notna().all(axis=1).sum()
        recent_availability_rate = float(recent_valid) / len(recent_window)
    else:
        recent_availability_rate = 0.0

    # ── Outliers (IQR method, 3*IQR threshold) ───────────────────────────────
    outlier_masks = pd.concat(
        [_iqr_outlier_mask(tmp[c]) for c in present_value_cols], axis=1
    )
    outlier_row_mask = outlier_masks.any(axis=1) & valid_mask
    outlier_count = int(outlier_row_mask.sum())
    outlier_rate = outlier_count / max(1, valid_record_count)

    # ── Flatline (primary column only) ───────────────────────────────────────
    primary_col = present_value_cols[0]
    flat_count = _flatline_count(tmp.loc[valid_mask, primary_col])
    flat_rate = flat_count / max(1, valid_record_count)

    # ── Noise indicator (median |first difference| of primary col) ───────────
    primary_vals = tmp.loc[valid_mask, primary_col].reset_index(drop=True)
    noise_indicator = (
        float(primary_vals.diff().abs().median())
        if len(primary_vals) >= 2
        else _nan
    )

    # ── Confidence score ──────────────────────────────────────────────────────
    def _clip(v: float) -> float:
        return float(np.clip(v if not np.isnan(v) else 0.0, 0.0, 1.0))

    confidence_score = (
        0.40 * _clip(completeness_rate)
        + 0.25 * _clip(recent_availability_rate)
        + 0.20 * (1.0 - _clip(outlier_rate))
        + 0.15 * (1.0 - _clip(missing_value_rate))
    )

    label = _confidence_label(confidence_score, valid_record_count)

    return {
        "source_name": source_name,
        "sensor_id": sensor_id if sensor_id is not None else source_name,
        "start_time": start_time,
        "end_time": end_time,
        "record_count": record_count,
        "valid_record_count": valid_record_count,
        "missing_value_count": missing_value_count,
        "missing_value_rate": round(missing_value_rate, 6),
        "duplicate_timestamp_count": dup_count,
        "data_span_days": round(data_span_days, 1),
        "expected_record_count": expected_record_count,
        "completeness_rate": round(completeness_rate, 6),
        "recent_availability_rate": round(recent_availability_rate, 6),
        "outlier_count": outlier_count,
        "outlier_rate": round(outlier_rate, 6),
        "flatline_count": flat_count,
        "flatline_rate": round(flat_rate, 6),
        "noise_indicator": round(noise_indicator, 6) if not np.isnan(noise_indicator) else _nan,
        "confidence_score": round(confidence_score, 4),
        "confidence_label": label,
    }


def compute_all_sensor_quality(excel_path: str | Path) -> pd.DataFrame:
    """Run quality assessment across all implemented data sources.

    Sources evaluated:
      - River Stage (stage_ft, daily)
      - GPS E1/E2/E3 longitudinal and transverse (irregular frequency)
      - PP-15 Filter: measured_expansion_in, temperature_f,
                      calculated_expansion_in, corrected_expansion_in (6h)

    Returns a DataFrame with columns defined in QUALITY_COLUMNS.
    """
    from .data_loader import load_gps_data, load_pp15_filter, load_river_stage

    rows = []

    # River Stage ─────────────────────────────────────────────────────────────
    try:
        river = load_river_stage(excel_path)
        rows.append(
            compute_series_quality(
                river, "timestamp", ["stage_ft"],
                source_name="River Stage", sensor_id="stage_ft",
                expected_freq="D",
            )
        )
    except Exception:
        pass

    # GPS ─────────────────────────────────────────────────────────────────────
    try:
        gps = load_gps_data(excel_path)
        for pier in ["E1", "E2", "E3"]:
            pier_df = gps[gps["pier_id"] == pier].copy()
            for col, label in [("longitudinal_in", "longitudinal"), ("transverse_in", "transverse")]:
                rows.append(
                    compute_series_quality(
                        pier_df, "timestamp", [col],
                        source_name="GPS",
                        sensor_id=f"{pier}_{label}",
                        expected_freq=None,
                    )
                )
    except Exception:
        pass

    # PP-15 Filter ─────────────────────────────────────────────────────────────
    try:
        pp15 = load_pp15_filter(excel_path)
        pp15_streams = [
            ("measured_expansion_in", "PP-15 measured expansion"),
            ("temperature_f", "PP-15 temperature"),
            ("calculated_expansion_in", "PP-15 calculated expansion"),
            ("corrected_expansion_in", "PP-15 corrected expansion"),
        ]
        for col, sid in pp15_streams:
            if col in pp15.columns and pp15[col].notna().any():
                rows.append(
                    compute_series_quality(
                        pp15, "timestamp", [col],
                        source_name="PP-15 Filter",
                        sensor_id=sid,
                        expected_freq="6h",
                    )
                )
    except Exception:
        pass

    # Primary device sheets (W2, PP15, E2, E3) ───────────────────────────────
    from .data_loader import load_device_sheet
    device_stream_map = [
        ("W2",    "W2",   [("measured_expansion_in", "W2 measured expansion"),
                           ("temperature_f",          "W2 temperature"),
                           ("corrected_expansion_in", "W2 corrected expansion")]),
        ("PP 15", "PP15", [("measured_expansion_in", "PP15 measured expansion"),
                           ("temperature_f",          "PP15 temperature"),
                           ("corrected_expansion_in", "PP15 corrected expansion")]),
        ("E2",    "E2",   [("measured_expansion_in", "E2 measured expansion"),
                           ("temperature_f",          "E2 temperature"),
                           ("corrected_expansion_in", "E2 corrected expansion")]),
        ("E3",    "E3",   [("measured_expansion_in", "E3 measured expansion"),
                           ("temperature_f",          "E3 temperature"),
                           ("corrected_expansion_in", "E3 corrected expansion"),
                           ("corrected_expansion_alt_in", "E3 corrected expansion (alt span)")]),
    ]
    for sheet_name, device_id, streams in device_stream_map:
        try:
            dev = load_device_sheet(excel_path, sheet_name, device_id)
            if dev.empty:
                continue
            for col, sid in streams:
                if col in dev.columns and dev[col].notna().any():
                    rows.append(
                        compute_series_quality(
                            dev, "timestamp", [col],
                            source_name="Primary Device",
                            sensor_id=sid,
                            expected_freq="6h",
                        )
                    )
        except Exception:
            pass

    if not rows:
        return pd.DataFrame(columns=QUALITY_COLUMNS)

    result = pd.DataFrame(rows)
    for col in QUALITY_COLUMNS:
        if col not in result.columns:
            result[col] = np.nan
    return result[QUALITY_COLUMNS].reset_index(drop=True)
