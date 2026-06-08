from __future__ import annotations

import numpy as np
import pandas as pd


def device_availability_summary(all_device_df: pd.DataFrame) -> pd.DataFrame:
    """
    Screening-level data availability summary for each primary device.

    Returns one row per device_id with columns:
    device_id, sheet_name, start_time, end_time, record_count,
    temperature_min_f, temperature_max_f, temperature_missing_rate,
    measured_expansion_min_in, measured_expansion_max_in, measured_expansion_missing_rate,
    corrected_expansion_min_in, corrected_expansion_max_in, corrected_expansion_missing_rate.
    """
    if all_device_df.empty:
        return pd.DataFrame()

    SHEET_MAP = {"W2": "W2", "PP15": "PP 15", "E2": "E2", "E3": "E3"}
    rows = []

    for device_id, grp in all_device_df.groupby("device_id", sort=True):
        rec: dict = {
            "device_id": device_id,
            "sheet_name": SHEET_MAP.get(device_id, device_id),
            "start_time": grp["timestamp"].min(),
            "end_time": grp["timestamp"].max(),
            "record_count": len(grp),
        }
        for col, label in [
            ("temperature_f", "temperature"),
            ("measured_expansion_in", "measured_expansion"),
            ("corrected_expansion_in", "corrected_expansion"),
        ]:
            if col in grp.columns and grp[col].notna().any():
                vals = grp[col].dropna()
                rec[f"{label}_min"] = float(vals.min())
                rec[f"{label}_max"] = float(vals.max())
                rec[f"{label}_missing_rate"] = float(grp[col].isna().mean())
            else:
                rec[f"{label}_min"] = np.nan
                rec[f"{label}_max"] = np.nan
                rec[f"{label}_missing_rate"] = np.nan
        rows.append(rec)

    return pd.DataFrame(rows).reset_index(drop=True)


def latest_device_snapshot(all_device_df: pd.DataFrame) -> pd.DataFrame:
    """
    Most recent reading for each primary device.

    Returns one row per device_id with the latest timestamp and key measurement values.
    """
    if all_device_df.empty:
        return pd.DataFrame()

    rows = []
    for device_id, grp in all_device_df.groupby("device_id", sort=True):
        valid = grp.dropna(subset=["timestamp"]).sort_values("timestamp")
        if valid.empty:
            continue
        last = valid.iloc[-1]
        rows.append({
            "device_id": device_id,
            "latest_timestamp": last["timestamp"],
            "latest_measured_expansion_in": last.get("measured_expansion_in", np.nan),
            "latest_temperature_f": last.get("temperature_f", np.nan),
            "latest_corrected_expansion_in": last.get("corrected_expansion_in", np.nan),
            "latest_delta_temperature_f": last.get("delta_temperature_f", np.nan),
        })

    return pd.DataFrame(rows).reset_index(drop=True)


