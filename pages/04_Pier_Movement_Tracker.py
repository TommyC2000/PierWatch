import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_river_stage_data, get_gps_data,
)
from src.event_detection import detect_low_water_events
from src.gps_processing import compute_event_movement
from src.movement_analysis import compute_coupling_metrics

_mode, _ck_path, _ck_mtime = source_cache_key()


@st.cache_data(show_spinner=False)
def _cached_river_stage(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_river_stage_data()


@st.cache_data(show_spinner=False)
def _cached_gps_data(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_gps_data()


st.title("Pier Movement Tracker")
st.caption("Engineering Question: How did E1, E2, and E3 GPS displacement change during selected low-water events?")

show_mode_banner()

st.info(
    "**Data source note:** Movement tracking on this page uses the workbook-level **GPS Data** sheet, "
    "which is a standalone GPS movement source for event-based movement estimates. "
    "It is not the primary device data table. "
    "The primary monitoring sheets — W2, PP 15, E2, and E3 — "
    "are the primary R1 device sheets (jointmeter data integrated on the Primary Device Comparison page)."
)

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()

river = _cached_river_stage(_mode, _ck_path, _ck_mtime)
events = detect_low_water_events(river)
gps = _cached_gps_data(_mode, _ck_path, _ck_mtime)

if events.empty:
    st.warning("No low-water events were detected. Check the river stage loader and thresholds.")
    st.stop()
if gps.empty:
    st.warning("GPS parsing returned no rows. Inspect the GPS Data sheet mapping.")
    st.stop()

movement = compute_event_movement(gps, events)
coupling = compute_coupling_metrics(movement)

# ── GPS coverage classification ───────────────────────────────────────────────

# An event is "GPS-covered" if compute_event_movement() produced at least one
# row with a non-null longitudinal or transverse movement value for that event.
_gps_events: set[str] = set()
if not movement.empty:
    has_data = movement[
        movement["longitudinal_movement_in"].notna()
        | movement["transverse_movement_in"].notna()
    ]
    _gps_events = set(has_data["event_id"].unique())

def _has_gps(event_id: str) -> bool:
    return event_id in _gps_events

gps_start = gps["timestamp"].min()
gps_end = gps["timestamp"].max()
n_gps_covered = sum(_has_gps(eid) for eid in events["event_id"])
n_total_events = len(events)

# ── Sidebar: coverage filter + event selector ─────────────────────────────────

with st.sidebar:
    st.subheader("Event filter")
    show_all = st.checkbox(
        "Show all low-water events, including events without GPS coverage",
        value=False,
        key="m4_show_all",
        help=(
            "By default only events with computed GPS movement data are shown. "
            "Check this box to include all detected low-water events (2000–2026)."
        ),
    )

    if show_all:
        display_events = events.copy()
    else:
        display_events = events[events["event_id"].apply(_has_gps)].copy()

    if display_events.empty:
        st.warning("No events match the current filter.")
        st.stop()

    def _event_label(row: pd.Series) -> str:
        tag = "GPS available" if _has_gps(row["event_id"]) else "No GPS coverage"
        return (
            f"{row['event_id']} | {int(row['event_year'])} | "
            f"{row['start_date']} to {row['end_date']} | {tag}"
        )

    event_labels_list = display_events.apply(_event_label, axis=1).tolist()

    # Default to LW-050 if present, else most recent GPS-covered event
    pref_ids = ["LW-050"] + list(display_events[display_events["event_id"].apply(_has_gps)]["event_id"].iloc[-1:])
    default_label_idx = 0
    for pref in pref_ids:
        matches = [i for i, lbl in enumerate(event_labels_list) if lbl.startswith(pref + " |")]
        if matches:
            default_label_idx = matches[0]
            break

    selected_label = st.selectbox(
        "Select low-water event",
        options=event_labels_list,
        index=default_label_idx,
        key="m4_event_select",
        help=(
            "Select a low-water event. GPS movement data is available only for events "
            "from June 2022 onward. Recommended: LW-050 (2022) for the largest movement demo."
        ),
    )
    selected_event_id = selected_label.split(" | ")[0]

if not show_all:
    st.caption(
        f"Showing {n_gps_covered} low-water events with available GPS movement data. "
        "GPS coverage begins in 2022. "
        "Check 'Show all low-water events' in the sidebar to include earlier hydrologic events."
    )

# ── GPS coverage summary expander ────────────────────────────────────────────

with st.expander("GPS coverage summary"):
    st.markdown(
        f"""
| | |
|---|---|
| GPS data start | `{gps_start.date()}` |
| GPS data end | `{gps_end.date()}` |
| Total low-water events detected | {n_total_events} |
| Events with GPS movement data | {n_gps_covered} |
| Events without GPS coverage | {n_total_events - n_gps_covered} |
"""
    )

# ── Resolve selected event ────────────────────────────────────────────────────

selected_event = events[events["event_id"] == selected_event_id].iloc[0]
selected_coupling = coupling[coupling["event_id"] == selected_event_id]
event_has_gps = _has_gps(selected_event_id)

start = pd.to_datetime(selected_event["start_date"]).normalize()
end = pd.to_datetime(selected_event["end_date"]).normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
plot_start = start - pd.Timedelta(days=14)
plot_end = end + pd.Timedelta(days=14)
window = gps[(gps["timestamp"] >= plot_start) & (gps["timestamp"] <= plot_end)].copy()
event_window = gps[(gps["timestamp"] >= start) & (gps["timestamp"] <= end)].copy()
selected_movement = movement[movement["event_id"] == selected_event_id].copy()

# ── No-GPS-data branch ────────────────────────────────────────────────────────

if not event_has_gps:
    st.warning(
        f"No GPS movement data are available for **{selected_event_id}** "
        f"({selected_event['start_date']} to {selected_event['end_date']}). "
        "The Pier Movement Tracker uses the standalone GPS Data sheet, which begins in 2022. "
        "Use the **Low-Water Event Detector** page to review earlier hydrologic events."
    )

    st.subheader("Event hydrologic context")
    st.markdown(
        f"| | |\n|---|---|\n"
        f"| **Event ID** | {selected_event_id} |\n"
        f"| **Date range** | {selected_event['start_date']} to {selected_event['end_date']} |\n"
        f"| **Minimum river stage** | {selected_event['min_stage_ft']:.2f} ft |\n"
        f"| **Days below 7 ft** | {int(selected_event['days_below_7'])} |\n"
        f"| **Event class** | {selected_event['event_class']} |\n"
        f"| **Data status** | No GPS coverage |\n"
    )
    st.stop()

# ── GPS-covered event: metrics + plots ───────────────────────────────────────

c1, c2, c3 = st.columns(3)
c1.metric("GPS records", f"{len(gps):,}",
          help="Total GPS position records across all piers in the loaded GPS Data sheet.")
c2.metric("Event window records", f"{len(event_window):,}",
          help="GPS records falling within the selected event start/end window.")
c3.metric("Movement rows", f"{len(selected_movement):,}",
          help="Event movement estimates computed for the selected event (one row per pier).")

pier_list = " · ".join(f"`{p}`" for p in sorted(gps["pier_id"].drop_duplicates().tolist()))
st.markdown(f"**Piers detected:** {pier_list} — Movement estimates are GPS-derived screening values.")

if window.empty:
    st.warning("No GPS observations are available near the selected event.")
else:
    fig_long = px.line(
        window,
        x="timestamp",
        y="longitudinal_in",
        color="pier_id",
        labels={"timestamp": "Date", "longitudinal_in": "Longitudinal Displacement (in)", "pier_id": "Pier"},
        title="Longitudinal GPS Displacement — ±14-Day Event Window",
    )
    fig_long.add_vrect(x0=start, x1=end, opacity=0.12, line_width=0)
    st.plotly_chart(fig_long, use_container_width=True, key="m4_long_disp")

    fig_trans = px.line(
        window,
        x="timestamp",
        y="transverse_in",
        color="pier_id",
        labels={"timestamp": "Date", "transverse_in": "Transverse Displacement (in)", "pier_id": "Pier"},
        title="Transverse GPS Displacement — ±14-Day Event Window",
    )
    fig_trans.add_vrect(x0=start, x1=end, opacity=0.12, line_width=0)
    st.plotly_chart(fig_trans, use_container_width=True, key="m4_trans_disp")

st.subheader("Event Movement Estimate")
st.caption(
    "Movement is estimated as the median GPS displacement in the post-event window minus "
    "the median in the pre-event window (before/after comparison). "
    "This is a screening-level estimate from the GPS workflow, "
    "not a direct structural displacement measurement."
)
st.dataframe(selected_movement, use_container_width=True, hide_index=True)

st.subheader("E-1 / E-2 Coupling")
if selected_coupling.empty:
    st.info("No coupling metrics are available for the selected event.")
else:
    coupling_row = selected_coupling.iloc[0]
    k1, k2, k3, k4 = st.columns(4)
    ratio = coupling_row["coupling_ratio"]
    diff = coupling_row["differential_movement_in"]
    tolerance = coupling_row["tolerance_in"]
    k1.metric("Coupling ratio", "N/A" if pd.isna(ratio) else f"{ratio:.2f}",
              help="Ratio of E1 to E2 longitudinal movement. Values near 1.0 suggest similar movement magnitude.")
    k2.metric("Differential movement (in)", "N/A" if pd.isna(diff) else f"{diff:.2f}",
              help="Absolute difference between E1 and E2 longitudinal movement (in).")
    k3.metric("Tolerance (in)", "N/A" if pd.isna(tolerance) else f"{tolerance:.2f}",
              help="Movement tolerance threshold used to classify coupling status — based on a fraction of average movement.")
    k4.metric("Coupling status", coupling_row["coupling_status"],
              help="Screening interpretation of whether E1 and E2 moved together with similar direction and magnitude.")
    st.write(coupling_row["interpretation"])
    with st.expander("How is coupling status determined?"):
        st.markdown(
            """
**E-1 / E-2 coupling classification (screening-level):**

- **Coupled**: Both E1 and E2 show movement above a minimum threshold, coupling ratio is
  between 0.5 and 2.0, and differential movement is within tolerance.
- **Not Strongly Coupled**: Movement detected but either the ratio or differential movement
  is outside the expected range.
- **Stable / Minimal Movement**: Movement below the minimum threshold for both piers.
- **Insufficient Data**: GPS data is not available for one or both piers.

Coupling ratio = E1 longitudinal movement ÷ E2 longitudinal movement.
Differential movement = |E1 − E2| longitudinal movement (in).

This is a screening-level interpretation based on GPS estimates only.
"""
        )

st.subheader("Data Availability")
availability = (
    selected_movement[
        [
            "pier_id",
            "baseline_source",
            "pre_sample_count",
            "post_sample_count",
            "data_availability",
        ]
    ]
    if not selected_movement.empty
    else pd.DataFrame()
)
st.dataframe(availability, use_container_width=True, hide_index=True)

st.subheader("Coupling Summary")
st.dataframe(coupling, use_container_width=True, hide_index=True)

with st.expander("GPS data sample", expanded=False):
    st.dataframe(gps.head(30), use_container_width=True, hide_index=True)

st.info("Milestone 5 adds E-1/E-2 coupling analysis. PP-15 risk and Year-to-Year Sensitivity are intentionally not implemented on this page yet.")
