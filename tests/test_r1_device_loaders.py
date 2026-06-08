import unittest
from pathlib import Path
import pandas as pd


class R1DeviceLoadersTests(unittest.TestCase):
    def setUp(self):
        from src.config import EXCEL_PATH
        self.excel_path = EXCEL_PATH
        self.excel_available = EXCEL_PATH.exists()

    def test_r1_workbook_exists(self):
        if not self.excel_available:
            self.skipTest("Private workbook is not included in the public repository.")
        self.assertTrue(
            self.excel_path.exists(),
            f"R1 workbook not found at {self.excel_path}"
        )

    def test_load_device_sheet_w2(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_device_sheet
        df = load_device_sheet(str(self.excel_path), "W2", "W2")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "W2 returned empty DataFrame")
        for col in ["timestamp", "device_id", "measured_expansion_in", "temperature_f"]:
            self.assertIn(col, df.columns)
        self.assertTrue((df["device_id"] == "W2").all())
        self.assertTrue(df["timestamp"].notna().all())

    def test_load_device_sheet_pp15(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_device_sheet
        df = load_device_sheet(str(self.excel_path), "PP 15", "PP15")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "PP15 returned empty DataFrame")
        self.assertGreater(len(df), 100)
        for col in ["timestamp", "device_id", "measured_expansion_in", "temperature_f",
                    "corrected_expansion_in"]:
            self.assertIn(col, df.columns)
        self.assertTrue((df["device_id"] == "PP15").all())

    def test_load_device_sheet_e2(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_device_sheet
        df = load_device_sheet(str(self.excel_path), "E2", "E2")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "E2 returned empty DataFrame")
        self.assertGreater(len(df), 100)
        for col in ["timestamp", "device_id", "measured_expansion_in", "temperature_f"]:
            self.assertIn(col, df.columns)

    def test_load_device_sheet_e3_has_alt_columns(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_device_sheet
        df = load_device_sheet(str(self.excel_path), "E3", "E3")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty, "E3 returned empty DataFrame")
        self.assertIn("corrected_expansion_alt_in", df.columns)
        self.assertIn("calculated_expansion_alt_in", df.columns)
        # Alt columns should have some valid values
        self.assertTrue(df["corrected_expansion_alt_in"].notna().any())

    def test_load_device_sheet_no_invalid_sentinels(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_device_sheet
        df = load_device_sheet(str(self.excel_path), "PP 15", "PP15")
        for col in ["measured_expansion_in", "temperature_f", "corrected_expansion_in"]:
            if col in df.columns:
                vals = df[col].dropna()
                self.assertFalse((vals == -7999).any(), f"{col} contains -7999 sentinel")
                self.assertFalse((vals == -9999).any(), f"{col} contains -9999 sentinel")

    def test_load_device_sheet_timestamps_are_sorted(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_device_sheet
        df = load_device_sheet(str(self.excel_path), "PP 15", "PP15")
        self.assertTrue((df["timestamp"].diff().dropna() >= pd.Timedelta(0)).all())

    def test_load_all_primary_device_data_returns_all_devices(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_all_primary_device_data
        df = load_all_primary_device_data(str(self.excel_path))
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        device_ids = set(df["device_id"].unique())
        for did in ["W2", "PP15", "E2", "E3"]:
            self.assertIn(did, device_ids)

    def test_gps_loader_still_works(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_gps_data
        df = load_gps_data(str(self.excel_path))
        self.assertFalse(df.empty)
        self.assertIn("E1", df["pier_id"].values)
        self.assertIn("E2", df["pier_id"].values)
        self.assertIn("E3", df["pier_id"].values)

    def test_river_stage_loader_still_works(self):
        if not self.excel_available:
            self.skipTest("R1 workbook not available")
        from src.data_loader import load_river_stage
        df = load_river_stage(str(self.excel_path))
        self.assertFalse(df.empty)
        self.assertIn("stage_ft", df.columns)
        self.assertGreater(len(df), 1000)


if __name__ == "__main__":
    unittest.main()
