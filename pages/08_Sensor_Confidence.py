from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.sensor_quality import QUALITY_COLUMNS
from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_sensor_quality_data,
)

_mode, _ck_path, _ck_mtime = source_cache_key()

st.title("Sensor Confidence and Data Quality")
st.caption(
    "Screening-level data quality indicators for the monitoring streams used in PierWatch."
)

show_mode_banner()

st.info(
    "**R1 data scope:** Quality metrics on this page cover all implemented R1 monitoring streams: "
    "River Stage 2000-2026, GPS Data (E1, E2, E3), PP-15 Filter (reference), "
    "and the four primary device sheets — **W2**, **PP 15**, **E2**, **E3**."
)

st.markdown(
    """
**Engineering context.**
Long-term structural health monitoring interpretation depends on the completeness, consistency,
and reliability of the underlying data. Gaps, outliers, sensor dropouts, and flatline readings
can all distort trend analysis and event detection.

This page provides **screening-level data quality indicators** for each monitoring data stream
currently loaded in PierWatch:

- **River Stage** (2000–2026, ~daily)
- **GPS pier positions** — E1, E2, E3 longitudinal and transverse
- **Primary device sheets** — W2, PP 15, E2, E3: measured expansion, temperature, and corrected expansion (6 h intervals)
- **PP-15 Filter** — pre-processed reference filter record (6 h intervals, 2022 only)

Metrics reported include completeness rate, missing value rate, IQR-based outlier rate (3 × IQR
threshold), recent availability, flatline indicator, and a composite confidence score.

**Important.** A high confidence score does not prove sensor correctness. Manual data validation,
field verification, and engineering judgment remain essential before drawing structural conclusions.
"""
)

# ── Data loading ──────────────────────────────────────────────────────────────

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()


@st.cache_data(show_spinner=False)
def _load(mode: str, path: str, mt: float) -> pd.DataFrame:
    return get_sensor_quality_data()


quality = _load(_mode, _ck_path, _ck_mtime)

if quality.empty:
    st.warning("No sensor quality data could be computed. Check that the data files are present.")
    st.stop()

# ── Sidebar filters ───────────────────────────────────────────────────────────

LABEL_ORDER = ["High", "Medium", "Low", "Poor", "Insufficient Data"]
all_sources = sorted(quality["source_name"].dropna().unique().tolist())
all_labels = [lb for lb in LABEL_ORDER if lb in quality["confidence_label"].values]

with st.sidebar:
    st.subheader("Sensor quality filters")

    selected_sources = st.multiselect(
        "Data source",
        options=all_sources,
        default=all_sources,
        key="m9_source_filter",
        help="Filter streams by data source category (River Stage, GPS, Primary Device, PP-15 Filter).",
    )
    selected_labels = st.multiselect(
        "Confidence label",
        options=LABEL_ORDER,
        default=LABEL_ORDER,
        key="m9_label_filter",
        help=(
            "Filter by screening confidence label: "
            "High (score ≥ 0.80), Medium (0.60–0.79), Low (0.40–0.59), "
            "Poor (< 0.40), Insufficient Data (fewer than 10 valid records)."
        ),
    )
    min_score = st.slider(
        "Minimum confidence score",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.05,
        key="m9_min_score",
        help="Only show streams with a confidence score at or above this threshold (0 = show all streams).",
    )

filtered = quality.copy()
if selected_sources:
    filtered = filtered[filtered["source_name"].isin(selected_sources)]
if selected_labels:
    filtered = filtered[filtered["confidence_label"].isin(selected_labels)]
filtered = filtered[filtered["confidence_score"].fillna(0) >= min_score]

# ── Summary cards ─────────────────────────────────────────────────────────────

label_counts = quality["confidence_label"].value_counts()
n_high = int(label_counts.get("High", 0))
n_medium = int(label_counts.get("Medium", 0))
n_low_poor = int(label_counts.get("Low", 0) + label_counts.get("Poor", 0))
n_insufficient = int(label_counts.get("Insufficient Data", 0))
avg_score = float(quality["confidence_score"].mean())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total streams", len(quality),
          help="Total monitoring streams evaluated in this prototype.")
c2.metric("High confidence", n_high,
          help="Streams with confidence score ≥ 0.80.")
c3.metric("Medium confidence", n_medium,
          help="Streams with confidence score 0.60–0.79.")
c4.metric("Low / Poor", n_low_poor,
          help="Streams with confidence score below 0.60.")
c5.metric("Avg score (0–1)", f"{avg_score:.3f}",
          help="Average confidence score across all evaluated streams. Score = 0.40×completeness + 0.25×recent_availability + 0.20×(1−outlier_rate) + 0.15×(1−missing_rate).")

# ── Main quality table ────────────────────────────────────────────────────────

st.subheader("Data quality summary table")

display_cols = [
    "source_name", "sensor_id",
    "start_time", "end_time",
    "record_count", "valid_record_count",
    "completeness_rate", "missing_value_rate",
    "outlier_rate", "recent_availability_rate",
    "flatline_rate",
    "confidence_score", "confidence_label",
]
display_cols = [c for c in display_cols if c in filtered.columns]

if filtered.empty:
    st.info("No streams match the selected filters.")
