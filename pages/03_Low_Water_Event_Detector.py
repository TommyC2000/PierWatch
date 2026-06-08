import pandas as pd
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_river_stage_data,
)
from src.event_detection import detect_low_water_events
from src.plotting import river_stage_plot

_mode, _ck_path, _ck_mtime = source_cache_key()


@st.cache_data(show_spinner=False)
def _cached_river_stage(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_river_stage_data()


st.title("Low-Water Event Detector")
st.caption("Engineering Question: When did river stage fall into a range where pier movement becomes possible or likely?")

show_mode_banner()

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()

possible = st.sidebar.number_input(
    "Movement possible threshold (ft)", value=12.0, step=0.5,
    help="River stage below this threshold indicates pier movement becomes possible, based on engineering thresholds for this bridge type.",
)
likely = st.sidebar.number_input(
    "Movement likely threshold (ft)", value=7.0, step=0.5,
    help="River stage below this threshold indicates pier movement is likely, based on engineering thresholds for this bridge type.",
)
min_days = st.sidebar.number_input(
    "Minimum event days", value=3, min_value=1, step=1,
    help="Minimum number of days below the possible-movement threshold to qualify as a low-water event.",
)
merge_gap = st.sidebar.number_input(
    "Merge gap days", value=5, min_value=0, step=1,
    help="Events separated by fewer than this many days above threshold are merged into a single event.",
)

if likely >= possible:
    st.sidebar.warning("The likely-movement threshold should be below the possible-movement threshold.")

river = _cached_river_stage(_mode, _ck_path, _ck_mtime)
events = detect_low_water_events(river, possible, likely, int(min_days), int(merge_gap))

available_years = sorted(events["event_year"].dropna().astype(int).unique().tolist()) if not events.empty else []
selected_years = st.sidebar.multiselect("Event years", available_years, default=available_years)
filtered_events = events[events["event_year"].isin(selected_years)] if selected_years else events.iloc[0:0]

r1, r2, r3 = st.columns(3)
r1.metric("River records", f"{len(river):,}",
          help="Total daily river stage records in the loaded dataset.")
r2.metric("Detected events", f"{len(events):,}",
          help="Total low-water events detected across all years using the current thresholds.")
r3.metric("Displayed events", f"{len(filtered_events):,}",
          help="Events matching the selected year and threshold filters.")

stage_min = river["stage_ft"].min()
stage_max = river["stage_ft"].max()
s1, s2 = st.columns(2)
s1.metric("Min Stage (ft)", f"{stage_min:.2f}",
          help="Lowest river stage recorded across the full dataset.")
s2.metric("Max Stage (ft)", f"{stage_max:.2f}",
          help="Highest river stage recorded across the full dataset.")

st.plotly_chart(river_stage_plot(river, filtered_events, possible, likely), use_container_width=True)

with st.expander("How are low-water events detected?"):
    st.markdown(
        """
**Event detection logic (screening-level):**

1. Days where river stage drops below the **movement-possible threshold** (default: 12 ft) are identified.
2. Consecutive below-threshold days are grouped into candidate events.
3. Events shorter than the **minimum event days** setting are discarded.
4. Events separated by fewer than the **merge gap** days above threshold are merged.
5. Each event is classified by low-water severity and minimum stage.

**Cumulative deficit below 7 ft** is the sum of (7 − stage_ft) over all days when stage < 7 ft.
It approximates total low-water exposure severity for the event.

**Event class** is a screening label based on exposure duration and depth — it is not a
structural safety classification.

This is a screening-level heuristic. It does not replace hydrological analysis or
engineering judgment.
"""
    )

st.subheader("Detected Low-Water Events")
if filtered_events.empty:
    st.info("No events match the current threshold and year filters.")
else:
    st.dataframe(filtered_events, use_container_width=True, hide_index=True)

with st.expander("River stage sample", expanded=False):
    st.dataframe(river.head(20), use_container_width=True, hide_index=True)

st.info(
    "Event detection uses river stage only. GPS movement tracking and PP-15 risk screening are intentionally outside Milestone 3."
)
