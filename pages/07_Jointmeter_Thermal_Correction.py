from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_sources import (
    source_cache_key, show_mode_banner, is_data_available,
    get_device_sheet_data,
)
from src.thermal_correction import compare_low_temperature_windows, compute_linear_thermal_correction

_mode, _ck_path, _ck_mtime = source_cache_key()

_DEVICE_OPTIONS = {
    "PP15 (PP 15)": ("PP 15", "PP15"),
    "W2":           ("W2",    "W2"),
    "E2":           ("E2",    "E2"),
    "E3":           ("E3",    "E3"),
}

st.title("Jointmeter / Thermal Correction")
st.caption(
    "Primary device jointmeter screening: how much measured expansion variation is temperature-driven "
    "before interpreting long-term movement trends?"
)

show_mode_banner()

st.markdown(
    """
**Engineering context.**
The PP-15 expansion joint and the W2, E2, E3 pier jointmeters record measured opening/closing
in inches. Jointmeter readings contain both a thermal component (joint expands in cold,
contracts in heat) and a structural component (permanent or quasi-permanent movement from
pier displacement or span jacking history).

This page supports **screening-level interpretation** by:
1. Visualising raw measured and pre-computed thermally corrected expansion over time.
2. Fitting a simple linear model (movement = slope × temperature + intercept) to quantify
   the temperature signal in the measured record.
3. Comparing thermally corrected expansion under similar low-temperature conditions
   across years when multiple years of data are available.

**Important limitation.** This analysis does not replace field verification, bridge
inspection, structural analysis, or engineering judgment.

**Data source.** This page reads the four primary R1 device sheets:
**W2**, **PP 15**, **E2**, and **E3**.
The PP-15 Filter sheet is available as a supplementary reference in the Data Overview page.
"""
)

if not is_data_available():
    st.error("Data not available. Check DATA_MODE and data files.")
    st.stop()

# ── Sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader("Device and filter controls")

    device_label = st.selectbox(
        "Primary device",
        options=list(_DEVICE_OPTIONS.keys()),
        index=0,
        key="m8r1_device",
        help="Select from the four primary R1 device sheets: PP15, W2, E2, E3.",
    )
    sheet_name, device_id = _DEVICE_OPTIONS[device_label]

    temp_percentile = st.slider(
        "Low-temperature percentile for year-over-year comparison",
        min_value=5, max_value=50, value=10, step=5,
        key="m8r1_temp_pct",
        help=(
            "Records at or below this temperature percentile are used for the "
            "low-temperature year-over-year comparison."
        ),
    )


@st.cache_data(show_spinner=False)
def _load(mode: str, path: str, mt: float, device_id: str) -> pd.DataFrame:
    return get_device_sheet_data(device_id)


device_df = _load(_mode, _ck_path, _ck_mtime, device_id)

if device_df.empty:
    st.warning(f"No usable data loaded for device {device_id} (sheet: {sheet_name!r}).")
    st.stop()

# E3: allow selecting which corrected column to use
corrected_col = "corrected_expansion_in"
if device_id == "E3" and "corrected_expansion_alt_in" in device_df.columns:
    corr_choice = st.sidebar.selectbox(
        "E3 corrected expansion column",
        options=["corrected_expansion_in", "corrected_expansion_alt_in"],
        index=0,
        key="m8r1_e3_corr",
        help=(
            "E3 has two corrected expansion columns: primary (440.34 ft span) "
            "and alternate (540 ft behavioral span)."
        ),
    )
    corrected_col = corr_choice

with st.sidebar:
    date_min = device_df["timestamp"].min().date()
    date_max = device_df["timestamp"].max().date()
    date_range = st.date_input(
        "Date range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
        key="m8r1_date_range",
        help="Filter device records to a specific date range.",
    )
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    else:
        start_date, end_date = pd.Timestamp(date_min), pd.Timestamp(date_max)

    movement_options = [c for c in ["measured_expansion_in", corrected_col] if c in device_df.columns]
    regression_col = st.selectbox(
        "Movement column for linear regression",
        options=movement_options,
        index=0,
        key="m8r1_reg_col",
        help=(
            "'measured_expansion_in' is the raw jointmeter reading. "
            "The corrected column is the pre-computed thermally corrected value from the workbook."
        ),
    )

filtered = device_df[
    (device_df["timestamp"] >= start_date) & (device_df["timestamp"] <= end_date)
].copy()

# ── Data loading summary ──────────────────────────────────────────────────────

