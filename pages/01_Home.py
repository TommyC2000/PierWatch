import streamlit as st
import plotly.graph_objects as go
from src.data_sources import show_mode_banner


def _monitoring_schematic() -> go.Figure:
    """
    Simplified, anonymized conceptual bridge monitoring schematic.
    Drawn entirely in code — no original plan image, no private geometry.
    Warren truss panels for central spans; plain engineering-style linework.
    """
    fig = go.Figure()

    chord_y = 2.8          # bottom chord / deck
    top_y   = chord_y + 0.82  # truss top chord
    e1, e2, e3 = 3.0, 6.0, 9.0
    app_l, app_r = 0.8, 11.2

    # ── Channel / water zone (very subtle fill + dashed water surface) ────────
    fig.add_shape(
        type="rect", x0=1.8, y0=0.0, x1=10.2, y1=1.45,
        fillcolor="rgba(190,220,245,0.20)",
        line=dict(color="rgba(90,150,200,0.30)", width=0.7),
        layer="below",
    )
    fig.add_shape(
        type="line", x0=1.8, y0=1.45, x1=10.2, y1=1.45,
        line=dict(color="rgba(80,140,200,0.50)", width=0.9, dash="dot"),
    )
    fig.add_annotation(
        x=6.0, y=0.6, text="channel",
        showarrow=False, font=dict(size=8, color="rgba(55,105,165,0.60)"),
    )

    # ── Bottom chord (full span) ──────────────────────────────────────────────
    fig.add_shape(
        type="line", x0=0.0, y0=chord_y, x1=12.0, y1=chord_y,
        line=dict(color="#222222", width=1.8),
    )

    # ── Warren truss panels (central spans only) ──────────────────────────────
    def _truss(x0, x1, n=4):
        pw = (x1 - x0) / n
        fig.add_shape(                          # top chord
            type="line", x0=x0, y0=top_y, x1=x1, y1=top_y,
            line=dict(color="#3a3a3a", width=1.1),
        )
        for i in range(n):                      # Warren diagonals (no verticals)
            xl, xr = x0 + i * pw, x0 + (i + 1) * pw
            if i % 2 == 0:
                fig.add_shape(type="line", x0=xl, y0=chord_y, x1=xr, y1=top_y,
                              line=dict(color="#585858", width=0.85))
            else:
                fig.add_shape(type="line", x0=xl, y0=top_y, x1=xr, y1=chord_y,
                              line=dict(color="#585858", width=0.85))

    _truss(e1, e2)
    _truss(e2, e3)

    # ── Approach piers — unlabeled, thin dashed ───────────────────────────────
    for xp in (app_l, app_r):
        fig.add_shape(
            type="line", x0=xp, y0=0.0, x1=xp, y1=chord_y,
            line=dict(color="#c0c0c0", width=1.1, dash="dot"),
        )

    # ── Monitored piers: E1, E2, E3 ──────────────────────────────────────────
    for xp in (e1, e2, e3):
        fig.add_shape(
            type="line", x0=xp, y0=0.0, x1=xp, y1=chord_y,
            line=dict(color="#2e2e2e", width=1.7),
        )
        fig.add_shape(                          # footing spread
            type="line", x0=xp - 0.22, y0=0.0, x1=xp + 0.22, y1=0.0,
            line=dict(color="#2e2e2e", width=1.7),
        )

    # ── Monitoring sensor dots at deck level ──────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[e1, e2, e3], y=[chord_y, chord_y, chord_y],
        mode="markers",
        marker=dict(symbol="circle", size=7, color="#c0392b",
                    line=dict(color="#922b21", width=1)),
        showlegend=False, hoverinfo="skip",
    ))

    # ── Pier labels below deck ────────────────────────────────────────────────
    for label, xp in (("E1", e1), ("E2", e2), ("E3", e3)):
        fig.add_annotation(
            x=xp, y=chord_y - 0.38, text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=10, color="#1a1a1a"),
        )

    # ── Device labels — plain small italic text, no box ───────────────────────
    dev_y = chord_y + 0.17
    for dx, dlabel in [
        (1.75,               "W2"),
        ((e1 + e2) / 2,      "PP15"),
        (e2 + 0.38,          "E2"),
        (e3 + 0.38,          "E3"),
    ]:
        fig.add_annotation(
            x=dx, y=dev_y, text=dlabel,
            showarrow=False,
            font=dict(size=7.5, color="#5a5a5a", style="italic"),
        )

    # ── GPS markers above truss top chord ────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[e1, e2, e3], y=[top_y + 0.30, top_y + 0.30, top_y + 0.30],
        mode="markers+text",
        marker=dict(symbol="triangle-up", size=7, color="#27ae60",
                    line=dict(color="#1e8449", width=0.7)),
        text=["GPS", "GPS", "GPS"],
        textposition="top center",
        textfont=dict(size=7, color="#27ae60"),
        showlegend=False, hoverinfo="skip",
    ))

    # ── Movement arrow in channel zone (data-coordinate anchor) ───────────────
    fig.add_annotation(
        x=e1 + 1.6, y=0.92,       # arrowhead: in channel, right of E1
        ax=e1 - 0.1, ay=0.92,     # text anchor: just left of E1 base
        xref="x", yref="y", axref="x", ayref="y",
        text="<i>low-water movement</i>",
        showarrow=True, arrowhead=2, arrowsize=0.85,
        arrowwidth=1.1, arrowcolor="#a84200",
        font=dict(size=7.5, color="#a84200"),
    )

    # ── W / E orientation marks at deck edges ─────────────────────────────────
    fig.add_annotation(
        x=0.05, y=chord_y + 0.14, text="W",
        showarrow=False, font=dict(size=8, color="#b0b0b0"), xanchor="left",
    )
    fig.add_annotation(
        x=11.95, y=chord_y + 0.14, text="E",
        showarrow=False, font=dict(size=8, color="#b0b0b0"), xanchor="right",
    )

    # ── Layout ────────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="Engineering Background: Conceptual Monitoring Layout",
            font=dict(size=11.5, color="#3a3a3a"),
            x=0.5, xanchor="center", y=0.99, yanchor="top",
        ),
        height=360,
        margin=dict(l=8, r=8, t=36, b=8),
        xaxis=dict(visible=False, range=[-0.5, 12.5]),
        yaxis=dict(visible=False, range=[-0.65, 5.0]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode=False,
    )
    fig.update_traces(hoverinfo="skip", hovertemplate=None)
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
    "PierWatch is motivated by monitoring cases where water level, support movement, "
    "and joint/device response need to be interpreted together."
)
st.plotly_chart(
    _monitoring_schematic(),
    use_container_width=True,
    key="home_schematic",
    config={"displayModeBar": False},
)
st.caption("Conceptual schematic. Not an original bridge plan.")

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
