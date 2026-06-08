from __future__ import annotations
import pandas as pd
import numpy as np


EVENT_COLUMNS = [
    "event_id",
    "start_date",
    "end_date",
    "duration_days",
    "min_stage_ft",
    "days_below_12",
    "days_below_7",
    "cumulative_deficit_below_12",
    "cumulative_deficit_below_7",
    "max_drop_rate_ft_per_day",
    "event_year",
    "event_class",
]


def _merge_periods(periods, max_gap_days: int):
    if not periods:
        return []
    merged = [periods[0]]
    for start, end in periods[1:]:
        last_start, last_end = merged[-1]
        gap = (start - last_end).days - 1
        if gap <= max_gap_days:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))
    return merged


def _event_class(days_below_likely: int, days_below_possible: int, min_stage: float, likely_threshold: float) -> str:
    if days_below_likely >= 50 or min_stage <= max(0.0, likely_threshold - 7.0):
        return "Critical / 2022-like"
    if days_below_likely >= 20:
        return "Significant"
    if days_below_likely > 0 or days_below_possible >= 10:
        return "Watch"
    return "Minor"


def detect_low_water_events(
    river_df: pd.DataFrame,
    possible_threshold: float = 12.0,
    likely_threshold: float = 7.0,
    min_event_days: int = 3,
    merge_gap_days: int = 5,
) -> pd.DataFrame:
    if river_df.empty or not {"timestamp", "stage_ft"}.issubset(river_df.columns):
        return pd.DataFrame(columns=EVENT_COLUMNS)

    df = river_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["stage_ft"] = pd.to_numeric(df["stage_ft"], errors="coerce")
    df = df.dropna(subset=["timestamp", "stage_ft"])
    if df.empty:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    df["date"] = pd.to_datetime(df["timestamp"]).dt.normalize()
    daily = df.groupby("date", as_index=False)["stage_ft"].mean().sort_values("date")
    low = daily["stage_ft"] < possible_threshold
    periods = []
    start = None
    prev_date = None
    for date, is_low in zip(daily["date"], low):
        if is_low and start is None:
            start = date
        if start is not None and (not is_low):
            periods.append((start, prev_date))
            start = None
        prev_date = date
    if start is not None:
        periods.append((start, prev_date))
    periods = _merge_periods(periods, merge_gap_days)

    rows = []
    for start, end in periods:
        window = daily[(daily["date"] >= start) & (daily["date"] <= end)].copy()
        duration = (end - start).days + 1
        if duration < min_event_days:
            continue
        days_below_12 = int((window["stage_ft"] < possible_threshold).sum())
        days_below_7 = int((window["stage_ft"] < likely_threshold).sum())
        deficit12 = float(np.maximum(0, possible_threshold - window["stage_ft"]).sum())
        deficit7 = float(np.maximum(0, likely_threshold - window["stage_ft"]).sum())
        daily_drop = -window["stage_ft"].diff()
        max_drop = float(max(0.0, daily_drop.max(skipna=True))) if len(window) > 1 else 0.0
        min_stage = float(window["stage_ft"].min())
        rows.append({
            "start_date": start.date(),
            "end_date": end.date(),
            "duration_days": duration,
            "min_stage_ft": min_stage,
            "days_below_12": days_below_12,
            "days_below_7": days_below_7,
            "cumulative_deficit_below_12": deficit12,
            "cumulative_deficit_below_7": deficit7,
            "max_drop_rate_ft_per_day": max_drop,
            "event_year": int(start.year),
            "event_class": _event_class(days_below_7, days_below_12, min_stage, likely_threshold),
        })

    for idx, row in enumerate(rows, start=1):
        row["event_id"] = f"LW-{idx:03d}"

    return pd.DataFrame(rows, columns=EVENT_COLUMNS)
