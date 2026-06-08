import streamlit as st
import plotly.graph_objects as go
from src.data_sources import show_mode_banner


def _monitoring_schematic() -> go.Figure:
    """
    Simplified, anonymized conceptual bridge monitoring schematic.
    Drawn entirely in code — no original plan image, no private geometry.
    """
    fig = go.Figure()
    deck_y = 3.5

    # ── River / channel zone ─────────────────────────────────────────────────
    fig.add_shape(
        type="rect", x0=2.3, y0=0.0, x1=7.7, y1=1.8,
        fillcolor="rgba(173,216,230,0.35)",
        line=dict(color="rgba(70,130,180,0.4)", width=1),
        layer="below",
    )
    fig.add_annotation(
        x=5.0, y=0.9, text="Generic river / channel zone",
        showarrow=False, font=dict(size=10, color="#3a6ea5"),
        bgcolor="rgba(255,255,255,0.55)",
    )

    # ── Deck line ────────────────────────────────────────────────────────────
    fig.add_shape(
        type="line", x0=0.0, y0=deck_y, x1=10.0, y1=deck_y,
        line=dict(color="#2c2c2c", width=3.5),
    )
    # Thin top chord — suggests superstructure depth without truss detail
    fig.add_shape(
        type="line", x0=0.0, y0=deck_y + 0.35, x1=10.0, y1=deck_y + 0.35,
        line=dict(color="#666666", width=1, dash="dot"),
    )

    # ── Approach piers — unlabeled, dashed ───────────────────────────────────
    for xp in (0.5, 9.5):
        fig.add_shape(
            type="line", x0=xp, y0=0.0, x1=xp, y1=deck_y,
            line=dict(color="#bbbbbb", width=2, dash="dot"),
        )

    # ── Monitored piers: E1, E2, E3 ──────────────────────────────────────────
    piers = {"E1": 3.0, "E2": 5.0, "E3": 7.0}
    for label, xp in piers.items():
        fig.add_shape(
            type="line", x0=xp, y0=0.0, x1=xp, y1=deck_y,
            line=dict(color="#333333", width=3),
        )
        # Footing spread at base
        fig.add_shape(
            type="line", x0=xp - 0.3, y0=0.0, x1=xp + 0.3, y1=0.0,
            line=dict(color="#333333", width=3),
        )
        fig.add_annotation(
            x=xp, y=2.2, text=f"<b>{label}</b>",
            showarrow=False, font=dict(size=12, color="#111111", family="monospace"),
            bgcolor="rgba(255,255,255,0.82)", borderpad=2,
        )

    # ── GPS monitoring markers above deck ────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[3.0, 5.0, 7.0],
        y=[4.65, 4.65, 4.65],
        mode="markers+text",
        marker=dict(
            symbol="triangle-up", size=13, color="#2ca02c",
            line=dict(color="#1a7a1a", width=1),
        ),
        text=["GPS · E1", "GPS · E2", "GPS · E3"],
        textposition="top center",
        textfont=dict(size=9, color="#1a7a1a"),
        showlegend=False,
        hoverinfo="skip",
    ))

    # ── Device / joint labels at deck level ───────────────────────────────────
    # Staggered slightly from pier centerlines to avoid overlap with GPS markers
    device_y = deck_y + 0.6
    devices = [
        (1.5, "W2 Device",  "#7B3F00"),
        (4.0, "PP15 Joint", "#8B0000"),
        (5.3, "E2 Device",  "#8B0000"),
        (7.3, "E3 Device",  "#8B0000"),
    ]
    for dx, dlabel, dcolor in devices:
        fig.add_annotation(
            x=dx, y=device_y, text=dlabel,
            showarrow=False,
            font=dict(size=9, color=dcolor),
            bgcolor="rgba(255,243,243,0.92)",
            bordercolor=dcolor, borderwidth=1, borderpad=2,
        )

    # ── Movement response arrow ───────────────────────────────────────────────
    # Arrow tail is 85 px to the left of arrowhead (pixel offset, no axref/ayref)
    # Arrowhead points into the channel zone near E1, indicating pier movement direction
    fig.add_annotation(
        x=4.1, y=1.3,
        ax=-90, ay=0,
        text="possible low-water<br>movement response",
        showarrow=True, arrowhead=3, arrowsize=1.2,
        arrowwidth=2, arrowcolor="#CC4400",
        font=dict(size=9, color="#CC4400"),
        bgcolor="rgba(255,255,255,0.88)", borderpad=3,
    )

    # ── West / East orientation labels ───────────────────────────────────────
    fig.add_annotation(
        x=0.0, y=deck_y, text="← West",
        showarrow=False, font=dict(size=9, color="#888888"),
        xanchor="right",
    )
    fig.add_annotation(
        x=10.0, y=deck_y, text="East →",
        showarrow=False, font=dict(size=9, color="#888888"),
        xanchor="left",
    )

    # ── Disclaimer ───────────────────────────────────────────────────────────
    fig.add_annotation(
        x=0.0, y=-0.6, xref="x", yref="y",
        text="Conceptual schematic — not an original plan.",
        showarrow=False, font=dict(size=9, color="#aaaaaa"), xanchor="left",
    )

    fig.update_layout(
        title=dict(
            text="Engineering Background: Conceptual Monitoring Layout",
            font=dict(size=13, color="#333333"),
            x=0.5, xanchor="center",
        ),
        height=390,
        margin=dict(l=20, r=20, t=48, b=30),
        xaxis=dict(visible=False, range=[-0.6, 10.6]),
        yaxis=dict(visible=False, range=[-0.9, 6.3]),
        plot_bgcolor="rgba(248,248,248,0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


st.title("Home / Engineering Story")

show_mode_banner()

st.markdown("""
## PierWatch
**Engineering-Informed SHM Early Warning for Low-Water-Induced Bridge Pier Movement**

PierWatch is a screening-level SHM analytics prototype for data-driven event detection and multi-sensor interpretation using a synthetic public demo dataset.

> **Public version notice:** The public GitHub version uses synthetic, anonymized demo data. Real project names, bridge identifiers, and monitoring records are not included.

> **This is a monitoring-based decision-support prototype, not a full FE-based digital twin or official engineering report.**

### Physical Mechanism
Low River Stage → E-1 / E-2 Pier Movement Toward Channel → E-3 Joint Opening and PP-15 Joint Closing → Reduced Remaining Joint Clearance → Span Jacking Risk

### Report-based thresholds
- River stage below **12 ft**: pier movement becomes possible.
- River stage below **7 ft**: pier movement is likely.
- 2022 reference peak movement rate: about **0.10 in/day**.
- Remaining allowable movement before another jacking operation: about **0.5 in**.
""")

st.markdown("---")

st.markdown(
    "PierWatch is motivated by bridge monitoring cases where environmental loading, "
    "support movement, and joint/device responses must be interpreted together. "
    "The schematic below illustrates the monitoring workflow in a simplified and anonymized form."
)
st.plotly_chart(_monitoring_schematic(), use_container_width=True, key="home_schematic")
st.caption(
    "Simplified anonymized schematic for demonstration only. "
    "Geometry, labels, and monitoring locations are conceptual and do not represent an original bridge plan."
)

st.markdown("---")

st.markdown("""
### Recommended Demo Path

Work through these pages in order for the clearest narrative:

| Step | Page | What to look for |
|---|---|---|
| 1 | **Low-Water Event Detector** | Identify which years had significant low-water exposure and compare severity via LWSI. |
| 2 | **Pier Movement Tracker** | Select event LW-050 (2022) to see the largest GPS-era movement — E1 ≈ 4.2 in, E2 ≈ 3.8 in — and examine E-1/E-2 coupling. |
| 3 | **Primary Device Comparison** | Compare cross-device jointmeter records (W2, PP15, E2, E3) and check data availability across the full 2004–2026 record. |
| 4 | **PP-15 Joint Clearance Risk** | Adjust remaining allowance and scenario days to demonstrate how quickly the risk level changes. |
| 5 | **Engineering Summary** | Select LW-050 for a full consolidated report across all monitoring streams. |

### Recommended Demo Events

| Event | Year | Why useful |
|---|---|---|
| **LW-050** | 2022 | Best for demo — largest GPS-era movement, E1/E2 coupling, emergency-response reference, most complete monitoring record. |
| **LW-058** | 2025 | Best for recent-monitoring context — shows post-remediation movement levels under comparable exposure. |

---

### Monitoring Layout and Data Scope

The monitoring workbook centers on four primary device / location sheets: **W2**, **PP 15**, **E2**, and **E3**, plus the primary hydrology record **River Stage 2000-2026**.

The current prototype uses the workbook-level `GPS Data` sheet as the standalone GPS movement tracking source for event-based analysis.
Primary jointmeter data from the four primary device sheets is integrated on the Primary Device Comparison page.

---

### Data Privacy Note

This local version uses private monitoring data from `data/raw/`. The raw workbook and engineering reports are confidential.

**Public GitHub / portfolio versions should use synthetic demo data only.** See `docs/PUBLIC_DEMO_MODE.md` and run `python scripts/create_demo_data.py` to generate synthetic demo files.
""")