else:
    st.dataframe(
        filtered[display_cols].reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Full quality metrics table"):
        st.dataframe(filtered.reset_index(drop=True), use_container_width=True, hide_index=True)

if filtered.empty:
    st.stop()

# ── Confidence score bar chart ────────────────────────────────────────────────

st.subheader("Confidence scores by stream")

COLOR_MAP = {"High": "#2ca02c", "Medium": "#1f77b4", "Low": "#ff7f0e",
             "Poor": "#d62728", "Insufficient Data": "#7f7f7f"}

fig_conf = px.bar(
    filtered.sort_values("confidence_score", ascending=True),
    x="confidence_score",
    y="sensor_id",
    color="confidence_label",
    color_discrete_map=COLOR_MAP,
    orientation="h",
    labels={"confidence_score": "Confidence score (0–1)", "sensor_id": "Stream"},
    title="Sensor Confidence Score",
    range_x=[0, 1],
)
fig_conf.add_vline(x=0.80, line_dash="dot", line_color="green",
                   annotation_text="High threshold (0.80)", annotation_position="top right")
fig_conf.add_vline(x=0.60, line_dash="dot", line_color="orange",
                   annotation_text="Medium threshold (0.60)", annotation_position="top left")
st.plotly_chart(fig_conf, use_container_width=True, key="m9_confidence_bar")

# ── Missing value rate ────────────────────────────────────────────────────────

st.subheader("Missing value rates")

fig_miss = px.bar(
    filtered.sort_values("missing_value_rate", ascending=True),
    x="missing_value_rate",
    y="sensor_id",
    color="source_name",
    orientation="h",
    labels={"missing_value_rate": "Missing value rate (0–1)", "sensor_id": "Stream"},
    title="Missing Value Rate by Stream",
)
st.plotly_chart(fig_miss, use_container_width=True, key="m9_missing_bar")

# ── Outlier rate ──────────────────────────────────────────────────────────────

st.subheader("Outlier rates (IQR method, 3 × IQR threshold)")

fig_out = px.bar(
    filtered.sort_values("outlier_rate", ascending=True),
    x="outlier_rate",
    y="sensor_id",
    color="source_name",
    orientation="h",
    labels={"outlier_rate": "Outlier rate (0–1)", "sensor_id": "Stream"},
    title="Outlier Rate by Stream (3 × IQR Threshold)",
)
st.plotly_chart(fig_out, use_container_width=True, key="m9_outlier_bar")

# ── Data availability timeline ────────────────────────────────────────────────

st.subheader("Data availability timeline")

timeline_data = filtered.dropna(subset=["start_time", "end_time"]).copy()
if not timeline_data.empty:
    timeline_data["start_str"] = timeline_data["start_time"].astype(str)
    timeline_data["end_str"] = timeline_data["end_time"].astype(str)
    fig_timeline = px.timeline(
        timeline_data,
        x_start="start_str",
        x_end="end_str",
        y="sensor_id",
        color="confidence_label",
        color_discrete_map=COLOR_MAP,
        labels={"sensor_id": "Stream", "confidence_label": "Confidence"},
        title="Monitoring Data Availability by Stream",
        hover_data=["record_count", "data_span_days", "confidence_score"],
    )
    fig_timeline.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_timeline, use_container_width=True, key="m9_timeline")
else:
    st.info("Availability timeline requires start/end timestamps.")

# ── Completeness vs recent availability scatter ───────────────────────────────

if filtered[["completeness_rate", "recent_availability_rate"]].notna().all(axis=None):
    fig_scatter = px.scatter(
        filtered,
        x="completeness_rate",
        y="recent_availability_rate",
        color="confidence_label",
        color_discrete_map=COLOR_MAP,
        text="sensor_id",
        labels={
            "completeness_rate": "Completeness rate",
            "recent_availability_rate": "Recent availability (last 90 d)",
        },
        title="Completeness vs Recent Availability",
        range_x=[0, 1.05],
        range_y=[0, 1.05],
    )
    fig_scatter.update_traces(textposition="top center", marker_size=10)
    st.plotly_chart(fig_scatter, use_container_width=True, key="m9_completeness_scatter")

# ── Engineering interpretation ────────────────────────────────────────────────

st.subheader("Engineering interpretation")
st.markdown(
    """
**How to use these indicators:**

- **High confidence** streams (score ≥ 0.80) have high completeness, low missing-value and
  outlier rates, and good recent availability. They are more suitable for trend interpretation
  and event detection.

- **Medium confidence** streams (0.60–0.79) may have modest gaps, occasional outliers, or
  limited recent data. They can support qualitative trend analysis but warrant caution for
  quantitative conclusions.

- **Low / Poor confidence** streams (below 0.60) have significant data gaps, high outlier or
  missing-value rates, or limited recent availability. They should not drive engineering
  conclusions without manual review and independent verification.

- **Insufficient Data** streams do not have enough records to compute reliable statistics.
  Field verification or additional data collection is recommended before relying on them.

**Confidence score formula (screening-level):**

```
confidence_score = 0.40 × completeness_rate
                 + 0.25 × recent_availability_rate
                 + 0.20 × (1 − outlier_rate)
                 + 0.15 × (1 − missing_value_rate)
```

Outlier detection uses the IQR method with a 3 × IQR threshold to avoid over-flagging
engineering data with real large-amplitude events.
"""
)

st.info(
    "Milestone 9: Screening-level sensor confidence and data quality assessment. "
    "This page does not replace manual data validation, field verification, "
    "bridge inspection, or engineering judgment."
)
