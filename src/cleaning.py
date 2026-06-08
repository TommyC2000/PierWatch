from __future__ import annotations
import pandas as pd
import numpy as np


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().replace("\n", " ").replace("  ", " ") for c in df.columns]
    return df


def clean_timestamp(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
    df = df.dropna(subset=[timestamp_col])
    df = df.sort_values(timestamp_col).drop_duplicates(subset=[timestamp_col])
    return df.reset_index(drop=True)


def parse_timestamp_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def clean_numeric_series(series: pd.Series, invalid_values=None) -> pd.Series:
    if invalid_values is None:
        invalid_values = [-7999, -9999, 9999]
    cleaned = pd.to_numeric(series, errors="coerce")
    return cleaned.replace(invalid_values, np.nan)


def remove_blank_rows(df: pd.DataFrame, required_cols: list[str] | None = None) -> pd.DataFrame:
    df = df.copy()
    if required_cols:
        return df.dropna(subset=required_cols, how="all").reset_index(drop=True)
    return df.dropna(how="all").reset_index(drop=True)


def clean_time_series(df: pd.DataFrame, timestamp_col: str, value_cols: list[str]) -> pd.DataFrame:
    df = remove_blank_rows(df, [timestamp_col, *value_cols])
    df[timestamp_col] = parse_timestamp_series(df[timestamp_col])
    for col in value_cols:
        df[col] = clean_numeric_series(df[col])
    df = df.dropna(subset=[timestamp_col, *value_cols])
    df = df.sort_values(timestamp_col).drop_duplicates(subset=[timestamp_col], keep="first")
    return df.reset_index(drop=True)


def replace_invalid_values(df: pd.DataFrame, invalid_values=None) -> pd.DataFrame:
    df = df.copy()
    if invalid_values is None:
        invalid_values = [-7999, -9999, 9999]
    return df.replace(invalid_values, np.nan)


def remove_unreasonable_values(df: pd.DataFrame, value_cols: list[str], abs_limit: float) -> pd.DataFrame:
    df = df.copy()
    for col in value_cols:
        if col in df.columns:
            df.loc[df[col].abs() > abs_limit, col] = np.nan
    return df


def daily_resample(df: pd.DataFrame, value_cols: list[str], timestamp_col: str = "timestamp", how: str = "median") -> pd.DataFrame:
    if df.empty:
        return df.copy()
    temp = df.copy()
    temp[timestamp_col] = pd.to_datetime(temp[timestamp_col], errors="coerce")
    temp = temp.dropna(subset=[timestamp_col]).set_index(timestamp_col)
    if how == "mean":
        out = temp[value_cols].resample("D").mean()
    else:
        out = temp[value_cols].resample("D").median()
    return out.reset_index()


def calculate_completeness(df: pd.DataFrame, timestamp_col: str = "timestamp", expected_freq: str = "D") -> float:
    if df.empty or timestamp_col not in df.columns:
        return 0.0
    ts = pd.to_datetime(df[timestamp_col], errors="coerce").dropna()
    if ts.empty:
        return 0.0
    expected = pd.date_range(ts.min().normalize(), ts.max().normalize(), freq=expected_freq)
    if len(expected) == 0:
        return 0.0
    actual = ts.dt.normalize().drop_duplicates()
    return min(1.0, len(actual) / len(expected))
