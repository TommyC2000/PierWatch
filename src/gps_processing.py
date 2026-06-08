from __future__ import annotations

import numpy as np
import pandas as pd


MOVEMENT_COLUMNS = [
    "event_id",
    "event_year",
    "pier_id",
    "pre_longitudinal_in",
    "post_longitudinal_in",
    "longitudinal_movement_in",
    "pre_transverse_in",
    "post_transverse_in",
    "transverse_movement_in",
    "pre_sample_count",
    "post_sample_count",
    "baseline_source",
    "data_availability",
]


def _valid_samples(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    valid = df.dropna(subset=["timestamp", "longitudinal_in", "transverse_in"]).copy()
    valid["date"] = valid["timestamp"].dt.normalize()
    return valid.sort_values("timestamp")


def _window_samples(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return _valid_samples(df[(df["timestamp"] >= start) & (df["timestamp"] <= end)])


def _in_event_fallback_samples(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, sample_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    samples = _valid_samples(df[(df["timestamp"] >= start) & (df["timestamp"] <= end)])
    if samples.empty:
        return samples, samples

    daily = (
        samples.groupby("date", as_index=False)
        .agg(
            timestamp=("timestamp", "min"),
            longitudinal_in=("longitudinal_in", "median"),
            transverse_in=("transverse_in", "median"),
        )
        .sort_values("date")
    )
    return daily.head(sample_days), daily.tail(sample_days)


def _movement_row(event: pd.Series, pier_id: str, pre: pd.DataFrame, post: pd.DataFrame, baseline_source: str) -> dict:
    pre_long = float(pre["longitudinal_in"].median()) if not pre.empty else np.nan
    post_long = float(post["longitudinal_in"].median()) if not post.empty else np.nan
    pre_trans = float(pre["transverse_in"].median()) if not pre.empty else np.nan
    post_trans = float(post["transverse_in"].median()) if not post.empty else np.nan
    has_baseline = pd.notna(pre_long) and pd.notna(post_long) and pd.notna(pre_trans) and pd.notna(post_trans)

    return {
        "event_id": event.get("event_id"),
        "event_year": event.get("event_year"),
        "pier_id": pier_id,
        "pre_longitudinal_in": pre_long,
        "post_longitudinal_in": post_long,
        "longitudinal_movement_in": post_long - pre_long if has_baseline else np.nan,
        "pre_transverse_in": pre_trans,
        "post_transverse_in": post_trans,
        "transverse_movement_in": post_trans - pre_trans if has_baseline else np.nan,
        "pre_sample_count": int(len(pre)),
        "post_sample_count": int(len(post)),
        "baseline_source": baseline_source,
        "data_availability": "Available" if has_baseline else "Insufficient",
    }


def compute_event_movement(
    gps_df: pd.DataFrame,
    events_df: pd.DataFrame,
    pre_window_days: int = 7,
    post_window_days: int = 7,
) -> pd.DataFrame:
    if gps_df.empty or events_df.empty:
        return pd.DataFrame(columns=MOVEMENT_COLUMNS)
    required = {"timestamp", "pier_id", "longitudinal_in", "transverse_in"}
    if not required.issubset(gps_df.columns):
        return pd.DataFrame(columns=MOVEMENT_COLUMNS)

    gps = gps_df.copy()
    gps["timestamp"] = pd.to_datetime(gps["timestamp"], errors="coerce")
    gps["longitudinal_in"] = pd.to_numeric(gps["longitudinal_in"], errors="coerce")
    gps["transverse_in"] = pd.to_numeric(gps["transverse_in"], errors="coerce")
    gps = gps.dropna(subset=["timestamp", "pier_id"])

    rows = []
    for _, event in events_df.iterrows():
        start = pd.to_datetime(event["start_date"]).normalize()
        end = pd.to_datetime(event["end_date"]).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
        pre_start = start - pd.Timedelta(days=pre_window_days)
        pre_end = start - pd.Timedelta(microseconds=1)
        post_start = end + pd.Timedelta(microseconds=1)
        post_end = post_start + pd.Timedelta(days=post_window_days) - pd.Timedelta(microseconds=1)

        for pier_id, pier_data in gps.groupby("pier_id", sort=True):
            pre = _window_samples(pier_data, pre_start, pre_end)
            post = _window_samples(pier_data, post_start, post_end)
            baseline_source = "pre_post_window"

            if pre.empty or post.empty:
                pre, post = _in_event_fallback_samples(pier_data, start, end, 7)
                baseline_source = "in_event_fallback" if not pre.empty and not post.empty else "insufficient_data"

            rows.append(_movement_row(event, pier_id, pre, post, baseline_source))

    return pd.DataFrame(rows, columns=MOVEMENT_COLUMNS)
