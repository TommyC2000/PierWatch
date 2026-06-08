import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_river_stage_data, get_gps_data,
)
from src.event_detection import detect_low_water_events
from src.gps_processing import compute_event_movement
from src.sensitivity_model import compute_movement_sensitivity

_mode, _ck_path, _ck_mtime = source_cache_key()


@st.cache_data(show_spinner=False)
def _cached_river_stage(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_river_stage_data()


@st.cache_data(show_spinner=False)
def _cached_gps_data(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_gps_data()


st.title("Year-to-Year Movement Sensitivity")
st.caption("Engineering Question: How does low-water exposure severity relate to E-1/E-2 movement across events?")

show_mode_banner()

st.info(
    "**Data source note:** Sensitivity analysis on this page uses event-based movement estimates "
    "derived from the standalone **GPS Data** sheet. "
    "The primary monitoring sheets — W2, PP 15, E2, E3 — "
    "provide jointmeter data integrated on the Primary Device Comparison page."
)

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()

river = _cached_river_stage(_mode, _ck_path, _ck_mtime)
events = detect_low_water_events(river)
gps = _cached_gps_data(_mode, _ck_path, _ck_mtime)
movement = compute_event_movement(gps, events) if not gps.empty else pd.DataFrame()
sensitivity = compute_movement_sensitivity(events, movement)

if sensitivity.empty:
    st.warning("No movement sensitivity data are available.")
    st.stop()

available_years = sorted(sensitivity["event_year"].dropna().astype(int).unique().tolist())
default_years = [year for year in available_years if year >= 2022] or available_years
selected_years = st.sidebar.multiselect("Event years", available_years, default=default_years)
filtered = sensitivity[sensitivity["event_year"].isin(selected_years)].copy() if selected_years else sensitivity.iloc[0:0].copy()

event_labels = filtered.assign(
    event_label=lambda df: df["event_id"].astype(str) + " (" + df["event_year"].astype(str) + ")"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Events displayed", f"{len(filtered):,}",
          help="Number of low-water events matching the selected year filter.")
c2.metric("Max LWSI", "N/A" if filtered.empty else f"{filtered['LWSI'].max():.2f}",
          help=(
              "Low-Water Severity Index — dimensionless composite of days below 12 ft, "
              "days below 7 ft, cumulative deficit below 7 ft, and depth below 7 ft, "
              "all min-max normalized across detected events. Higher values indicate more severe exposure."
          ))
if not filtered.empty and filtered["E1_longitudinal_movement_in"].notna().any():
    c3.metric("Max E1 movement (in)", f"{filtered['E1_longitudinal_movement_in'].abs().max():.2f}",
              help="Maximum absolute E1 longitudinal GPS movement (in) across displayed events. Screening-level auxiliary GPS estimate.")
else:
    c3.metric("Max E1 movement (in)", "N/A")
if not filtered.empty and filtered["E2_longitudinal_movement_in"].notna().any():
    c4.metric("Max E2 movement (in)", f"{filtered['E2_longitudinal_movement_in'].abs().max():.2f}",
              help="Maximum absolute E2 longitudinal GPS movement (in) across displayed events. Screening-level auxiliary GPS estimate.")
else:
    c4.metric("Max E2 movement (in)", "N/A")

st.subheader("Low-Water Severity and Movement Table")
st.dataframe(filtered, use_container_width=True, hide_index=True)

if filtered.empty:
    st.info("No events match the selected year filter.")
    st.stop()

long_for_bars = event_labels.melt(
    id_vars=["event_id", "event_label", "event_year"],
    value_vars=["E1_longitudinal_movement_in", "E2_longitudinal_movement_in"],
    var_name="pier",
    value_name="longitudinal_movement_in",
)
long_for_bars["pier"] = long_for_bars["pier"].str.replace("_longitudinal_movement_in", "", regex=False)
fig_movement = px.bar(
    long_for_bars,
    x="event_label",
    y="longitudinal_movement_in",
    color="pier",
    barmode="group",
    labels={
        "event_label": "Event",
        "longitudinal_movement_in": "Longitudinal Movement (in)",
        "pier": "Pier",
    },
    title="E1/E2 Longitudinal Movement by Event",
)
fig_movement.add_vrect(x0=-0.5, x1=0.5, opacity=0.08, line_width=0) if 2022 in filtered["event_year"].values else None
st.plotly_chart(fig_movement, use_container_width=True, key="m7_movement_bar")

scatter_data = event_labels.melt(
    id_vars=["event_id", "event_label", "event_year", "LWSI", "days_below_7", "min_stage_ft"],
    value_vars=["E1_longitudinal_movement_in", "E2_longitudinal_movement_in"],
    var_name="pier",
    value_name="longitudinal_movement_in",
)
scatter_data["pier"] = scatter_data["pier"].str.replace("_longitudinal_movement_in", "", regex=False)
fig_scatter = px.scatter(
    scatter_data,
    x="LWSI",
    y="longitudinal_movement_in",
    color="pier",
    symbol="event_year",
    hover_data=["event_id", "event_year", "days_below_7", "min_stage_ft"],
    labels={
        "LWSI": "LWSI (dimensionless index)",
        "longitudinal_movement_in": "Longitudinal Movement (in)",
        "pier": "Pier",
    },
    title="Low-Water Severity Index vs E1/E2 Movement",
)
st.plotly_chart(fig_scatter, use_container_width=True, key="m7_lwsi_scatter")
st.caption(
    "LWSI is a dimensionless composite index (min-max normalized) combining days below 12 ft, "
    "days below 7 ft, cumulative deficit below 7 ft, and depth below 7 ft. "
    "It is an exploratory screening metric — not a structural risk score."
)

sensitivity_bars = event_labels.melt(
    id_vars=["event_id", "event_label", "event_year"],
    value_vars=["E1_movement_per_LWSI", "E2_movement_per_LWSI"],
    var_name="pier",
    value_name="movement_per_LWSI",
)
sensitivity_bars["pier"] = sensitivity_bars["pier"].str.replace("_movement_per_LWSI", "", regex=False)
fig_sensitivity = px.bar(
    sensitivity_bars,
    x="event_label",
    y="movement_per_LWSI",
    color="pier",
    barmode="group",
    labels={
        "event_label": "Event",
        "movement_per_LWSI": "Movement per LWSI (in / index unit)",
        "pier": "Pier",
    },
    title="Movement Sensitivity per LWSI",
)
st.plotly_chart(fig_sensitivity, use_container_width=True, key="m7_sensitivity_bar")
st.caption(
    "Movement per LWSI = pier longitudinal movement (in) ÷ LWSI. "
    "High values indicate larger movement per unit of low-water severity. "
    "2022 is treated as a high-movement reference event because it produced the "
    "largest GPS-era movement and triggered emergency response."
)

if 2022 in filtered["event_year"].values:
    reference_2022 = filtered[filtered["event_year"] == 2022]
    st.subheader("2022 Reference Event")
    st.dataframe(reference_2022, use_container_width=True, hide_index=True)
    st.info("2022 is highlighted as a high-movement reference event where available GPS-derived movement estimates are substantially larger than many later low-water events.")

st.subheader("Engineering Interpretation")
st.markdown(
    """
Low-water exposure and pier movement are not necessarily a simple linear relationship. The 2022 event appears to be a high-movement reference event, while later low-water events may show lower movement sensitivity even when exposure remains significant.

This screening-level comparison supports an engineering interpretation where hysteresis, soil-pier interaction history, prior movement state, remediation effects, and event segmentation may influence the observed movement response.
"""
)

st.info("Milestone 7 uses interpretable event metrics only. No black-box ML, PP-15 Filter parsing, or thermal correction is implemented here.")
