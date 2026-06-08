from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_primary_device_data, get_river_stage_data,
)
from src.device_comparison import (
    device_availability_summary,
    event_window_device_comparison,
    latest_device_snapshot,
    yearly_device_summary,
)
from src.event_detection import detect_low_water_events

_mode, _ck_path, _ck_mtime = source_cache_key()

st.title("Primary Device Comparison")
st.caption(
    "Screening-level comparison of W2, PP15, E2, and E3 jointmeter data "
    "from the R1 primary device sheets."
)

show_mode_banner()

st.info(
    "**Data source:** This page reads the four primary R1 device sheets — "
    "**W2**, **PP 15**, **E2**, **E3** — and compares measured expansion, "
    "temperature, and corrected expansion across devices and events. "
    "GPS movement tracking uses the standalone GPS Data sheet."
)

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()


@st.cache_data(show_spinner=True)
def _load_devices(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_primary_device_data()


@st.cache_data(show_spinner=False)
def _load_events(mode: str, path: str, mt: float) -> pd.DataFrame:
    river = get_river_stage_data()
    return detect_low_water_events(river)


with st.spinner("Loading primary device sheets (this may take a moment for large datasets)…"):
    all_devices = _load_devices(_mode, _ck_path, _ck_mtime)

events = _load_events(_mode, _ck_path, _ck_mtime)

if all_devices.empty:
    st.warning("No primary device data could be loaded. Check that the R1 workbook is present.")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader("Device comparison filters")
    all_device_ids = sorted(all_devices["device_id"].unique().tolist())
    selected_devices = st.multiselect(
        "Devices to display",
        options=all_device_ids,
        default=all_device_ids,
        key="m10c_devices",
        help="Select which primary device sheets to include in the comparison.",
    )

filtered_devices = all_devices[all_devices["device_id"].isin(selected_devices)] if selected_devices else all_devices.iloc[0:0]

# ── Section A: Data Availability Table ───────────────────────────────────────

st.subheader("A. Device Data Availability")
st.caption(
    "Data availability summary for each primary device sheet. "
    "Screening-level overview — does not replace manual data validation."
)

avail = device_availability_summary(filtered_devices)
if not avail.empty:
    st.dataframe(avail, use_container_width=True, hide_index=True)
else:
    st.info("No availability data to display.")

# ── Section B: Latest Snapshot ────────────────────────────────────────────────

st.subheader("B. Latest Device Snapshot")
st.caption("Most recent reading for each device.")

snapshot = latest_device_snapshot(filtered_devices)
if not snapshot.empty:
    st.dataframe(snapshot, use_container_width=True, hide_index=True)
else:
    st.info("No snapshot data available.")

# ── Section C: Event Window Comparison ───────────────────────────────────────

st.subheader("C. Event Window Comparison")
st.caption(
    "Pre/post corrected and measured expansion change during a selected low-water event. "
    "Pre-event window = 7 days before event start; post-event window = 7 days after event end."
)

if events.empty:
    st.info("No low-water events detected. Cannot run event window comparison.")
else:
    gps_era = events[events["event_year"] >= 2022]
    default_event_idx = int(gps_era.index[-1]) if not gps_era.empty else len(events) - 1
    event_labels_list = (
        events["event_id"].astype(str)
        + " ("
        + events["event_year"].astype(str)
        + ") — "
        + events["event_class"].astype(str)
    ).tolist()
    selected_ev_label = st.selectbox(
        "Select event for device comparison",
        options=event_labels_list,
        index=events.index.get_loc(events.index[default_event_idx]) if default_event_idx < len(events) else 0,
        key="m10c_event",
        help="Select the low-water event to compare device readings across.",
    )
    selected_ev_id = selected_ev_label.split(" ")[0]

    ev_comparison = event_window_device_comparison(filtered_devices, events, selected_ev_id)
    if ev_comparison.empty:
        st.info(f"No device comparison data available for event {selected_ev_id}.")
    else:
        st.dataframe(ev_comparison, use_container_width=True, hide_index=True)

        # Visualise event change
        ev_plot = ev_comparison.dropna(subset=["event_change_corrected_in"])
        if not ev_plot.empty:
            fig_ev = px.bar(
                ev_plot,
                x="device_id",
                y="event_change_corrected_in",
                color="device_id",
                labels={
                    "device_id": "Device",
                    "event_change_corrected_in": "Corrected Expansion Change (in)",
                },
                title=f"Corrected Expansion Change During Event {selected_ev_id} (post − pre median)",
            )
            fig_ev.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            st.plotly_chart(fig_ev, use_container_width=True, key="m10c_ev_change_bar")
            st.caption(
                "Positive = expansion increased (joint opened). "
                "Negative = expansion decreased (joint closed). "
                "Screening-level estimate; requires engineering review."
            )

    with st.expander("How is the event window comparison calculated?"):
        st.markdown(
            """
**Event window comparison method (screening-level):**

- **Pre-event window**: device records in the 7 days before the event start date.
- **Event window**: device records between event start and end dates.
- **Post-event window**: device records in the 7 days after the event end date.
- **Change** = post-event median − pre-event median (corrected or measured expansion).

This is an exploratory comparison. It does not account for temperature differences
between the pre and post windows, seasonal trends, or other confounders.
"""
        )

# ── Section D: Yearly / Seasonal Summary ─────────────────────────────────────

st.subheader("D. Yearly Device Summary")
st.caption(
    "Annual statistics per device. "
    "Supports long-term trend screening similar to workbook comparison tables."
)

with st.sidebar:
    low_pct = st.slider(
        "Low/high temperature percentile",
        min_value=10,
        max_value=40,
        value=25,
        step=5,
        key="m10c_lowpct",
        help=(
            "Records at or below this percentile are used for 'low-temperature median'; "
            "records at or above (100 − this percentile) for 'high-temperature median'."
        ),
    )

yearly = yearly_device_summary(filtered_devices, low_temp_percentile=low_pct)

if yearly.empty:
    st.info("No yearly summary data available.")
else:
    year_filter_min = int(yearly["year"].min())
    year_filter_max = int(yearly["year"].max())
    with st.sidebar:
        year_range = st.slider(
            "Year range",
            min_value=year_filter_min,
            max_value=year_filter_max,
            value=(max(year_filter_min, year_filter_max - 10), year_filter_max),
            key="m10c_year_range",
            help="Filter yearly summary to a specific year range.",
        )
    yearly_filtered = yearly[
        (yearly["year"] >= year_range[0]) & (yearly["year"] <= year_range[1])
    ]
    st.dataframe(yearly_filtered, use_container_width=True, hide_index=True)

    if "median_corrected_expansion_in" in yearly_filtered.columns:
        fig_yr = px.line(
            yearly_filtered,
            x="year",
            y="median_corrected_expansion_in",
            color="device_id",
            markers=True,
            labels={
                "year": "Year",
                "median_corrected_expansion_in": "Median Corrected Expansion (in)",
                "device_id": "Device",
            },
            title="Median Annual Corrected Expansion by Device",
        )
        st.plotly_chart(fig_yr, use_container_width=True, key="m10c_yearly_line")

    if "median_temperature_f" in yearly_filtered.columns:
        fig_temp = px.line(
            yearly_filtered,
            x="year",
            y="median_temperature_f",
            color="device_id",
            markers=True,
            labels={
                "year": "Year",
                "median_temperature_f": "Median Annual Temperature (°F)",
                "device_id": "Device",
            },
            title="Median Annual Temperature by Device",
        )
        st.plotly_chart(fig_temp, use_container_width=True, key="m10c_yearly_temp_line")

# ── Corrected Expansion Time Series ──────────────────────────────────────────

st.subheader("E. Corrected Expansion Time Series")
st.caption("Full time-series comparison across selected primary devices. May be slow for large date ranges.")

with st.sidebar:
    show_ts = st.checkbox(
        "Show full time-series chart",
        value=False,
        key="m10c_show_ts",
        help="Plot all device corrected expansion over time. Disable for faster page load.",
    )

if show_ts:
    ts_data = filtered_devices.dropna(subset=["corrected_expansion_in"])
    if not ts_data.empty:
        fig_ts = px.line(
            ts_data,
            x="timestamp",
            y="corrected_expansion_in",
            color="device_id",
            labels={
                "timestamp": "Date",
                "corrected_expansion_in": "Corrected Expansion (in)",
                "device_id": "Device",
            },
            title="Corrected Expansion Over Time — Primary Devices",
        )
        st.plotly_chart(fig_ts, use_container_width=True, key="m10c_ts_corr")
    else:
        st.info("No corrected expansion data available for the selected devices.")

st.info(
    "Primary Device Comparison — R1 workbook. Screening-level interpretation. "
    "Does not replace field measurements, structural analysis, or engineering judgment."
)
