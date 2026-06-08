import unittest

import numpy as np
import pandas as pd

from src.sensor_quality import (
    QUALITY_COLUMNS,
    compute_all_sensor_quality,
    compute_series_quality,
)

_VALID_LABELS = {"High", "Medium", "Low", "Poor", "Insufficient Data"}


def _make_df(n: int = 50, missing_frac: float = 0.0, add_outlier: bool = False) -> pd.DataFrame:
    """Synthetic daily time-series with optional missing values and outliers."""
    ts = pd.date_range("2022-01-01", periods=n, freq="D")
    vals = np.linspace(10.0, 15.0, n) + np.random.default_rng(0).normal(0, 0.1, n)
    if missing_frac > 0:
        n_miss = max(1, int(n * missing_frac))
        idx = np.random.default_rng(1).choice(n, size=n_miss, replace=False)
        vals[idx] = np.nan
    if add_outlier:
        vals[n // 2] = 9999.0
    return pd.DataFrame({"timestamp": ts, "value": vals})


class ComputeSeriesQualityTests(unittest.TestCase):
    # ── Basic structure ───────────────────────────────────────────────────────

    def test_returns_dict_with_all_quality_columns(self):
        df = _make_df()
        result = compute_series_quality(df, "timestamp", ["value"], "TestSource", "s1")
        for col in QUALITY_COLUMNS:
            self.assertIn(col, result, msg=f"Missing key: {col}")

    def test_source_and_sensor_id_are_set(self):
        df = _make_df()
        result = compute_series_quality(df, "timestamp", ["value"], "RiverStage", "stage_ft")
        self.assertEqual(result["source_name"], "RiverStage")
        self.assertEqual(result["sensor_id"], "stage_ft")

    # ── Clean data ────────────────────────────────────────────────────────────

    def test_clean_data_has_zero_missing_and_high_confidence(self):
        df = _make_df(n=100)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v", expected_freq="D")
        self.assertEqual(result["missing_value_count"], 0)
        self.assertGreaterEqual(result["confidence_score"], 0.80)
        self.assertEqual(result["confidence_label"], "High")

    def test_valid_record_count_equals_n_when_no_missing(self):
        n = 60
        df = _make_df(n=n)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["valid_record_count"], n)

    def test_record_count_correct(self):
        df = _make_df(n=40)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["record_count"], 40)

    # ── Missing values ────────────────────────────────────────────────────────

    def test_missing_values_counted(self):
        df = _make_df(n=50, missing_frac=0.20)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertGreater(result["missing_value_count"], 0)
        self.assertGreater(result["missing_value_rate"], 0.0)

    def test_high_missing_rate_reduces_confidence(self):
        df = _make_df(n=50, missing_frac=0.50)
        result_miss = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        df_clean = _make_df(n=50)
        result_clean = compute_series_quality(df_clean, "timestamp", ["value"], "S", "v")
        self.assertLess(result_miss["confidence_score"], result_clean["confidence_score"])

    # ── Duplicate timestamps ──────────────────────────────────────────────────

    def test_duplicate_timestamps_are_counted_and_deduped(self):
        df = _make_df(n=20)
        dup = pd.concat([df, df.iloc[:5]], ignore_index=True)
        result = compute_series_quality(dup, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["duplicate_timestamp_count"], 5)
        self.assertEqual(result["record_count"], 25)
        # After dedup, valid_record_count should match original 20
        self.assertEqual(result["valid_record_count"], 20)

    # ── Outliers ──────────────────────────────────────────────────────────────

    def test_outlier_detected_with_iqr_method(self):
        df = _make_df(n=50, add_outlier=True)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertGreater(result["outlier_count"], 0)
        self.assertGreater(result["outlier_rate"], 0.0)

    def test_no_outlier_in_clean_data(self):
        df = _make_df(n=50)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["outlier_count"], 0)

    # ── Confidence score and label ────────────────────────────────────────────

    def test_confidence_score_is_between_0_and_1(self):
        for n, missing, outlier in [(50, 0.0, False), (50, 0.3, False), (50, 0.0, True)]:
            with self.subTest(n=n, missing=missing, outlier=outlier):
                df = _make_df(n=n, missing_frac=missing, add_outlier=outlier)
                result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
                score = result["confidence_score"]
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)

    def test_confidence_label_is_valid(self):
        for n in [5, 20, 50, 100]:
            with self.subTest(n=n):
                df = _make_df(n=n)
                result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
                self.assertIn(result["confidence_label"], _VALID_LABELS)

    def test_small_dataset_returns_insufficient_data(self):
        df = _make_df(n=5)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["confidence_label"], "Insufficient Data")

    # ── Edge cases ────────────────────────────────────────────────────────────

    def test_empty_dataframe_returns_insufficient(self):
        result = compute_series_quality(pd.DataFrame(), "timestamp", ["value"], "S", "v")
        self.assertEqual(result["confidence_label"], "Insufficient Data")
        self.assertEqual(result["record_count"], 0)

    def test_missing_timestamp_col_returns_insufficient(self):
        df = pd.DataFrame({"other": [1, 2, 3]})
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["confidence_label"], "Insufficient Data")

    def test_missing_value_col_returns_insufficient(self):
        df = _make_df(n=30)
        result = compute_series_quality(df, "timestamp", ["nonexistent"], "S", "v")
        self.assertEqual(result["confidence_label"], "Insufficient Data")

    def test_expected_freq_completeness_computed_correctly(self):
        # 10 days of daily data — expected_record_count should be ~10, completeness ~1
        df = _make_df(n=10)
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v", expected_freq="D")
        self.assertAlmostEqual(result["completeness_rate"], 1.0, places=1)
        self.assertAlmostEqual(result["expected_record_count"], 10.0, delta=1.0)

    def test_flatline_count_nonzero_for_constant_series(self):
        ts = pd.date_range("2022-01-01", periods=20, freq="D")
        df = pd.DataFrame({"timestamp": ts, "value": [5.0] * 20})
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertGreater(result["flatline_count"], 0)

    def test_all_nan_values_returns_insufficient(self):
        ts = pd.date_range("2022-01-01", periods=20, freq="D")
        df = pd.DataFrame({"timestamp": ts, "value": [np.nan] * 20})
        result = compute_series_quality(df, "timestamp", ["value"], "S", "v")
        self.assertEqual(result["valid_record_count"], 0)
        self.assertEqual(result["confidence_label"], "Insufficient Data")


