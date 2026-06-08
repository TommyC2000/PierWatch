from __future__ import annotations

import math


DEFAULT_REMAINING_ALLOWABLE_IN = 0.5
MOVEMENT_RATE_PRESETS = {
    "Low": 0.01,
    "Moderate": 0.02,
    "High": 0.05,
    "2022-like": 0.10,
}


def simulate_additional_movement(days_below_7: float, movement_rate_in_per_day: float) -> float:
    days = max(0.0, float(days_below_7 or 0.0))
    rate = max(0.0, float(movement_rate_in_per_day or 0.0))
    return days * rate


def classify_pp15_risk(predicted_additional_movement_in: float, remaining_allowable_in: float) -> str:
    predicted = max(0.0, float(predicted_additional_movement_in or 0.0))
    remaining = float(remaining_allowable_in or 0.0)
    if remaining <= 0:
        return "Span Jacking Likely"

    risk_ratio = predicted / remaining
    if risk_ratio >= 1.0:
        return "Span Jacking Likely"
    if risk_ratio >= 0.8:
        return "Critical"
    if risk_ratio >= 0.5:
        return "Watch"
    return "Normal"


def generate_pp15_recommendation(risk_level: str) -> str:
    return {
        "Normal": "Continue routine monitoring.",
        "Watch": "Increase review frequency during low-water period.",
        "Critical": "Verify PP-15 joint clearance and prepare contingency plan.",
        "Span Jacking Likely": "Coordinate engineering review and consider span-jacking preparation.",
    }.get(risk_level, "Manual engineering review recommended.")


def compute_pp15_risk(
    remaining_allowable_in: float = DEFAULT_REMAINING_ALLOWABLE_IN,
    predicted_additional_movement_in: float = 0.0,
) -> dict:
    predicted = max(0.0, float(predicted_additional_movement_in or 0.0))
    remaining = float(remaining_allowable_in or 0.0)
    risk_level = classify_pp15_risk(predicted, remaining)
    risk_ratio = math.inf if remaining <= 0 else predicted / remaining

    return {
        "remaining_allowable_in": remaining,
        "predicted_additional_movement_in": predicted,
        "remaining_after_scenario_in": remaining - predicted,
        "risk_ratio": risk_ratio,
        "risk_level": risk_level,
        "recommendation": generate_pp15_recommendation(risk_level),
    }
