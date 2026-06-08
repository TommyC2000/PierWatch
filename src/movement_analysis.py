from __future__ import annotations

import numpy as np
import pandas as pd


COUPLING_COLUMNS = [
    "event_id",
    "event_year",
    "E1_longitudinal_movement_in",
    "E2_longitudinal_movement_in",
    "average_abs_movement_in",
    "coupling_ratio",
    "differential_movement_in",
    "tolerance_in",
    "coupling_status",
    "interpretation",
]

INTERPRETATIONS = {
    "Coupled": "E-1 and E-2 moved with similar magnitude and direction, consistent with the coupled pier movement mechanism described in the engineering documentation.",
    "Stable / Minimal Movement": "The estimated movement is small, so coupling classification is not meaningful for this event.",
    "Not Strongly Coupled": "E-1 and E-2 movement estimates are not strongly coupled for this event, which may indicate event segmentation effects, measurement uncertainty, or different local response.",
    "Insufficient Data": "There is not enough GPS data to evaluate E-1/E-2 coupling for this event.",
    "Not Coupled": "E-1 and E-2 movement estimates have opposite directions and are not coupled for this event.",
}


def _first_movement(group: pd.DataFrame, pier_id: str) -> float:
    pier = group[group["pier_id"].astype(str).str.upper().str.replace("-", "") == pier_id]
    if pier.empty or "longitudinal_movement_in" not in pier.columns:
        return np.nan
    values = pd.to_numeric(pier["longitudinal_movement_in"], errors="coerce").dropna()
    return float(values.iloc[0]) if not values.empty else np.nan


def _classify_coupling(e1_movement: float, e2_movement: float) -> tuple[float, float, float, float, str]:
    if pd.isna(e1_movement) or pd.isna(e2_movement):
        return np.nan, np.nan, np.nan, np.nan, "Insufficient Data"

    average_abs = float((abs(e1_movement) + abs(e2_movement)) / 2.0)
    differential = float(abs(e1_movement - e2_movement))

    if average_abs < 0.1:
        ratio = e1_movement / e2_movement if abs(e2_movement) > 1e-9 else np.nan
        return average_abs, ratio, differential, np.nan, "Stable / Minimal Movement"

    if np.sign(e1_movement) != np.sign(e2_movement):
        ratio = e1_movement / e2_movement if abs(e2_movement) > 1e-9 else np.nan
        return average_abs, ratio, differential, np.nan, "Not Coupled"

    ratio = e1_movement / e2_movement if abs(e2_movement) > 1e-9 else np.nan
    tolerance = float(max(0.5, 0.15 * average_abs))
    if pd.notna(ratio) and 0.8 <= ratio <= 1.2 and differential <= tolerance:
        status = "Coupled"
    else:
        status = "Not Strongly Coupled"
    return average_abs, ratio, differential, tolerance, status


def compute_coupling_metrics(event_movement_df: pd.DataFrame) -> pd.DataFrame:
    if event_movement_df.empty or "event_id" not in event_movement_df.columns:
        return pd.DataFrame(columns=COUPLING_COLUMNS)

    rows = []
    for event_id, group in event_movement_df.groupby("event_id", sort=True):
        e1_movement = _first_movement(group, "E1")
        e2_movement = _first_movement(group, "E2")
        average_abs, ratio, differential, tolerance, status = _classify_coupling(e1_movement, e2_movement)
        event_year = group["event_year"].iloc[0] if "event_year" in group.columns and not group.empty else np.nan

        rows.append(
            {
                "event_id": event_id,
                "event_year": event_year,
                "E1_longitudinal_movement_in": e1_movement,
                "E2_longitudinal_movement_in": e2_movement,
                "average_abs_movement_in": average_abs,
                "coupling_ratio": ratio,
                "differential_movement_in": differential,
                "tolerance_in": tolerance,
                "coupling_status": status,
                "interpretation": INTERPRETATIONS[status],
            }
        )

    return pd.DataFrame(rows, columns=COUPLING_COLUMNS)
