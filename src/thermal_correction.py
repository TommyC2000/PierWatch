from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


_MIN_ROWS = 5

YEARLY_COMPARISON_COLUMNS = [
    "year",
    "record_count",
    "temperature_threshold_f",
    "median_temperature_f",
    "median_corrected_expansion_in",
    "mean_corrected_expansion_in",
    "min_corrected_expansion_in",
    "max_corrected_expansion_in",
]


def compute_linear_thermal_correction(
    df: pd.DataFrame,
    movement_col: str,
    temperature_col: str,
) -> tuple[pd.DataFrame, dict]:
    """Fit movement = slope * temperature + intercept and return residuals.

    Returns (corrected_df, stats_dict).

    corrected_df gains two columns:
      predicted_thermal_movement_in   — model-predicted thermal component
      thermal_corrected_residual_in   — movement minus prediction

    stats_dict keys: slope, intercept, r_squared, record_count, status.
    When fewer than _MIN_ROWS valid rows are present, prediction columns are
    NaN and status is 'insufficient_data'.
    """
    stats: dict = {
        "slope": np.nan,
        "intercept": np.nan,
        "r_squared": np.nan,
        "record_count": 0,
        "status": "insufficient_data",
    }

    out = df.copy()
    out["predicted_thermal_movement_in"] = np.nan
    out["thermal_corrected_residual_in"] = np.nan

    if movement_col not in out.columns or temperature_col not in out.columns:
        stats["status"] = f"missing_column ({movement_col!r} or {temperature_col!r} not found)"
        return out, stats

    valid = out[movement_col].notna() & out[temperature_col].notna()
    n = int(valid.sum())
    stats["record_count"] = n

    if n < _MIN_ROWS:
        stats["status"] = f"insufficient_data (need >= {_MIN_ROWS}, got {n})"
        return out, stats

    X = out.loc[valid, temperature_col].values.reshape(-1, 1)
    y = out.loc[valid, movement_col].values
    model = LinearRegression().fit(X, y)

    out.loc[valid, "predicted_thermal_movement_in"] = model.predict(X)
    out.loc[valid, "thermal_corrected_residual_in"] = (
        out.loc[valid, movement_col] - out.loc[valid, "predicted_thermal_movement_in"]
    )

    stats.update(
        slope=float(model.coef_[0]),
        intercept=float(model.intercept_),
        r_squared=float(model.score(X, y)),
        status="ok",
    )
    return out, stats


def compare_low_temperature_windows(
    df: pd.DataFrame,
    temperature_col: str,
    corrected_col: str,
    temp_percentile: float = 10,
) -> pd.DataFrame:
    """Year-over-year comparison of corrected expansion under similar low-temperature conditions.

    Selects records at or below the given temperature percentile across all years,
    then summarises by year. Supports screening-level interpretation only; does not
    fully isolate structural movement from other sources of variance.

    Returns a DataFrame with columns defined in YEARLY_COMPARISON_COLUMNS.
    """
    empty = pd.DataFrame(columns=YEARLY_COMPARISON_COLUMNS)

    tmp = df.copy()
    required = {"timestamp", temperature_col, corrected_col}
    if tmp.empty or not required.issubset(tmp.columns):
        return empty
    tmp["timestamp"] = pd.to_datetime(tmp["timestamp"], errors="coerce")
    tmp = tmp.dropna(subset=["timestamp", temperature_col, corrected_col])
    if tmp.empty:
        return empty

    threshold = float(tmp[temperature_col].quantile(temp_percentile / 100))
    low = tmp[tmp[temperature_col] <= threshold].copy()
    if low.empty:
        return empty

    low["year"] = low["timestamp"].dt.year
    summary = low.groupby("year", as_index=False).agg(
        record_count=(corrected_col, "count"),
        median_temperature_f=(temperature_col, "median"),
        median_corrected_expansion_in=(corrected_col, "median"),
        mean_corrected_expansion_in=(corrected_col, "mean"),
        min_corrected_expansion_in=(corrected_col, "min"),
        max_corrected_expansion_in=(corrected_col, "max"),
    )
    summary.insert(2, "temperature_threshold_f", round(threshold, 3))
    return summary[YEARLY_COMPARISON_COLUMNS]
