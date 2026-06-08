import math

import plotly.graph_objects as go
import streamlit as st

from src.pp15_risk import (
    DEFAULT_REMAINING_ALLOWABLE_IN,
    MOVEMENT_RATE_PRESETS,
    compute_pp15_risk,
    simulate_additional_movement,
)
from src.data_sources import show_mode_banner


st.title("PP-15 Joint Clearance Risk")
st.caption("Engineering Question: How much remaining movement allowance may be consumed under a continued low-water scenario?")

show_mode_banner()

st.warning(
    "This is a screening-level monitoring interpretation and does not replace field measurements, structural analysis, or engineering judgment."
)

remaining = st.number_input(
    "Remaining allowable movement before possible span jacking (in)",
    value=DEFAULT_REMAINING_ALLOWABLE_IN,
    step=0.05,
    help=(
        "Approximate remaining longitudinal movement allowance before another span-jacking "
        "operation may need to be considered. Default is based on source monitoring documentation "
        "and should be treated as a screening-level estimate."
    ),
)
days_below_7 = st.number_input(
    "Additional days below 7 ft", value=10.0, min_value=0.0, step=1.0,
    help=(
        "Scenario assumption for continued low-water exposure. "
        "Engineering thresholds indicate movement is likely when river stage is below 7 ft."
    ),
)

preset_options = [f"{name}: {rate:.2f} in/day" for name, rate in MOVEMENT_RATE_PRESETS.items()] + ["Custom"]
preset = st.selectbox(
    "Movement rate preset", preset_options, index=1,
    help=(
        "Assumed movement rate for screening scenario. "
        "The 2022-like rate (~0.10 in/day) is based on the reported peak movement rate "
        "of approximately 1 inch every 10 days."
    ),
)
if preset == "Custom":
    movement_rate = st.number_input("Custom movement rate (in/day)", value=0.02, min_value=0.0, step=0.01)
else:
    preset_name = preset.split(":", 1)[0]
    movement_rate = MOVEMENT_RATE_PRESETS[preset_name]

predicted = simulate_additional_movement(days_below_7, movement_rate)
risk = compute_pp15_risk(remaining_allowable_in=remaining, predicted_additional_movement_in=predicted)
risk_ratio = risk["risk_ratio"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Predicted additional movement (in)", f"{predicted:.2f}",
          help="Predicted additional movement = additional days × movement rate. Screening estimate only.")
c2.metric("Remaining clearance after scenario (in)", f"{risk['remaining_after_scenario_in']:.2f}",
          help="Remaining allowable movement minus predicted additional movement. May be negative if scenario exceeds the allowance.")
c3.metric("Risk ratio", "∞" if math.isinf(risk_ratio) else f"{risk_ratio:.2f}",
          help="Predicted additional movement divided by remaining allowable movement. A screening-level indicator, not a structural safety factor.")
c4.metric("Risk level", risk["risk_level"],
          help="Screening category: Normal (<0.5), Watch (0.5–0.8), Critical (0.8–1.0), Span Jacking Likely (≥1.0). Does not replace field measurements or engineering judgment.")

risk_level = risk["risk_level"]
if risk_level == "Normal":
    st.success(f"Screening risk level: **{risk_level}**")
elif risk_level == "Watch":
    st.warning(f"Screening risk level: **{risk_level}**")
else:
    st.error(f"Screening risk level: **{risk_level}** — engineering review recommended.")

gauge_value = 1.2 if math.isinf(risk_ratio) else min(float(risk_ratio), 1.2)
fig = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=gauge_value,
        number={"valueformat": ".2f"},
        title={"text": "PP-15 Screening Risk Ratio"},
        gauge={
            "axis": {"range": [0, 1.2]},
            "bar": {"color": "#1f77b4"},
            "steps": [
                {"range": [0, 0.5], "color": "#d9ead3"},
                {"range": [0.5, 0.8], "color": "#fff2cc"},
                {"range": [0.8, 1.0], "color": "#f4cccc"},
                {"range": [1.0, 1.2], "color": "#e06666"},
            ],
            "threshold": {"line": {"color": "black", "width": 3}, "thickness": 0.75, "value": 1.0},
        },
    )
)
fig.update_layout(height=300, margin={"l": 20, "r": 20, "t": 50, "b": 10})
st.plotly_chart(fig, use_container_width=True, key="m6_risk_gauge")

with st.expander("How is PP-15 risk calculated?"):
    st.markdown(
        """
**PP-15 risk calculation (screening-level):**

- **Predicted additional movement** = additional days below 7 ft × movement rate (in/day)
- **Risk ratio** = predicted additional movement ÷ remaining allowable movement
- **Risk levels:**
  - **Normal** (ratio < 0.5): Predicted movement is less than half the remaining allowance.
  - **Watch** (0.5 ≤ ratio < 0.8): Predicted movement is approaching the remaining allowance.
  - **Critical** (0.8 ≤ ratio < 1.0): Predicted movement is close to exhausting the remaining allowance.
  - **Span Jacking Likely** (ratio ≥ 1.0): Predicted movement equals or exceeds the remaining allowance.

This is a screening-level scenario, not a structural analysis. It does not replace field
measurements, structural analysis, bridge inspection, or engineering judgment.
"""
    )

st.subheader("Recommended Action")
st.write(risk["recommendation"])

with st.expander("Scenario details", expanded=False):
    st.write(
        {
            "remaining_allowable_in": risk["remaining_allowable_in"],
            "additional_days_below_7": days_below_7,
            "movement_rate_in_per_day": movement_rate,
            "predicted_additional_movement_in": risk["predicted_additional_movement_in"],
            "remaining_after_scenario_in": risk["remaining_after_scenario_in"],
            "risk_ratio": "infinite" if math.isinf(risk_ratio) else risk_ratio,
            "risk_level": risk["risk_level"],
        }
    )

st.info("Milestone 6 implements PP-15 screening only. Year-to-Year Sensitivity and PP-15 Filter thermal correction are intentionally not implemented here.")