# ── compute_all_sensor_quality ────────────────────────────────────────────────

class ComputeAllSensorQualityTests(unittest.TestCase):
    def setUp(self):
        from src.config import EXCEL_PATH
        self.excel_available = EXCEL_PATH.exists()

    def test_returns_dataframe_with_quality_columns_when_file_present(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        df = compute_all_sensor_quality(str(EXCEL_PATH))
        self.assertIsInstance(df, pd.DataFrame)
        for col in QUALITY_COLUMNS:
            self.assertIn(col, df.columns, msg=f"Missing column: {col}")

    def test_returns_expected_number_of_streams(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        df = compute_all_sensor_quality(str(EXCEL_PATH))
        # At minimum: 1 river + 6 GPS + 4 PP-15 = 11
        self.assertGreaterEqual(len(df), 11)

    def test_all_confidence_labels_are_valid(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        df = compute_all_sensor_quality(str(EXCEL_PATH))
        for label in df["confidence_label"].dropna():
            self.assertIn(label, _VALID_LABELS)

    def test_all_confidence_scores_are_in_range(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        df = compute_all_sensor_quality(str(EXCEL_PATH))
        scores = df["confidence_score"].dropna()
        self.assertTrue((scores >= 0.0).all())
        self.assertTrue((scores <= 1.0).all())

    def test_source_names_include_expected_sources(self):
        if not self.excel_available:
            self.skipTest("Excel workbook not available")
        from src.config import EXCEL_PATH
        df = compute_all_sensor_quality(str(EXCEL_PATH))
        sources = set(df["source_name"].dropna().unique())
        self.assertIn("River Stage", sources)
        self.assertIn("GPS", sources)
        self.assertIn("PP-15 Filter", sources)

    def test_nonexistent_path_returns_empty_df(self):
        df = compute_all_sensor_quality("/nonexistent/path.xlsx")
        self.assertTrue(df.empty)
        for col in QUALITY_COLUMNS:
            self.assertIn(col, df.columns)


if __name__ == "__main__":
    unittest.main()
