# PierWatch — Public / Portfolio Demo Mode

## What is confidential

The following files are **confidential and must NOT be committed to any public repository**:

| File | Status |
|---|---|
| `data/raw/Jointmeters w GPS R1.xlsx` | Confidential — real monitoring workbook |
| `data/raw/Jointmeters w GPS R0.xlsx` | Confidential — prior workbook version |
| `data/raw/*.docx` | Confidential — engineering reports |
| `data/raw/*.pdf` | Confidential — engineering reports |
| Any original sensor data files | Confidential |

These files are listed in `.gitignore` and will not be tracked by git.

---

## Running in local mode (default)

Local mode uses the real R1 workbook. This is the default for private analysis.

```bash
# Default — no environment variable needed
streamlit run PierWatch.py

# Or explicitly:
PIERWATCH_DATA_MODE=local streamlit run PierWatch.py
```

Requirements:
- `data/raw/Jointmeters w GPS R1.xlsx` must be present
- All 10 Streamlit pages load with full data

---

## Running in demo mode (public / portfolio)

Demo mode uses synthetic CSV files from `data/demo/`. It is intended for public GitHub
portfolios, conference demos, or situations where the real workbook cannot be shared.

### Phase 1: Generate synthetic demo data

Run the data generation script **once**:

```bash
python scripts/create_demo_data.py
```

This creates four synthetic CSV files in `data/demo/`:

| File | Contents |
|---|---|
| `demo_river_stage.csv` | Synthetic daily river stage, 2000–2026 |
| `demo_gps_data.csv` | Synthetic GPS pier positions, 2022–2026 |
| `demo_device_data.csv` | Synthetic jointmeter readings (PP15, E2, E3, W2) |
| `demo_events.csv` | Pre-computed low-water events from synthetic stage |

**Important:** These files contain synthetic, perturbed values. They are not copies of
the real monitoring data and should not be used for engineering decisions.

### Phase 2: Wire demo loaders (implemented)

Full demo-mode integration is complete. All PierWatch pages route through
`src/data_sources.py`, which selects demo CSV loaders or local Excel loaders
based on `DATA_MODE`.

Key new modules:
- `src/demo_data_loader.py` — CSV-based loaders returning the same column schema as local loaders
- `src/data_sources.py` — mode-aware wrappers (`get_river_stage_data`, `get_gps_data`, etc.)

## Running in demo mode

```bash
PIERWATCH_DATA_MODE=demo streamlit run PierWatch.py
```

All pages (01–11) will display a demo-mode banner and load synthetic CSV data.
Page 02 (Data Overview) stops gracefully with a notice — workbook structure
inspection requires the R1 workbook.

---

## What demo data preserves (and what it changes)

| Aspect | Preserved in demo data |
|---|---|
| Column names and dtypes | Yes — same schema as real data |
| Date range (approximate) | Yes — 2000–2026 for river stage, 2022–2026 for GPS |
| Seasonal temperature pattern | Yes (synthetic sinusoidal) |
| Presence of a major 2022-like event | Yes (synthetic, shifted values) |
| Actual measured values | **No** — all values are synthetic |
| Official monitoring records | **No** |
| Real pier identities or bridge IDs | **No** — uses generic E1/E2/E3/PP15 labels only |

---

## .gitignore rules

The `.gitignore` file already prevents raw data files from being tracked:

```
data/raw/*.xlsx
data/raw/*.xls
data/raw/*.docx
data/raw/*.pdf
data/raw/*.csv
```

Demo CSV files in `data/demo/` **are** tracked (they contain only synthetic data):

```
# Allow demo data
!data/demo/*.csv
!data/demo/.gitkeep
```

---

## Limitations of demo mode

- Demo data does not reproduce the real event magnitudes, coupling ratios, or risk levels.
- Research Insights, Engineering Summary, and Primary Device Comparison pages will show
  different (synthetic) values compared to the local/private mode.
- Demo mode is for portfolio demonstration of the workflow and methodology, not for
  reproducing the specific monitoring findings.

---

## Statement

> The synthetic demo data files in `data/demo/` are computer-generated and do not
> represent actual bridge monitoring records. They are provided solely to demonstrate
> the PierWatch software architecture and workflow. No structural safety conclusions
> should be drawn from demo-mode outputs.
