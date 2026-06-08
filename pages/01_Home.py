import streamlit as st
from src.data_sources import show_mode_banner

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

---

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
