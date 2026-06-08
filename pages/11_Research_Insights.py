from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_river_stage_data, get_gps_data, get_primary_device_data, get_sensor_quality_data,
)
from src.device_comparison import event_window_device_comparison
from src.event_detection import detect_low_water_events
from src.gps_processing import compute_event_movement
from src.sensitivity_model import compute_movement_sensitivity

_mode, _ck_path, _ck_mtime = source_cache_key()

st.title("Research Insights")
st.caption(
    "Exploratory, screening-level observations from the implemented monitoring workflow. "
    "These are research questions and interpretation patterns, not engineering decisions."
)

show_mode_banner()

st.info(
    "**Scope:** This page summarizes patterns observed in the PierWatch dataset. "
    "All insights are screening-level and exploratory. "
    "They do not replace field measurements, structural analysis, bridge inspection, or engineering judgment."
)

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()


# ── Cached loaders ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_sensitivity(mode: str, path: str, mt: float) -> pd.DataFrame:
    river = get_river_stage_data()
    events = detect_low_water_events(river)
    gps = get_gps_data()
    movement = compute_event_movement(gps, events) if not gps.empty else pd.DataFrame()
    return compute_movement_sensitivity(events, movement)


@st.cache_data(show_spinner=False)
def _load_sensor_quality(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_sensor_quality_data()


@st.cache_data(show_spinner=True)
def _load_all_devices(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_primary_device_data()


@st.cache_data(show_spinner=False)
def _load_events_and_movement(mode: str, path: str, mt: float):
    river = get_river_stage_data()
    events = detect_low_water_events(river)
    gps = get_gps_data()
    movement = compute_event_movement(gps, events) if not gps.empty else pd.DataFrame()
    return events, movement


sens = _load_sensitivity(_mode, _ck_path, _ck_mtime)
quality_df = _load_sensor_quality(_mode, _ck_path, _ck_mtime)
events_df, movement_df = _load_events_and_movement(_mode, _ck_path, _ck_mtime)
gps_era_sens = sens[sens["event_year"] >= 2022].copy() if not sens.empty else pd.DataFrame()

# ── Section 1: 2022 High-Sensitivity Reference Event ─────────────────────────

st.markdown("---")
st.subheader("1. The 2022 Event as a High-Sensitivity Reference")
st.markdown(
    "The 2022 low-water event appears to be a high-sensitivity reference event in the GPS-era dataset. "
    "Its movement-per-LWSI ratios are substantially higher than those of later GPS-era events "
    "with comparable or greater LWSI scores."
)

if gps_era_sens.empty:
    st.info("No GPS-era sensitivity data available.")
else:
    display_cols = [
        "event_id", "event_year", "LWSI",
        "E1_longitudinal_movement_in", "E2_longitudinal_movement_in",
        "E1_movement_per_LWSI", "E2_movement_per_LWSI",
    ]
    st.dataframe(
        gps_era_sens[display_cols].rename(columns={
            "event_id": "Event",
            "event_year": "Year",
            "LWSI": "LWSI",
            "E1_longitudinal_movement_in": "E1 movement (in)",
            "E2_longitudinal_movement_in": "E2 movement (in)",
            "E1_movement_per_LWSI": "E1 / LWSI",
            "E2_movement_per_LWSI": "E2 / LWSI",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # 2022 vs 2025 sensitivity ratio
    row_2022 = gps_era_sens[gps_era_sens["event_year"] == 2022]
    row_2025 = gps_era_sens[gps_era_sens["event_year"] == 2025]
    if not row_2022.empty and not row_2025.empty:
        e1_ratio = row_2022["E1_movement_per_LWSI"].iloc[0] / row_2025["E1_movement_per_LWSI"].iloc[0]
        e2_ratio = row_2022["E2_movement_per_LWSI"].iloc[0] / row_2025["E2_movement_per_LWSI"].iloc[0]
        st.markdown(
            f"**2022 vs 2025 sensitivity ratio (LWSI-normalised):**  \n"
            f"- E1: {e1_ratio:.1f}× higher in 2022 than 2025  \n"
            f"- E2: {e2_ratio:.1f}× higher in 2022 than 2025  \n\n"
            "Both events have similar LWSI (~0.46). This divergence in movement magnitude "
            "raises questions about whether the system exhibits hysteresis, remediation effects, "
            "or a shift in soil-pier interaction state."
        )

    # Chart: movement per LWSI by event
    melt_sens = gps_era_sens.melt(
        id_vars=["event_id", "event_year"],
        value_vars=["E1_movement_per_LWSI", "E2_movement_per_LWSI"],
        var_name="pier", value_name="movement_per_LWSI",
    )
    melt_sens["pier"] = melt_sens["pier"].str.replace("_movement_per_LWSI", "", regex=False)
    melt_sens = melt_sens.dropna(subset=["movement_per_LWSI"])
    if not melt_sens.empty:
        fig1 = px.bar(
            melt_sens,
            x="event_id", y="movement_per_LWSI", color="pier", barmode="group",
            labels={
                "event_id": "Event",
                "movement_per_LWSI": "Movement per LWSI (in / index unit)",
                "pier": "Pier",
            },
            title="GPS-Era Movement Sensitivity per LWSI",
        )
        fig1.add_annotation(
            text="2022 reference",
            x="LW-050", y=melt_sens["movement_per_LWSI"].max() * 0.95,
            showarrow=False, font=dict(size=11, color="gray"),
        )
        st.plotly_chart(fig1, use_container_width=True, key="ri_sens_bar")
        st.caption(
            "Movement per LWSI = GPS longitudinal movement ÷ Low-Water Severity Index. "
            "High values indicate larger pier movement per unit of hydrologic exposure. "
            "LW-050 (2022) is treated as the reference high-sensitivity event."
        )

# ── Section 2: LWSI Non-linearity ────────────────────────────────────────────

st.markdown("---")
st.subheader("2. Low-Water Severity Is Not a Simple Linear Predictor")
st.markdown(
    "Across GPS-era events, similar or greater LWSI values do not consistently produce "
    "similar movement magnitudes. This suggests that LWSI alone is an incomplete predictor "
    "of pier movement response."
)

if not gps_era_sens.empty:
    scatter_melt = gps_era_sens.melt(
        id_vars=["event_id", "event_year", "LWSI", "days_below_7", "min_stage_ft"],
        value_vars=["E1_longitudinal_movement_in", "E2_longitudinal_movement_in"],
        var_name="pier", value_name="longitudinal_movement_in",
    )
    scatter_melt["pier"] = scatter_melt["pier"].str.replace("_longitudinal_movement_in", "", regex=False)
    scatter_melt = scatter_melt.dropna(subset=["longitudinal_movement_in"])

    if not scatter_melt.empty:
        fig2 = px.scatter(
            scatter_melt,
            x="LWSI", y="longitudinal_movement_in",
            color="pier", symbol="event_year",
            hover_data=["event_id", "event_year", "days_below_7", "min_stage_ft"],
            labels={
                "LWSI": "LWSI (dimensionless composite index)",
                "longitudinal_movement_in": "Longitudinal Movement (in)",
                "pier": "Pier",
            },
            title="LWSI vs GPS Longitudinal Movement — GPS-Era Events",
        )
        st.plotly_chart(fig2, use_container_width=True, key="ri_lwsi_scatter")
        st.caption(
            "LW-050 (2022, triangle marker) stands out with large movement despite moderate LWSI. "
            "LW-054 (2023) has higher LWSI but substantially lower movement, "
            "consistent with possible hysteresis or a change in pier-soil interaction state."
        )

    st.markdown(
        "**Potential explanations (screening-level, not verified):**\n"
        "- Hysteresis from prior large-movement events\n"
        "- Shift in soil-pier interaction state following emergency span jacking\n"
        "- Nonlinear foundation response under extreme vs moderate conditions\n"
        "- Differences in event duration, antecedent conditions, or scour exposure\n"
        "- Sensor coverage changes between events\n\n"
        "This pattern motivates further investigation into event-specific conditioning factors "
        "beyond simple hydrologic severity metrics."
    )

# ── Section 3: Multi-sensor comparison ───────────────────────────────────────

st.markdown("---")
st.subheader("3. Multi-Sensor Interpretation Opportunity")

st.markdown(
    "For GPS-era events (2022–2026), PierWatch can compare GPS pier movement with jointmeter "
    "event-window changes from the PP15, E2, and E3 primary device sheets. "
    "W2 is not available for GPS-era events (monitoring ended 2019)."
)

with st.spinner("Loading primary device data for multi-sensor comparison…"):
    all_devices = _load_all_devices(_mode, _ck_path, _ck_mtime)

if not all_devices.empty and not events_df.empty and not gps_era_sens.empty:
    gps_era_event_ids = gps_era_sens["event_id"].tolist()

    rows = []
    for eid in gps_era_event_ids:
        ev_row = events_df[events_df["event_id"] == eid]
        if ev_row.empty:
            continue
        ev = ev_row.iloc[0]

        # GPS movement for this event
        gps_mov = movement_df[movement_df["event_id"] == eid] if not movement_df.empty else pd.DataFrame()
        def _gps_mov(pier: str) -> float | None:
            if gps_mov.empty:
                return None
            r = gps_mov[gps_mov["pier_id"] == pier]
            if r.empty:
                return None
            v = r["longitudinal_movement_in"].iloc[0]
            return float(v) if pd.notna(v) else None

        # Device event-window changes
        dev_cmp = event_window_device_comparison(all_devices, events_df, eid, pre_days=7, post_days=7)

        def _dev_delta(device_id: str) -> float | None:
            if dev_cmp.empty:
                return None
            r = dev_cmp[dev_cmp["device_id"] == device_id]
            if r.empty:
                return None
            v = r["event_change_corrected_in"].iloc[0]
            return float(v) if pd.notna(v) else None

        def _dev_note(device_id: str) -> str:
            if dev_cmp.empty:
                return "No device data"
            r = dev_cmp[dev_cmp["device_id"] == device_id]
            if r.empty:
                return "No device data"
            return str(r["data_quality_note"].iloc[0])

        e1_m = _gps_mov("E1")
        e2_m = _gps_mov("E2")

        # Consistency note
        gps_ok = e1_m is not None or e2_m is not None
        dev_ok_count = sum(1 for did in ["PP15", "E2", "E3"] if _dev_delta(did) is not None)

        if ev["event_year"] < 2022:
            cons_note = "W2 only — no GPS or device data for GPS-era metrics"
        elif gps_ok and dev_ok_count >= 2:
            cons_note = "Multi-source data available"
        elif gps_ok and dev_ok_count == 1:
            cons_note = "GPS + 1 device source"
        elif gps_ok:
            cons_note = "GPS only — device window data sparse"
        else:
            cons_note = "GPS data unavailable"

        rows.append({
            "event_id": eid,
            "year": int(ev["event_year"]),
            "LWSI": round(float(gps_era_sens.loc[gps_era_sens["event_id"] == eid, "LWSI"].iloc[0]), 3)
                   if eid in gps_era_sens["event_id"].values else None,
            "GPS E1 (in)": round(e1_m, 3) if e1_m is not None else None,
            "GPS E2 (in)": round(e2_m, 3) if e2_m is not None else None,
            "PP15 Δcorr (in)": round(_dev_delta("PP15"), 3) if _dev_delta("PP15") is not None else None,
            "E2 Δcorr (in)": round(_dev_delta("E2"), 3) if _dev_delta("E2") is not None else None,
            "E3 Δcorr (in)": round(_dev_delta("E3"), 3) if _dev_delta("E3") is not None else None,
            "W2 Δcorr (in)": "Not available (W2 ended 2019)",
            "consistency": cons_note,
        })

    multi_df = pd.DataFrame(rows)
    if not multi_df.empty:
        st.dataframe(multi_df, use_container_width=True, hide_index=True)
        st.caption(
            "Δcorr = post-event minus pre-event median corrected expansion (7-day windows). "
            "W2 monitoring ended in 2019 and is not available for any GPS-era event. "
            "Device window data may be sparse for events at the edges of device record coverage."
        )
    else:
        st.info("No multi-sensor comparison data could be assembled.")
else:
    st.info("Multi-sensor comparison requires primary device data. Check that the R1 workbook is present.")

st.markdown(
    "**Research opportunity:** Fusing GPS pier-level movement with local jointmeter event-window "
    "changes could improve confidence in movement interpretation and help distinguish "
    "global (pier-level) from local (joint-level) responses."
)

# ── Section 4: Data coverage ──────────────────────────────────────────────────

st.markdown("---")
st.subheader("4. Data Coverage and Sensor Quality Shape Interpretation")

st.markdown(
    "Sensor coverage is uneven across time and location. "
    "Long-term SHM interpretation must account for data availability and sensor reliability."
)

if not quality_df.empty:
    cov_cols = ["source_name", "sensor_id", "confidence_label", "confidence_score",
                "record_count", "start_time", "end_time"]
    st.dataframe(
        quality_df[cov_cols].rename(columns={
            "source_name": "Source",
            "sensor_id": "Stream",
            "confidence_label": "Confidence",
            "confidence_score": "Score",
            "record_count": "Records",
            "start_time": "Start",
            "end_time": "End",
        }),
        use_container_width=True,
        hide_index=True,
    )

st.markdown(
    "**Key coverage limitations for this dataset:**\n"
    "- **W2** monitoring ended 2019 — not available for any GPS-era event comparison\n"
    "- **GPS E1** has ~1,500 records vs ~3,400 for E2/E3 — affects coupling confidence for recent events\n"
    "- **E3 alternate corrected expansion** column has only ~11 valid records (Poor confidence)\n"
    "- **PP-15 Filter** reference sheet covers only Aug–Nov 2022\n"
    "- **GPS data** begins June 2022 — 49 of 58 detected low-water events have no GPS movement estimates\n\n"
    "Accounting for data completeness and confidence in multi-sensor interpretation "
    "is an open research challenge in SHM analytics."
)

# ── Section 5: Research questions ────────────────────────────────────────────

st.markdown("---")
st.subheader("5. Potential Research Questions")

st.markdown(
    """
**A. Event-based risk indicators**
How can long-term low-water event history be systematically converted into interpretable bridge movement risk indicators, even when direct sensor coverage is incomplete?

**B. Movement sensitivity hysteresis**
Why did the 2022 event produce substantially higher LWSI-normalised pier movement than later GPS-era events with comparable hydrologic exposure? What physical mechanisms (soil consolidation, span-jacking history, scour-hole evolution) might explain this?

**C. Multi-sensor data fusion**
How can GPS pier-level movement, local jointmeter readings, temperature corrections, and river-stage exposure be fused to improve confidence in movement interpretation and reduce dependence on any single data stream?

**D. Sensor quality-aware decision support**
How should data completeness, sensor reliability, and coverage gaps be formally incorporated into SHM-based screening metrics and decision thresholds?

**E. Interpretable analytics for smart infrastructure**
Can engineering-informed, interpretable analytics — without black-box ML models — provide actionable screening-level support for bridge maintenance planning at river crossings under recurring low-water risk?
"""
)

# ── Disclaimer ────────────────────────────────────────────────────────────────

st.markdown("---")
st.warning(
    "**Disclaimer:** These insights are exploratory and screening-level. "
    "They do not replace field measurements, structural analysis, bridge inspection, or engineering judgment. "
    "PierWatch is a monitoring-based decision-support prototype, "
    "not a full FE-based digital twin or official engineering report."
)
