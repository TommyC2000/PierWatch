from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_river_stage_data, get_gps_data, get_pp15_filter_data, get_sensor_quality_data,
)
from src.event_detection import detect_low_water_events
from src.gps_processing import compute_event_movement
from src.movement_analysis import compute_coupling_metrics
from src.pp15_risk import MOVEMENT_RATE_PRESETS, compute_pp15_risk, simulate_additional_movement
from src.river_stage import compute_low_water_severity
from src.sensitivity_model import compute_movement_sensitivity
from src.summary_generator import generate_engineering_summary
from src.thermal_correction import compute_linear_thermal_correction

_mode, _ck_path, _ck_mtime = source_cache_key()

st.title("Engineering Summary Generator")
st.caption(
    "Compile PierWatch screening-level monitoring outputs into a concise professional summary."
)

show_mode_banner()

st.markdown(
    """
This page brings together low-water event detection, GPS pier movement, E-1/E-2 coupling
analysis, PP-15 joint clearance risk screening, year-to-year movement sensitivity,
PP-15 thermal correction context, and sensor confidence into a single engineering monitoring
summary for the selected event and scenario.

**Important.** PierWatch is a monitoring-based decision-support prototype for
engineering-informed SHM analytics. It is not a complete digital twin and does not
replace field measurements, structural analysis, bridge inspection, or engineering judgment.
All outputs are screening-level interpretations only.
"""
)

# ── Guard ─────────────────────────────────────────────────────────────────────

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()

# ── Cached loaders ────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False)
def _load_events(mode: str, path: str, mt: float) -> pd.DataFrame:
    river = get_river_stage_data()
    return compute_low_water_severity(detect_low_water_events(river))


@st.cache_data(show_spinner=False)
def _load_movement(mode: str, path: str, mt: float) -> pd.DataFrame:
    events = _load_events(mode, path, mt)
    gps = get_gps_data()
    return compute_event_movement(gps, events) if not gps.empty else pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_coupling(mode: str, path: str, mt: float) -> pd.DataFrame:
    movement = _load_movement(mode, path, mt)
    return compute_coupling_metrics(movement) if not movement.empty else pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_sensitivity(mode: str, path: str, mt: float) -> pd.DataFrame:
    river = get_river_stage_data()
    events_raw = detect_low_water_events(river)
    movement = _load_movement(mode, path, mt)
    return compute_movement_sensitivity(events_raw, movement)


@st.cache_data(show_spinner=False)
def _load_thermal_stats(mode: str, path: str, mt: float) -> dict:
    pp15 = get_pp15_filter_data()
    if pp15.empty or "measured_expansion_in" not in pp15.columns:
        return {"status": "no_data", "r_squared": None, "slope": None,
                "intercept": None, "record_count": 0}
    _, stats = compute_linear_thermal_correction(pp15, "measured_expansion_in", "temperature_f")
    return stats


@st.cache_data(show_spinner=False)
def _load_sensor_quality_summary(mode: str, path: str, mt: float) -> dict:
    q = get_sensor_quality_data()
    if q.empty:
        return {}
    lc = q["confidence_label"].value_counts()
    return {
        "n_high": int(lc.get("High", 0)),
        "n_medium": int(lc.get("Medium", 0)),
        "n_low": int(lc.get("Low", 0)),
        "n_poor": int(lc.get("Poor", 0)),
        "n_insufficient": int(lc.get("Insufficient Data", 0)),
        "n_total": len(q),
        "avg_confidence_score": float(q["confidence_score"].mean()),
    }


events = _load_events(_mode, _ck_path, _ck_mtime)
movement_df = _load_movement(_mode, _ck_path, _ck_mtime)
coupling_df = _load_coupling(_mode, _ck_path, _ck_mtime)
sensitivity_df = _load_sensitivity(_mode, _ck_path, _ck_mtime)
thermal_stats = _load_thermal_stats(_mode, _ck_path, _ck_mtime)
sensor_quality_summary = _load_sensor_quality_summary(_mode, _ck_path, _ck_mtime)