def event_window_device_comparison(
    all_device_df: pd.DataFrame,
    events_df: pd.DataFrame,
    event_id: str,
    pre_days: int = 7,
    post_days: int = 7,
) -> pd.DataFrame:
    """
    For a selected low-water event, compute pre/post device expansion statistics.

    Returns one row per device_id with columns:
    device_id, event_id, event_data_count,
    pre_event_median_corrected_in, post_event_median_corrected_in, event_change_corrected_in,
    pre_event_median_measured_in, post_event_median_measured_in, event_change_measured_in,
    data_quality_note.
    """
    if all_device_df.empty or events_df.empty:
        return pd.DataFrame()

    ev_row = events_df[events_df["event_id"] == event_id]
    if ev_row.empty:
        return pd.DataFrame()

    ev = ev_row.iloc[0]
    start = pd.Timestamp(ev["start_date"])
    end = pd.Timestamp(ev["end_date"])
    pre_start = start - pd.Timedelta(days=pre_days)
    post_end = end + pd.Timedelta(days=post_days)

    def _median(df: pd.DataFrame, col: str) -> float:
        if col not in df.columns or df.empty:
            return np.nan
        v = df[col].dropna()
        return float(v.median()) if not v.empty else np.nan

    rows = []
    for device_id, grp in all_device_df.groupby("device_id", sort=True):
        pre = grp[(grp["timestamp"] >= pre_start) & (grp["timestamp"] < start)]
        post = grp[(grp["timestamp"] > end) & (grp["timestamp"] <= post_end)]
        ev_win = grp[(grp["timestamp"] >= start) & (grp["timestamp"] <= end)]

        pre_corr = _median(pre, "corrected_expansion_in")
        post_corr = _median(post, "corrected_expansion_in")
        pre_meas = _median(pre, "measured_expansion_in")
        post_meas = _median(post, "measured_expansion_in")

        if not (np.isnan(pre_corr) or np.isnan(post_corr)):
            delta_corr = post_corr - pre_corr
        else:
            delta_corr = np.nan

        if not (np.isnan(pre_meas) or np.isnan(post_meas)):
            delta_meas = post_meas - pre_meas
        else:
            delta_meas = np.nan

        if len(ev_win) == 0:
            note = "No device data in event window"
        elif len(pre) == 0 and len(post) == 0:
            note = "No pre/post window data"
        elif len(pre) == 0:
            note = "No pre-event window data"
        elif len(post) == 0:
            note = "No post-event window data"
        else:
            note = "OK"

        rows.append({
            "device_id": device_id,
            "event_id": event_id,
            "event_data_count": int(len(ev_win)),
            "pre_event_median_corrected_in": pre_corr,
            "post_event_median_corrected_in": post_corr,
            "event_change_corrected_in": delta_corr,
            "pre_event_median_measured_in": pre_meas,
            "post_event_median_measured_in": post_meas,
            "event_change_measured_in": delta_meas,
            "data_quality_note": note,
        })

    return pd.DataFrame(rows).reset_index(drop=True)


def yearly_device_summary(
    all_device_df: pd.DataFrame,
    low_temp_percentile: float = 25.0,
) -> pd.DataFrame:
    """
    Yearly statistics per device for screening-level comparison.

    Returns columns:
    device_id, year, record_count,
    median_corrected_expansion_in, min_corrected_expansion_in, max_corrected_expansion_in,
    median_temperature_f,
    low_temperature_median_corrected_in, high_temperature_median_corrected_in.
    """
    if all_device_df.empty:
        return pd.DataFrame()

    df = all_device_df.copy()
    df["year"] = df["timestamp"].dt.year

    rows = []
    for (device_id, year), grp in df.groupby(["device_id", "year"], sort=True):
        rec: dict = {"device_id": device_id, "year": int(year), "record_count": int(len(grp))}

        for col in ["corrected_expansion_in", "temperature_f"]:
            if col not in grp.columns or not grp[col].notna().any():
                for stat in ["median", "min", "max"]:
                    rec[f"{stat}_{col}"] = np.nan
                continue
            vals = grp[col].dropna()
            rec[f"median_{col}"] = float(vals.median())
            rec[f"min_{col}"] = float(vals.min())
            rec[f"max_{col}"] = float(vals.max())

        # Low/high temperature median corrected expansion
        if (
            "temperature_f" in grp.columns
            and "corrected_expansion_in" in grp.columns
        ):
            valid = grp.dropna(subset=["temperature_f", "corrected_expansion_in"])
            if len(valid) >= 4:
                lo_thresh = float(valid["temperature_f"].quantile(low_temp_percentile / 100))
                hi_thresh = float(valid["temperature_f"].quantile(1 - low_temp_percentile / 100))
                lo_grp = valid[valid["temperature_f"] <= lo_thresh]["corrected_expansion_in"]
                hi_grp = valid[valid["temperature_f"] >= hi_thresh]["corrected_expansion_in"]
                rec["low_temperature_median_corrected_in"] = float(lo_grp.median()) if not lo_grp.empty else np.nan
                rec["high_temperature_median_corrected_in"] = float(hi_grp.median()) if not hi_grp.empty else np.nan
            else:
                rec["low_temperature_median_corrected_in"] = np.nan
                rec["high_temperature_median_corrected_in"] = np.nan
        else:
            rec["low_temperature_median_corrected_in"] = np.nan
            rec["high_temperature_median_corrected_in"] = np.nan

        rows.append(rec)

    return pd.DataFrame(rows).reset_index(drop=True)