st.subheader("Data loading summary")
metric_col1, metric_col2 = st.columns(2)
metric_col1.metric("Records loaded", f"{len(device_df):,}")
metric_col2.metric("Records in view", f"{len(filtered):,}")
st.markdown(
    f"**Full date range:** `{date_min}` to `{date_max}`  \n"
    f"**Current view:** `{start_date.date()}` to `{end_date.date()}`"
)

mapped_cols = [c for c in device_df.columns if device_df[c].notna().any()]
st.markdown(f"**Columns successfully mapped:** {', '.join(mapped_cols)}")

missing_summary = {c: int(device_df[c].isna().sum()) for c in device_df.columns if device_df[c].isna().any()}
if missing_summary:
    st.markdown(
        "**Missing value counts:** "
        + ", ".join(f"{c}: {n}" for c, n in missing_summary.items())
    )
else:
    st.success("No missing values in loaded data.")

if filtered.empty:
    st.warning("No records in selected date range.")
    st.stop()

with st.expander(f"{device_id} data preview (first 50 rows)"):
    st.dataframe(filtered.head(50), use_container_width=True, hide_index=True)

# ── Time-series plots ─────────────────────────────────────────────────────────

st.subheader("Measured and corrected expansion over time")

expansion_cols = [c for c in ["measured_expansion_in", corrected_col] if c in filtered.columns]
if expansion_cols:
    fig_exp = px.line(
        filtered,
        x="timestamp",
        y=expansion_cols,
        labels={"value": "Expansion (in)", "variable": "Series", "timestamp": "Date"},
        title=f"{device_id} — Measured and Corrected Expansion",
    )
    fig_exp.update_layout(legend_title_text="Series")
    st.plotly_chart(fig_exp, use_container_width=True, key="m8r1_expansion_time")

if "temperature_f" in filtered.columns:
    fig_temp = px.line(
        filtered,
        x="timestamp",
        y="temperature_f",
        labels={"temperature_f": "Temperature (°F)", "timestamp": "Date"},
        title=f"{device_id} — Temperature Record",
    )
    st.plotly_chart(fig_temp, use_container_width=True, key="m8r1_temp_time")

if "delta_temperature_f" in filtered.columns and filtered["delta_temperature_f"].notna().any():
    fig_dtemp = px.line(
        filtered,
        x="timestamp",
        y="delta_temperature_f",
        labels={"delta_temperature_f": "ΔTemp (°F)", "timestamp": "Date"},
        title=f"{device_id} — Delta Temperature",
    )
    st.plotly_chart(fig_dtemp, use_container_width=True, key="m8r1_delta_temp_time")

if "calculated_expansion_in" in filtered.columns and filtered["calculated_expansion_in"].notna().any():
    fig_calc = px.line(
        filtered,
        x="timestamp",
        y="calculated_expansion_in",
        labels={"calculated_expansion_in": "Calculated thermal expansion (in)", "timestamp": "Date"},
        title=f"{device_id} — Pre-computed Calculated Thermal Expansion",
    )
    st.plotly_chart(fig_calc, use_container_width=True, key="m8r1_calc_thermal_time")

# ── Linear thermal regression ─────────────────────────────────────────────────

st.subheader("Simple linear thermal correction model")
st.markdown(
    f"Fitting: **{regression_col}** = slope × temperature_f + intercept  "
    "(screening-level regression only)"
)

if "temperature_f" not in filtered.columns or filtered["temperature_f"].notna().sum() < 5:
    st.warning("Insufficient temperature data for regression.")
