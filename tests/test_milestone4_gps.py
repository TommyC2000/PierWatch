import tempfile
import unittest
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from src.data_loader import load_gps_data
from src.gps_processing import compute_event_movement


class GpsLoaderTests(unittest.TestCase):
    def test_load_gps_data_converts_grouped_wide_sheet_to_long_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "gps.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "GPS Data"
            ws.append(["E1", None, None, None, "E2", None, None, None, "E3", None, None])
            ws.append(["2026-01-01 00:00", "1.0", "0.1", None, "2026-01-01 00:00", "2.0", "0.2", None, "2026-01-01 00:00", "3.0", "0.3"])
            ws.append(["2026-01-02 00:00", "-9999", "0.4", None, None, None, None, None, "bad date", "4.0", "0.4"])
            ws.append(["2026-01-01 00:00", "1.5", "0.5", None, "2026-01-02 00:00", "2.5", "0.5", None, "2026-01-02 00:00", "3.5", "0.5"])
            wb.save(path)

            gps = load_gps_data(path)

        self.assertEqual(list(gps.columns), ["timestamp", "pier_id", "longitudinal_in", "transverse_in"])
        self.assertEqual(gps["pier_id"].drop_duplicates().tolist(), ["E1", "E2", "E3"])
        self.assertEqual(len(gps), 5)
        self.assertEqual(gps.groupby("pier_id").size().to_dict(), {"E1": 1, "E2": 2, "E3": 2})
        self.assertFalse(gps[["longitudinal_in", "transverse_in"]].isna().any().any())


class EventMovementTests(unittest.TestCase):
    def test_compute_event_movement_uses_pre_and_post_event_medians(self):
        event = pd.DataFrame(
            [
                {
                    "event_id": "LW-001",
                    "event_year": 2026,
                    "start_date": pd.Timestamp("2026-01-10").date(),
                    "end_date": pd.Timestamp("2026-01-20").date(),
                }
            ]
        )
        rows = []
        for day in pd.date_range("2026-01-03", "2026-01-09"):
            rows.append({"timestamp": day, "pier_id": "E1", "longitudinal_in": 1.0, "transverse_in": 10.0})
        for day in pd.date_range("2026-01-21", "2026-01-27"):
            rows.append({"timestamp": day, "pier_id": "E1", "longitudinal_in": 3.0, "transverse_in": 13.0})
        gps = pd.DataFrame(rows)

        movement = compute_event_movement(gps, event)

        row = movement.iloc[0]
        self.assertEqual(row["baseline_source"], "pre_post_window")
        self.assertEqual(row["pre_sample_count"], 7)
        self.assertEqual(row["post_sample_count"], 7)
        self.assertEqual(row["longitudinal_movement_in"], 2.0)
        self.assertEqual(row["transverse_movement_in"], 3.0)

    def test_compute_event_movement_falls_back_to_first_and_last_seven_valid_days_inside_event(self):
        event = pd.DataFrame(
            [
                {
                    "event_id": "LW-002",
                    "event_year": 2026,
                    "start_date": pd.Timestamp("2026-02-01").date(),
                    "end_date": pd.Timestamp("2026-02-14").date(),
                }
            ]
        )
        gps = pd.DataFrame(
            {
                "timestamp": pd.date_range("2026-02-01", periods=14, freq="D"),
                "pier_id": ["E2"] * 14,
                "longitudinal_in": list(range(14)),
                "transverse_in": [value * 2 for value in range(14)],
            }
        )

        movement = compute_event_movement(gps, event)

        row = movement.iloc[0]
        self.assertEqual(row["baseline_source"], "in_event_fallback")
        self.assertEqual(row["pre_sample_count"], 7)
        self.assertEqual(row["post_sample_count"], 7)
        self.assertEqual(row["longitudinal_movement_in"], 7.0)
        self.assertEqual(row["transverse_movement_in"], 14.0)


if __name__ == "__main__":
    unittest.main()
