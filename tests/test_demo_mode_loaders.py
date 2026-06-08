"""
Tests for demo mode data loaders.
All tests must pass with PIERWATCH_DATA_MODE=demo (no Excel workbook required).
"""
import os
import unittest
import pandas as pd

# Force demo mode for these tests
os.environ["PIERWATCH_DATA_MODE"] = "demo"

# Re-import config after setting env var so DATA_MODE picks it up
import importlib
import src.config as _cfg
importlib.reload(_cfg)


class DemoRiverStageTests(unittest.TestCase):
    def test_returns_dataframe_with_required_columns(self):
        from src.demo_data_loader import load_demo_river_stage
        df = load_demo_river_stage()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("timestamp", df.columns)
        self.assertIn("stage_ft", df.columns)

    def test_timestamps_are_datetime(self):
        from src.demo_data_loader import load_demo_river_stage
        df = load_demo_river_stage()
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["timestamp"]))

    def test_stage_values_are_numeric(self):
        from src.demo_data_loader import load_demo_river_stage
        df = load_demo_river_stage()
        self.assertTrue(pd.api.types.is_float_dtype(df["stage_ft"]))


class DemoGpsTests(unittest.TestCase):
    def test_returns_dataframe_with_required_columns(self):
        from src.demo_data_loader import load_demo_gps_data
        df = load_demo_gps_data()
        for col in ["timestamp", "pier_id", "longitudinal_in", "transverse_in"]:
            self.assertIn(col, df.columns)
        self.assertFalse(df.empty)

    def test_all_three_piers_present(self):
        from src.demo_data_loader import load_demo_gps_data
        df = load_demo_gps_data()
        piers = set(df["pier_id"].unique())
        self.assertIn("E1", piers)
        self.assertIn("E2", piers)
        self.assertIn("E3", piers)


class DemoDeviceTests(unittest.TestCase):
    def test_returns_dataframe_with_required_columns(self):
        from src.demo_data_loader import load_demo_device_data
        df = load_demo_device_data()
        for col in ["timestamp", "device_id", "measured_expansion_in",
                    "temperature_f", "corrected_expansion_in"]:
            self.assertIn(col, df.columns)

    def test_all_four_devices_present(self):
        from src.demo_data_loader import load_all_demo_primary_device_data
        df = load_all_demo_primary_device_data()
        devices = set(df["device_id"].unique())
        for did in ["PP15", "E2", "E3", "W2"]:
            self.assertIn(did, devices)

    def test_load_demo_device_sheet_filters_correctly(self):
        from src.demo_data_loader import load_demo_device_sheet
        df = load_demo_device_sheet("PP15")
        self.assertTrue((df["device_id"] == "PP15").all())
        self.assertFalse(df.empty)


class DemoEventDetectionTests(unittest.TestCase):
    def test_event_detection_runs_on_demo_river_stage(self):
        from src.demo_data_loader import load_demo_river_stage
        from src.event_detection import detect_low_water_events
        river = load_demo_river_stage()
        events = detect_low_water_events(river)
        self.assertIsInstance(events, pd.DataFrame)
        self.assertFalse(events.empty)

    def test_compute_event_movement_runs_on_demo_gps(self):
        from src.demo_data_loader import load_demo_river_stage, load_demo_gps_data
        from src.event_detection import detect_low_water_events
        from src.gps_processing import compute_event_movement
        river = load_demo_river_stage()
        events = detect_low_water_events(river)
        gps = load_demo_gps_data()
        movement = compute_event_movement(gps, events)
        self.assertIsInstance(movement, pd.DataFrame)


class DemoDeviceComparisonTests(unittest.TestCase):
    def test_device_availability_summary_runs_on_demo_data(self):
        from src.demo_data_loader import load_all_demo_primary_device_data
        from src.device_comparison import device_availability_summary
        df = load_all_demo_primary_device_data()
        result = device_availability_summary(df)
        self.assertFalse(result.empty)
        devices = set(result["device_id"])
        self.assertIn("PP15", devices)


class DataSourcesWrapperTests(unittest.TestCase):
    """Test mode-aware wrapper functions return correct schema in demo mode."""

    def test_get_river_stage_data_returns_correct_schema(self):
        from src.data_sources import get_river_stage_data
        df = get_river_stage_data()
        self.assertIn("timestamp", df.columns)
        self.assertIn("stage_ft", df.columns)

    def test_get_gps_data_returns_correct_schema(self):
        from src.data_sources import get_gps_data
        df = get_gps_data()
        self.assertIn("pier_id", df.columns)
        self.assertIn("longitudinal_in", df.columns)

    def test_get_primary_device_data_returns_correct_schema(self):
        from src.data_sources import get_primary_device_data
        df = get_primary_device_data()
        self.assertIn("device_id", df.columns)
        self.assertIn("corrected_expansion_in", df.columns)

    def test_get_device_sheet_data_routes_correctly(self):
        from src.data_sources import get_device_sheet_data
        df = get_device_sheet_data("E2")
        self.assertTrue((df["device_id"] == "E2").all())

    def test_is_data_available_true_in_demo_mode(self):
        from src.data_sources import is_data_available
        self.assertTrue(is_data_available())

    def test_source_cache_key_returns_demo_mode(self):
        from src.data_sources import source_cache_key
        mode, path, mt = source_cache_key()
        self.assertEqual(mode, "demo")


if __name__ == "__main__":
    unittest.main()