else:
    corrected_df, model_stats = compute_linear_thermal_correction(
        filtered, regression_col, "temperature_f"
    )

    stats_display = {
        "Slope (in/°F)": f"{model_stats['slope']:.4f}" if model_stats["status"] == "ok" else "N/A",
        "Intercept (in)": f"{model_stats['intercept']:.4f}" if model_stats["status"] == "ok" else "N/A",
        "R²": f"{model_stats['r_squared']:.4f}" if model_stats["status"] == "ok" else "N/A",
        "Records used": str(model_stats["record_count"]),
        "Status": model_stats["status"],
    }
    st.markdown("**Linear model statistics**")
    st.table(pd.DataFrame(stats_display, index=["Value"]).T)
    st.caption(
        "**R²** — fraction of measured movement variance explained by the linear temperature model. "
        "Low R² (e.g. < 0.3) indicates that structural or other non-thermal factors dominate the signal. "
        "**Slope (in/°F)** — negative slope means joint closes as temperature rises (as expected for thermal expansion). "
        "This is a simple linear screening model; it does not fully isolate structural movement."
    )

    if model_stats["status"] != "ok":
        st.warning(f"Linear model not fitted: {model_stats['status']}")
    else:
        st.caption(
            f"R² = {model_stats['r_squared']:.3f} — temperature explains "
            f"{model_stats['r_squared']*100:.1f}% of variance in {regression_col}. "
            "A low R² indicates that structural or other non-thermal factors dominate."
        )

        fig_scatter = px.scatter(
            corrected_df,
            x="temperature_f",
            y=regression_col,
            trendline="ols",
            labels={
                "temperature_f": "Temperature (°F)",
                regression_col: f"{regression_col} (in)",
            },
            title=f"{device_id}: {regression_col} vs Temperature — Linear Fit",
        )
        st.plotly_chart(fig_scatter, use_container_width=True, key="m8r1_scatter_temp_movement")

        if "thermal_corrected_residual_in" in corrected_df.columns:
            fig_resid = px.line(
                corrected_df,
                x="timestamp",
                y="thermal_corrected_residual_in",
                labels={"thermal_corrected_residual_in": "Residual (in)", "timestamp": "Date"},
                title=f"{device_id} — Linear Temperature-Corrected Residual Over Time",
            )
            fig_resid.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            st.plotly_chart(fig_resid, use_container_width=True, key="m8r1_residual_time")
            st.caption(
                "Residual = measured movement minus the linearly predicted thermal component. "
                "Persistent non-zero residual or trends may indicate non-thermal movement, "
                "but requires engineering review to interpret."
            )

# ── Year-over-year low-temperature comparison ─────────────────────────────────

st.subheader("Low-temperature year-over-year comparison")

if "temperature_f" in device_df.columns and device_df[corrected_col].notna().any():
    yearly = compare_low_temperature_windows(
        device_df, "temperature_f", corrected_col, temp_percentile=temp_percentile
    )

    if yearly.empty:
        st.info("No records available for the low-temperature comparison.")
    else:
        n_years = len(yearly)
        if n_years == 1:
            st.info(
                f"Only one year of data in view ({int(yearly['year'].iloc[0])}). "
                "Year-over-year comparison requires multiple years of records."
            )

        st.markdown(
            f"Records at or below the {temp_percentile}th temperature percentile "
            f"(≤ {yearly['temperature_threshold_f'].iloc[0]:.1f} °F)."
        )
        st.dataframe(yearly, use_container_width=True, hide_index=True)

        if n_years > 1:
            fig_yor = px.bar(
                yearly,
                x="year",
                y="median_corrected_expansion_in",
                error_y=yearly["max_corrected_expansion_in"] - yearly["median_corrected_expansion_in"],
                error_y_minus=yearly["median_corrected_expansion_in"] - yearly["min_corrected_expansion_in"],
                labels={
                    "year": "Year",
                    "median_corrected_expansion_in": f"Median corrected expansion — {corrected_col} (in)",
                },
                title=f"{device_id} — Median Corrected Expansion at Low Temperature (≤ {temp_percentile}th pct)",
            )
            st.plotly_chart(fig_yor, use_container_width=True, key="m8r1_yor_bar")
        else:
            st.caption("Bar chart requires at least two years of data.")
else:
    st.info("Temperature or corrected expansion data not available for year-over-year comparison.")

# ── Engineering interpretation ────────────────────────────────────────────────

st.subheader("Engineering interpretation")
st.markdown(
    f"""
**Key observations from this screening-level analysis for {device_id}:**

- Jointmeter readings combine a **thermal component** (joint closes in heat, opens in cold)
  and a **structural component** (long-term trend from pier movement and span jacking history).
- The pre-computed thermally corrected column (`corrected_expansion_in`) removes the calculated
  thermal expansion using span length and the steel coefficient of thermal expansion.
- The simple linear regression provides an independent, data-driven estimate of the temperature
  signal. Agreement between the linear residual and the pre-computed corrected series supports
  confidence in the correction approach.
- Trends in the corrected expansion across seasons or years — particularly under similar
  low-temperature conditions — may indicate residual structural movement and warrant field
  verification.

**Important.** This tool supports monitoring-based, screening-level interpretation only. It does
not replace structural analysis, field measurement, bridge inspection, or engineering judgment.
Any apparent trend should be reviewed by a qualified bridge engineer before action.
"""
)

st.info(
    "Jointmeter thermal correction — R1 primary device sheets. "
    "No black-box ML. Screening-level interpretation only."
)