if events.empty:
    st.warning("No low-water events detected. Check that the river stage data is loaded.")
    st.stop()

# ── Sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader("Event and scenario controls")

    # Event selector
    event_labels = (
        events["event_id"].astype(str)
        + " ("
        + events["event_year"].astype(str)
        + ") — "
        + events["event_class"].astype(str)
    ).tolist()
    # Default to most recent GPS-era event
    gps_era = events[events["event_year"] >= 2022]
    default_idx = (
        events.index.get_loc(gps_era.index[-1]) if not gps_era.empty else len(events) - 1
    )
    selected_label = st.selectbox(
        "Select event",
        options=event_labels,
        index=default_idx,
        key="m10_event_select",
        help="Select the low-water event to summarize. GPS movement data is only available for events from June 2022 onward.",
    )
    st.caption(
        "Recommended: **LW-050** for the most complete demo (largest movement, full coupling record). "
        "**LW-058** for recent monitoring context."
    )
    selected_event_id = selected_label.split(" ")[0]

    st.markdown("---")
    st.subheader("PP-15 risk scenario")

    remaining_allowable = st.number_input(
        "Remaining allowable movement (in)",
        min_value=0.01,
        max_value=5.0,
        value=0.5,
        step=0.05,
        key="m10_remaining",
        help=(
            "Approximate remaining longitudinal movement allowance before another span-jacking "
            "operation may need to be considered. Default 0.5 in is based on source monitoring documentation."
        ),
    )
    scenario_days = st.slider(
        "Additional days below 7 ft",
        min_value=0,
        max_value=90,
        value=10,
        key="m10_days",
        help="Scenario assumption for continued low-water exposure used for the PP-15 risk screening calculation.",
    )
    rate_preset = st.selectbox(
        "Movement rate preset",
        options=list(MOVEMENT_RATE_PRESETS.keys()) + ["Custom"],
        index=1,
        key="m10_rate_preset",
        help=(
            "Assumed movement rate for PP-15 scenario screening. "
            "The 2022-like rate (~0.10 in/day) is based on reported peak movement of approximately 1 inch every 10 days."
        ),
    )
    if rate_preset == "Custom":
        movement_rate = st.number_input(
            "Custom rate (in/day)",
            min_value=0.001,
            max_value=1.0,
            value=0.02,
            step=0.005,
            format="%.3f",
            key="m10_custom_rate",
        )
    else:
        movement_rate = MOVEMENT_RATE_PRESETS[rate_preset]

    st.markdown("---")
    st.subheader("Optional sections")

    include_sensitivity = st.checkbox("Year-to-year sensitivity context", value=True, key="m10_sens",
                                      help="Include LWSI and movement sensitivity comparison context if available.")
    include_thermal = st.checkbox("Thermal correction context", value=True, key="m10_therm",
                                  help="Include PP-15 thermal correction context from the PP-15 Filter analysis, if available.")
    include_quality = st.checkbox("Sensor confidence", value=True, key="m10_qual",
                                  help="Include screening-level data quality context for implemented monitoring streams.")
    include_disclaimer = st.checkbox("Include disclaimer", value=True, key="m10_disc",
                                     help="Append a screening-level disclaimer reminding readers that this is not an official engineering report.")

# ── Assemble inputs for the selected event ────────────────────────────────────

event_row_df = events[events["event_id"] == selected_event_id]
if event_row_df.empty:
    st.error(f"Event {selected_event_id} not found.")
    st.stop()

event_row = event_row_df.iloc[0].to_dict()

# Movement rows for the selected event
sel_movement = (
    movement_df[movement_df["event_id"] == selected_event_id]
    if not movement_df.empty
    else pd.DataFrame()
)
movement_rows: list[dict] | None = (
    sel_movement.to_dict("records") if not sel_movement.empty else None
)

# Coupling row
if not coupling_df.empty and selected_event_id in coupling_df["event_id"].values:
    coupling_row: dict | None = (
        coupling_df[coupling_df["event_id"] == selected_event_id].iloc[0].to_dict()
    )
