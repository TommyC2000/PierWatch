import tempfile
import unittest
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from src.data_loader import load_river_stage
from src.event_detection import detect_low_water_events


class RiverStageLoaderTests(unittest.TestCase):
    def test_load_river_stage_cleans_to_exact_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "river.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "River Stage 2000-2026"
            ws.append(["Date / Tie", "Stage (Ft)", "Unused"])
            ws.append(["2026-01-01 08:00", "11.5", "x"])
            ws.append([None, None, None])
            ws.append(["2026-01-02 08:00", "-9999", "invalid"])
            ws.append(["2026-01-03 08:00", "8.2", "x"])
            ws.append(["2026-01-03 08:00", "8.4", "duplicate"])
            ws.append(["not a date", "5.0", "bad timestamp"])
            wb.save(path)

            river = load_river_stage(path)

        self.assertEqual(list(river.columns), ["timestamp", "stage_ft"])
        self.assertEqual(len(river), 2)
        self.assertEqual(river["stage_ft"].tolist(), [11.5, 8.2])
        self.assertTrue(river["timestamp"].is_monotonic_increasing)


class LowWaterEventDetectionTests(unittest.TestCase):
    def test_detects_merged_events_and_renumbers_after_short_events_are_ignored(self):
        dates = pd.date_range("2026-01-01", periods=18, freq="D")
        stages = [
            10.0,
            13.0,
            13.0,
            13.0,
            11.0,
            6.0,
            5.0,
            13.0,
            13.0,
            10.0,
            9.0,
            13.0,
            13.0,
            13.0,
            13.0,
            11.0,
            10.0,
            9.0,
        ]
        river = pd.DataFrame({"timestamp": dates, "stage_ft": stages})

        events = detect_low_water_events(river, min_event_days=3, merge_gap_days=2)

        self.assertEqual(events["event_id"].tolist(), ["LW-001", "LW-002"])
        first = events.iloc[0]
        self.assertEqual(first["start_date"], pd.Timestamp("2026-01-05").date())
        self.assertEqual(first["end_date"], pd.Timestamp("2026-01-11").date())
        self.assertEqual(first["duration_days"], 7)
        self.assertEqual(first["days_below_12"], 5)
        self.assertEqual(first["days_below_7"], 2)
        self.assertGreaterEqual(first["max_drop_rate_ft_per_day"], 5.0)

    def test_returns_expected_columns_for_empty_input(self):
        events = detect_low_water_events(pd.DataFrame(columns=["timestamp", "stage_ft"]))
        self.assertEqual(
            list(events.columns),
            [
                "event_id",
                "start_date",
                "end_date",
                "duration_days",
                "min_stage_ft",
                "days_below_12",
                "days_below_7",
                "cumulative_deficit_below_12",
                "cumulative_deficit_below_7",
                "max_drop_rate_ft_per_day",
                "event_year",
                "event_class",
            ],
        )
        self.assertTrue(events.empty)


if __name__ == "__main__":
    unittest.main()
