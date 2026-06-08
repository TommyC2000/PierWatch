from __future__ import annotations
import pandas as pd
import numpy as np


def _normalize(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    if s.max() == s.min():
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min()) / (s.max() - s.min())


def compute_low_water_severity(events_df: pd.DataFrame) -> pd.DataFrame:
    df = events_df.copy()
    if df.empty:
        df["LWSI"] = []
        return df
    min_stage_below_7 = (7 - pd.to_numeric(df["min_stage_ft"], errors="coerce")).clip(lower=0)
    df["LWSI"] = (
        0.25 * _normalize(df["days_below_12"]) +
        0.35 * _normalize(df["days_below_7"]) +
        0.25 * _normalize(df["cumulative_deficit_below_7"]) +
        0.15 * _normalize(min_stage_below_7)
    )
    return df
