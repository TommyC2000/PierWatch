from __future__ import annotations

import numpy as np
import pandas as pd


SENSITIVITY_COLUMNS = [
    "event_id",
    "event_year",
    "start_date",
    "end_date",
    "duration_days",
    "min_stage_ft",
    "days_below_12",
    "days_below_7",
    "cumulative_deficit_below_7",
    "depth_below_7",
    "LWSI",
    "E1_longitudinal_movement_in",
    "E2_longitudinal_movement_in",
    "E1_movement_per_day_below_7",
    "E2_movement_per_day_below_7",
    "E1_movement_per_cumulative_deficit_below_7",
    "E2_movement_per_cumulative_deficit_below_7",
    "E1_movement_per_LWSI",
    "E2_movement_per_LWSI",
]


def _normalize(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0)
    min_value = values.min()
    max_value = values.max()
    denominator = max_value - min_value
    if denominator == 0:
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    return (values - min_value) / denominator


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce").replace(0, np.nan)
    return numerator / denominator


def compute_low_water_severity_index(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        out = events_df.copy()
        out["depth_below_7"] = []
        out["LWSI"] = []
        return out

    df = events_df.copy()
    df["days_below_12"] = pd.to_numeric(df["days_below_12"], errors="coerce")
    df["days_below_7"] = pd.to_numeric(df["days_below_7"], errors="coerce")
    df["cumulative_deficit_below_7"] = pd.to_numeric(df["cumulative_deficit_below_7"], errors="coerce")
    df["min_stage_ft"] = pd.to_numeric(df["min_stage_ft"], errors="coerce")
    df["depth_below_7"] = (7.0 - df["min_stage_ft"]).clip(lower=0)
    df["LWSI"] = (
        0.25 * _normalize(df["days_below_12"])
        + 0.35 * _normalize(df["days_below_7"])
        + 0.25 * _normalize(df["cumulative_deficit_below_7"])
        + 0.15 * _normalize(df["depth_below_7"])
    )
    return df


def _pivot_e1_e2_movement(event_movement_df: pd.DataFrame) -> pd.DataFrame:
    if event_movement_df.empty:
        return pd.DataFrame(columns=["event_id", "event_year", "E1_longitudinal_movement_in", "E2_longitudinal_movement_in"])

    movement = event_movement_df.copy()
    movement["pier_id"] = movement["pier_id"].astype(str).str.upper().str.replace("-", "")
    movement = movement[movement["pier_id"].isin(["E1", "E2"])]
    if movement.empty:
        return pd.DataFrame(columns=["event_id", "event_year", "E1_longitudinal_movement_in", "E2_longitudinal_movement_in"])

    pivot = (
        movement.pivot_table(
            index=["event_id", "event_year"],
            columns="pier_id",
            values="longitudinal_movement_in",
            aggfunc="mean",
        )
        .rename(columns={"E1": "E1_longitudinal_movement_in", "E2": "E2_longitudinal_movement_in"})
        .reset_index()
    )
    return pivot


def compute_movement_sensitivity(events_df: pd.DataFrame, event_movement_df: pd.DataFrame) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame(columns=SENSITIVITY_COLUMNS)

    severity = compute_low_water_severity_index(events_df)
    movement = _pivot_e1_e2_movement(event_movement_df)
    df = severity.merge(movement, on=["event_id", "event_year"], how="left")

    for pier in ["E1", "E2"]:
        movement_col = f"{pier}_longitudinal_movement_in"
        if movement_col not in df.columns:
            df[movement_col] = np.nan
        df[f"{pier}_movement_per_day_below_7"] = _safe_divide(df[movement_col], df["days_below_7"])
        df[f"{pier}_movement_per_cumulative_deficit_below_7"] = _safe_divide(
            df[movement_col],
            df["cumulative_deficit_below_7"],
        )
        df[f"{pier}_movement_per_LWSI"] = _safe_divide(df[movement_col], df["LWSI"])

    for col in SENSITIVITY_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    return df[SENSITIVITY_COLUMNS]
