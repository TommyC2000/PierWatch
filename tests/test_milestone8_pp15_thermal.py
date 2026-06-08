import unittest

import numpy as np
import pandas as pd

from src.thermal_correction import (
    YEARLY_COMPARISON_COLUMNS,
    compare_low_temperature_windows,
    compute_linear_thermal_correction,
)


def _make_pp15_df(n: int = 20) -> pd.DataFrame:
    """Minimal synthetic PP-15 dataframe for testing."""
    rng = pd.date_range("2022-08-01", periods=n, freq="6h")
    temps = np.linspace(90, 40, n)
    measured = -0.04 * temps + 1.0 + np.linspace(0, -0.5, n)
    corrected = measured + 0.03 * temps - 0.8
    return pd.DataFrame(
        {
            "timestamp": rng,
            "measured_expansion_in": measured,
            "temperature_f": temps,
            "delta_temperature_f": temps - 80.0,
            "calculated_expansion_in": 0.01 * temps,
            "corrected_expansion_in": corrected,
        }
    )


# ── load_pp15_filter ──────────────────────────────────────────────────────────

class LoadPP15FilterTests(unittest.TestCase):
    def setUp(self):
        from src.config import EXCEL_PATH
        self.excel_available = EXCEL_PATH.exists()

    def test_returns_expected_columns_when_file_present(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        from src.data_loader import load_pp15_filter
        df = load_pp15_filter(str(EXCEL_PATH))
        expected = [
            "timestamp", "measured_expansion_in", "temperature_f",
            "delta_temperature_f", "calculated_expansion_in", "corrected_expansion_in",
        ]
        for col in expected:
            self.assertIn(col, df.columns, msg=f"Missing column: {col}")

    def test_timestamp_is_datetime_when_file_present(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        from src.data_loader import load_pp15_filter
        df = load_pp15_filter(str(EXCEL_PATH))
        self.assertFalse(df.empty)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["timestamp"]))

    def test_numeric_columns_are_float_when_file_present(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        from src.data_loader import load_pp15_filter
        df = load_pp15_filter(str(EXCEL_PATH))
        for col in ["measured_expansion_in", "temperature_f", "corrected_expansion_in"]:
            self.assertTrue(
                pd.api.types.is_float_dtype(df[col]),
                msg=f"{col} is not float dtype",
            )

    def test_no_invalid_sentinels_when_file_present(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        from src.data_loader import load_pp15_filter
        df = load_pp15_filter(str(EXCEL_PATH))
        for col in df.select_dtypes(include="number").columns:
            self.assertFalse(
                ((df[col] == -7999) | (df[col] == -9999)).any(),
                msg=f"Sentinel value found in {col}",
            )

    def test_no_duplicate_timestamps_when_file_present(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        from src.data_loader import load_pp15_filter
        df = load_pp15_filter(str(EXCEL_PATH))
        self.assertEqual(df["timestamp"].duplicated().sum(), 0)


# ── compute_linear_thermal_correction ────────────────────────────────────────

class LinearThermalCorrectionTests(unittest.TestCase):
    def test_returns_tuple_of_df_and_stats(self):
        df = _make_pp15_df()
        result = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        corr_df, stats = result
        self.assertIsInstance(corr_df, pd.DataFrame)
        self.assertIsInstance(stats, dict)

    def test_prediction_and_residual_columns_present(self):
        df = _make_pp15_df()
        corr_df, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertIn("predicted_thermal_movement_in", corr_df.columns)
        self.assertIn("thermal_corrected_residual_in", corr_df.columns)

    def test_residuals_are_numeric(self):
        df = _make_pp15_df()
        corr_df, _ = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertTrue(pd.api.types.is_float_dtype(corr_df["thermal_corrected_residual_in"]))

    def test_stats_has_required_keys(self):
        df = _make_pp15_df()
        _, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        for key in ("slope", "intercept", "r_squared", "record_count", "status"):
            self.assertIn(key, stats)

    def test_r_squared_between_zero_and_one(self):
        df = _make_pp15_df()
        _, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertEqual(stats["status"], "ok")
        self.assertGreaterEqual(stats["r_squared"], 0.0)
        self.assertLessEqual(stats["r_squared"], 1.0)

    def test_insufficient_data_returns_nan_columns(self):
        df = _make_pp15_df(n=3)
        corr_df, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertNotEqual(stats["status"], "ok")
        self.assertTrue(corr_df["predicted_thermal_movement_in"].isna().all())
        self.assertTrue(corr_df["thermal_corrected_residual_in"].isna().all())

    def test_all_nan_movement_does_not_crash(self):
        df = _make_pp15_df()
        df["measured_expansion_in"] = np.nan
        corr_df, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertNotEqual(stats["status"], "ok")
        self.assertTrue(corr_df["predicted_thermal_movement_in"].isna().all())

    def test_missing_column_does_not_crash(self):
        df = _make_pp15_df().drop(columns=["temperature_f"])
        corr_df, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        self.assertIn("missing_column", stats["status"])

    def test_zero_variance_temperature_does_not_crash(self):
        df = _make_pp15_df()
        df["temperature_f"] = 72.0
        corr_df, stats = compute_linear_thermal_correction(df, "measured_expansion_in", "temperature_f")
        # Should not raise; result may have nan residuals or zero r_squared
        self.assertIn("status", stats)


# ── compare_low_temperature_windows ──────────────────────────────────────────

class LowTempComparisonTests(unittest.TestCase):
    def test_returns_expected_columns(self):
        df = _make_pp15_df(40)
        result = compare_low_temperature_windows(df, "temperature_f", "corrected_expansion_in")
        for col in YEARLY_COMPARISON_COLUMNS:
            self.assertIn(col, result.columns)

    def test_returns_one_row_per_year(self):
        df = _make_pp15_df(40)
        result = compare_low_temperature_windows(df, "temperature_f", "corrected_expansion_in")
        self.assertFalse(result.empty)
        self.assertEqual(len(result), result["year"].nunique())

    def test_record_count_is_positive(self):
        df = _make_pp15_df(40)
        result = compare_low_temperature_windows(df, "temperature_f", "corrected_expansion_in")
        self.assertTrue((result["record_count"] > 0).all())

    def test_empty_input_returns_empty_df(self):
        result = compare_low_temperature_windows(
            pd.DataFrame(), "temperature_f", "corrected_expansion_in"
        )
        self.assertTrue(result.empty)
        for col in YEARLY_COMPARISON_COLUMNS:
            self.assertIn(col, result.columns)

    def test_all_nan_corrected_returns_empty(self):
        df = _make_pp15_df()
        df["corrected_expansion_in"] = np.nan
        result = compare_low_temperature_windows(df, "temperature_f", "corrected_expansion_in")
        self.assertTrue(result.empty)

    def test_temperature_threshold_is_correct_percentile(self):
        df = _make_pp15_df(100)
        pct = 20
        result = compare_low_temperature_windows(df, "temperature_f", "corrected_expansion_in", pct)
        expected_threshold = float(df["temperature_f"].quantile(pct / 100))
        self.assertAlmostEqual(result["temperature_threshold_f"].iloc[0], expected_threshold, places=2)

    def test_multi_year_data_returns_multiple_rows(self):
        df1 = _make_pp15_df(20)
        df2 = _make_pp15_df(20)
        df2["timestamp"] = df2["timestamp"] + pd.DateOffset(years=1)
        df = pd.concat([df1, df2], ignore_index=True)
        result = compare_low_temperature_windows(df, "temperature_f", "corrected_expansion_in")
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
