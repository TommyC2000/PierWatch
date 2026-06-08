# PierWatch

**Data-Driven Event Detection and Multi-Sensor Interpretation for Smart Bridge Infrastructure**

PierWatch is a screening-level SHM analytics prototype that demonstrates how river-stage records, GPS movement data, and jointmeter/device responses can be integrated into an interpretable monitoring workflow.

> **Public version notice:** The public GitHub version uses synthetic, anonymized demo data only. Real project names, bridge identifiers, monitoring records, and original reports are not included.

> **Scope disclaimer:** This is a research/portfolio prototype, not a full finite-element digital twin, not an official engineering report, and not a structural safety evaluation.

---

## Quick Start — Public Demo Mode

```bash
pip install -r requirements.txt
PIERWATCH_DATA_MODE=demo streamlit run PierWatch.py
```

This runs the app with synthetic, anonymized demo data. No private files are needed.

---

## Recommended Demo Workflow

Work through these pages in order for the clearest research narrative:

| Step | Page | What it shows |
|---|---|---|
| 1 | **Low-Water Event Detector** | Which years had significant low-water exposure; Low-Water Severity Index (LWSI) per event |
| 2 | **Pier Movement Tracker** | GPS-based E-1/E-2/E-3 pier movement per event; E-1/E-2 coupling analysis |
| 3 | **Primary Device Comparison** | Cross-device jointmeter availability, trends, and event-window changes (W2, PP15, E2, E3) |
| 4 | **PP-15 Joint Clearance Risk** | Remaining movement allowance under a continued low-water scenario |
| 5 | **Research Insights** | Movement sensitivity, hysteresis patterns, multi-sensor interpretation |
| 6 | **Engineering Summary** | Consolidated screening-level report for a selected event and scenario |

---

## Research Relevance

PierWatch demonstrates how a long-term SHM monitoring dataset — without new sensors — can be restructured into an event-driven, interpretable decision-support tool. It is relevant to:

- **Smart bridge infrastructure and SHM analytics** — converting passive sensor records into structured, queryable event indicators
- **Low-water event detection** — automated identification and severity ranking of river stage exposure periods
- **GPS-based pier movement tracking** — event-window movement estimates from displacement records
- **Jointmeter and multi-sensor response interpretation** — cross-device comparison, thermal correction, and coupling analysis
- **Sensor data quality assessment** — completeness, coverage, and confidence scoring across monitoring streams
- **Interpretable engineering decision-support** — screening-level risk outputs grounded in physical mechanism rather than black-box prediction
- **Movement sensitivity and hysteresis research** — the dataset structure supports investigation of nonstationary bridge response across repeated low-water exposures

---

## Interpreted Monitoring Mechanism

Low River Stage → E-1/E-2 Pier Movement Toward Channel → E-3 Joint Opening and PP-15 Joint Closing → Reduced Remaining Joint Clearance → Span Jacking Risk

---

## Analytics Workflow

```
River Stage (2000–2026)
  → Low-water event detection
  → Low-Water Severity Index (LWSI) per event

GPS Pier Positions (GPS era)
  → E-1/E-2/E-3 longitudinal and transverse movement per event
  → E-1/E-2 coupling analysis

Primary Device Sheets (W2, PP 15, E2, E3)
  → Jointmeter time-series, thermal correction, cross-device comparison

PP-15 Risk Screening
  → Remaining allowance + scenario movement rate → risk level

Engineering Summary
  → Consolidated screening-level report for any selected event
```

---

## Engineering Thresholds (Screening-Level)

- River stage **< 12 ft**: pier movement becomes possible.
- River stage **< 7 ft**: pier movement is likely.
- Reference movement-rate scenario: ~0.10 in/day.
- Reference remaining movement allowance scenario: ~0.5 in.

These thresholds are derived from source monitoring documentation and are used only for screening-level demonstration purposes.

---

## Pages

| Page | Engineering question |
|---|---|
| Data Overview | What sheets are in the workbook, and where do headers start? |
| Low-Water Event Detector | Which years had significant low-water exposure, and how severe? |
| Pier Movement Tracker | How did E1/E2/E3 move during a selected event? Are E1 and E2 coupled? |
| PP-15 Joint Clearance Risk | Under a given scenario, what is the projected risk level? |
| Year-to-Year Sensitivity | How does pier movement scale with low-water severity across events? |
| Jointmeter Thermal Correction | How much of PP-15/E2/E3 joint movement is temperature-driven? |
| Sensor Data Quality | What is the completeness and confidence of each monitoring stream? |
| Engineering Summary | Consolidated screening report for a selected event and scenario. |
| Primary Device Comparison | Cross-device jointmeter availability, trends, and event-window changes. |
| Research Insights | Movement sensitivity, hysteresis, and multi-sensor interpretation. |

---

## Data Privacy and Public Demo Mode

Raw monitoring data, original workbooks, and engineering reports are **confidential and are not included in this repository**.

- `data/raw/` is excluded via `.gitignore` — no raw files are committed.
- The public version uses synthetic CSV files in `data/demo/` only.
- Demo data files are computer-generated and do not represent actual bridge monitoring records.
- No engineering conclusions should be drawn from synthetic demo-mode outputs.
- The public version is for research portfolio demonstration only.

To regenerate demo data from scratch:

```bash
python scripts/create_demo_data.py
PIERWATCH_DATA_MODE=demo streamlit run PierWatch.py
```

See [`docs/PUBLIC_DEMO_MODE.md`](docs/PUBLIC_DEMO_MODE.md) for full details.

---

## Local / Private Mode

**Public users should use demo mode** (see Quick Start above). Local mode requires a private monitoring workbook placed in `data/raw/`, which is **not included in this repository**. Without that file, local mode will not load data.

```bash
# Requires private monitoring workbook in data/raw/ — not included in public repo
streamlit run PierWatch.py
```

---

## Limitations

- **Synthetic public data.** The public demo dataset does not represent an official bridge monitoring record. Values are computer-generated for workflow demonstration only.
- **Screening-level analysis only.** PierWatch does not replace field inspection, FE analysis, or engineering judgment.
- **Not a structural safety evaluation.** No safety conclusions should be drawn from any PierWatch output.
- **Not a full digital twin.** PierWatch does not implement physics-based simulation or finite-element modeling.
- **GPS-era only for movement tracking.** GPS data covers the GPS-era period only; earlier events have no GPS-derived movement estimates.
- **W2 sensor discontinued.** W2 monitoring ended before the GPS era and does not contribute to GPS-era event comparisons.
- **Linear thermal model is a screening approximation.** The OLS fit on temperature does not fully isolate structural movement from thermal signal.
- **Local/private workflow** may use a fuller private dataset not included in this repository.
