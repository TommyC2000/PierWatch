import unittest
import numpy as np
import pandas as pd


def _make_device_df():
    """Minimal synthetic device DataFrame for unit tests."""
    n = 100
    timestamps = pd.date_range("2022-01-01", periods=n, freq="6h")
    records = []
    for dev in ["W2", "PP15", "E2", "E3"]:
        df = pd.DataFrame({
            "timestamp": timestamps,
            "device_id": dev,
            "measured_expansion_in": np.random.uniform(-1, 1, n),
            "temperature_f": np.random.uniform(40, 90, n),
            "corrected_expansion_in": np.random.uniform(-0.5, 0.5, n),
            "delta_temperature_f": np.random.uniform(-5, 5, n),
        })
        records.append(df)
    return pd.concat(records, ignore_index=True)


def _make_events_df():
    return pd.DataFrame([{
        "event_id": "LW-TEST",
        "event_year": 2022,
        "start_date": "2022-06-01",
        "end_date": "2022-06-30",
        "event_class": "Test",
    }])


class DeviceAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.df = _make_device_df()

    def test_returns_one_row_per_device(self):
        from src.device_comparison import device_availability_summary
        result = device_availability_summary(self.df)
        self.assertEqual(len(result), 4)
        device_ids = set(result["device_id"])
        for did in ["W2", "PP15", "E2", "E3"]:
            self.assertIn(did, device_ids)

    def test_start_end_times_are_populated(self):
        from src.device_comparison import device_availability_summary
        result = device_availability_summary(self.df)
        self.assertTrue(result["start_time"].notna().all())
        self.assertTrue(result["end_time"].notna().all())

    def test_empty_input_returns_empty(self):
        from src.device_comparison import device_availability_summary
        result = device_availability_summary(pd.DataFrame())
        self.assertTrue(result.empty)


class LatestSnapshotTests(unittest.TestCase):
    def test_returns_latest_per_device(self):
        from src.device_comparison import latest_device_snapshot
        df = _make_device_df()
        result = latest_device_snapshot(df)
        self.assertEqual(len(result), 4)
        self.assertIn("latest_timestamp", result.columns)
        self.assertIn("latest_corrected_expansion_in", result.columns)

    def test_empty_input_returns_empty(self):
        from src.device_comparison import latest_device_snapshot
        result = latest_device_snapshot(pd.DataFrame())
        self.assertTrue(result.empty)


class EventWindowComparisonTests(unittest.TestCase):
    def test_returns_one_row_per_device(self):
        from src.device_comparison import event_window_device_comparison
        df = _make_device_df()
        events = _make_events_df()
        result = event_window_device_comparison(df, events, "LW-TEST")
        self.assertEqual(len(result), 4)
        self.assertIn("event_change_corrected_in", result.columns)
        self.assertIn("data_quality_note", result.columns)

    def test_unknown_event_returns_empty(self):
        from src.device_comparison import event_window_device_comparison
        df = _make_device_df()
        events = _make_events_df()
        result = event_window_device_comparison(df, events, "LW-UNKNOWN")
        self.assertTrue(result.empty)

    def test_empty_device_df_returns_empty(self):
        from src.device_comparison import event_window_device_comparison
        events = _make_events_df()
        result = event_window_device_comparison(pd.DataFrame(), events, "LW-TEST")
        self.assertTrue(result.empty)


class YearlyDeviceSummaryTests(unittest.TestCase):
    def test_returns_rows_per_device_and_year(self):
        from src.device_comparison import yearly_device_summary
        df = _make_device_df()
        result = yearly_device_summary(df)
        self.assertFalse(result.empty)
        self.assertIn("device_id", result.columns)
        self.assertIn("year", result.columns)
        self.assertIn("median_corrected_expansion_in", result.columns)

    def test_empty_input_returns_empty(self):
        from src.device_comparison import yearly_device_summary
        result = yearly_device_summary(pd.DataFrame())
        self.assertTrue(result.empty)

    def test_low_high_temp_columns_present(self):
        from src.device_comparison import yearly_device_summary
        df = _make_device_df()
        result = yearly_device_summary(df)
        self.assertIn("low_temperature_median_corrected_in", result.columns)
        self.assertIn("high_temperature_median_corrected_in", result.columns)


if __name__ == "__main__":
    unittest.main()
