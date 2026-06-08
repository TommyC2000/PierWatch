# PierWatch Engineering Logic

## Project positioning

PierWatch is a monitoring-based decision-support prototype, not a complete FE-based digital twin.

## Primary monitoring layout

The bridge monitoring workbook centers on four primary device / location sheets:

| Sheet | Role |
|---|---|
| `W2` | Pier W-2 — part of the broader jointmeter / monitoring network |
| `PP 15` | PP-15 expansion joint — critical joint clearance and span-jacking risk location |
| `E2` | Pier E-2 — movement transfer and joint response |
| `E3` | Pier E-3 — movement transfer and joint response |

Primary hydrology source: `River Stage 2000-2026`

The standalone `GPS Data` sheet is used for event-based movement tracking (R1 standalone GPS source). It is not the primary device data table.

## Primary intended workflow

```
River Stage 2000-2026
→ low-water event detection
→ primary monitoring locations: W2 / PP15 / E2 / E3
→ pier / joint response interpretation
→ PP-15 clearance risk screening
→ engineering summary
```

## Currently implemented workflow (R1 prototype)

```
River Stage 2000-2026
→ low-water event detection
→ GPS Data parser (standalone GPS movement tracking)
→ E-1/E-2 coupling analysis (based on GPS workflow)
→ PP-15 risk screening
→ Primary device sheets (W2, PP 15, E2, E3) — jointmeter and thermal correction
→ sensor confidence (all implemented streams)
→ engineering summary
```

## Mechanism

Low river stage creates conditions where pier movement becomes possible or likely. E-1 and E-2 tend to move toward the channel at similar time and magnitude. This mechanism causes E-3 joint opening and PP-15 joint closing. If PP-15 closes completely, compression forces may build up in the span. Therefore, PP-15 remaining clearance and E-1 movement are key warning indicators.

## Report-based thresholds

- River stage < 12 ft: movement possible.
- River stage < 7 ft: movement likely.
- 2022 peak movement rate: approximately 1 inch per 10 days, or 0.10 in/day.
- Remaining allowable movement before next span jacking: approximately 0.5 in.

## Suggested research framing

The most interesting research question is not generic anomaly detection. It is the nonstationary relationship between low-water exposure and pier movement. The 2022 event appears to be a high-sensitivity outlier, while later low-water events produced smaller movement. This suggests history effects, hysteresis, soil-pier interaction, and remediation state may matter.
