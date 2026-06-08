# Data Notes

## Raw files

- `data/raw/Pier_Monitoring_Report_private.docx` (private; not included in public version)
- `data/raw/Jointmeters w GPS R0.xlsx`

## Expected Excel sheets

Core:

- `River Stage 2000-2026`
- `GPS Data`
- `PP-15 Filter`
- `E2-PP15`
- `W2 - 2133`
- `PP 15 - 2132`
- `E2 - 2129`
- `E3 - 2130`
- `excelrpt`
- `2022-2025 E-1 Displacement`
- `2022-2025 E-2 Displacement`

## Parsing notes

The Excel workbook may have merged cells, grouped headers, blank rows, and calculation sheets. Start with the robust loaders, then inspect and adjust explicit column positions if necessary.

Known invalid values to clean:

- `-7999`
- `-9999`
- `9999`

For event-based movement, use median windows rather than single readings.