else:
    coupling_row = None

# Sensitivity row
if not sensitivity_df.empty and selected_event_id in sensitivity_df["event_id"].values:
    sens_row_df = sensitivity_df[sensitivity_df["event_id"] == selected_event_id]
    sensitivity_row: dict | None = sens_row_df.iloc[0].to_dict()
else:
    sensitivity_row = None

# PP-15 risk result
predicted = simulate_additional_movement(scenario_days, movement_rate)
pp15_risk = compute_pp15_risk(remaining_allowable, predicted)

# Optional inputs
thermal_input = thermal_stats if include_thermal and thermal_stats.get("status") == "ok" else None
quality_input = sensor_quality_summary if include_quality and sensor_quality_summary else None
sens_input = sensitivity_row if include_sensitivity else None

# ── Generate summary ──────────────────────────────────────────────────────────

summary = generate_engineering_summary(
    selected_event_row=event_row,
    movement_rows=movement_rows,
    coupling_row=coupling_row,
    pp15_risk_result=pp15_risk,
    sensitivity_row=sens_input,
    sensor_quality_summary=quality_input,
    pp15_thermal_stats=thermal_input,
    include_disclaimer=include_disclaimer,
)

# ── GPS data availability note ────────────────────────────────────────────────

event_year_val = event_row.get("event_year", 0)
try:
    event_year_int = int(event_year_val)
except (TypeError, ValueError):
    event_year_int = 0

if event_year_int < 2022:
    st.info(
        f"Event {selected_event_id} ({event_year_int}) pre-dates GPS monitoring (started June 2022). "
        "Pier movement, coupling, and sensitivity data are not available for this event."
    )

# ── Display sections ──────────────────────────────────────────────────────────

st.subheader(f"Summary — {selected_event_id} ({event_row.get('event_year')})")
st.markdown(f"**Event class:** {event_row.get('event_class', 'N/A')}")

st.markdown("#### Executive Summary")
st.markdown(summary["executive_summary"])

with st.expander("Low-Water Event Details", expanded=True):
    st.code(summary["low_water_summary"], language=None)

with st.expander("Pier Movement", expanded=True):
    st.code(summary["pier_movement_summary"], language=None)

with st.expander("E-1 / E-2 Coupling"):
    st.code(summary["coupling_summary"], language=None)

with st.expander("PP-15 Joint Clearance Risk Scenario"):
    risk_level = pp15_risk.get("risk_level", "")
    if risk_level == "Span Jacking Likely":
        st.warning(f"Screening risk level: {risk_level} — engineering review recommended.")
    elif risk_level == "Critical":
        st.warning(f"Screening risk level: {risk_level}")
    st.code(summary["pp15_risk_summary"], language=None)

if include_sensitivity:
    with st.expander("Year-to-Year Sensitivity Context"):
        st.code(summary["sensitivity_summary"], language=None)

if include_thermal:
    with st.expander("Thermal Correction Context"):
        st.code(summary["thermal_context_summary"], language=None)

if include_quality:
    with st.expander("Sensor Confidence"):
        st.code(summary["sensor_confidence_summary"], language=None)

with st.expander("Recommended Next Steps", expanded=True):
    st.markdown(summary["recommended_next_steps"])

if include_disclaimer:
    st.info(summary["disclaimer"])

# ── Copyable full text ────────────────────────────────────────────────────────

st.subheader("Full summary text")
st.caption("Select all and copy, or use the download button below.")
st.text_area(
    label="Full summary",
    value=summary["full_summary_text"],
    height=480,
    key="m10_full_text",
    label_visibility="collapsed",
)

st.download_button(
    label="Download summary (.txt)",
    data=summary["full_summary_text"].encode("utf-8"),
    file_name="pierwatch_engineering_summary.txt",
    mime="text/plain",
    key="m10_download",
)

st.caption(
    "PierWatch Milestone 10 — Engineering Summary Generator. "
    "Screening-level decision-support prototype. Not an official engineering report."
)
