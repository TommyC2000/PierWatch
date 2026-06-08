import unittest

import pandas as pd

from src.sensitivity_model import compute_low_water_severity_index, compute_movement_sensitivity


class SensitivityModelTests(unittest.TestCase):
    def test_lwsi_uses_weighted_min_max_normalized_components(self):
        events = pd.DataFrame(
            [
                {
                    "event_id": "LW-001",
                    "event_year": 2022,
                    "days_below_12": 10,
                    "days_below_7": 0,
                    "cumulative_deficit_below_7": 0.0,
                    "min_stage_ft": 8.0,
                },
                {
                    "event_id": "LW-002",
                    "event_year": 2023,
                    "days_below_12": 20,
                    "days_below_7": 10,
                    "cumulative_deficit_below_7": 30.0,
                    "min_stage_ft": 4.0,
                },
            ]
        )

        result = compute_low_water_severity_index(events)

        self.assertEqual(result.loc[0, "depth_below_7"], 0.0)
        self.assertEqual(result.loc[1, "depth_below_7"], 3.0)
        self.assertEqual(result.loc[0, "LWSI"], 0.0)
        self.assertEqual(result.loc[1, "LWSI"], 1.0)

    def test_compute_movement_sensitivity_merges_e1_e2_and_safe_divides(self):
        events = pd.DataFrame(
            [
                {
                    "event_id": "LW-001",
                    "event_year": 2022,
                    "start_date": "2022-08-29",
                    "end_date": "2022-12-10",
                    "days_below_12": 10,
                    "days_below_7": 0,
                    "cumulative_deficit_below_7": 0.0,
                    "min_stage_ft": 8.0,
                },
                {
                    "event_id": "LW-002",
                    "event_year": 2023,
                    "start_date": "2023-08-29",
                    "end_date": "2024-01-14",
                    "days_below_12": 20,
                    "days_below_7": 10,
                    "cumulative_deficit_below_7": 20.0,
                    "min_stage_ft": 5.0,
                },
            ]
        )
        movement = pd.DataFrame(
            [
                {"event_id": "LW-001", "event_year": 2022, "pier_id": "E1", "longitudinal_movement_in": 4.0},
                {"event_id": "LW-001", "event_year": 2022, "pier_id": "E2", "longitudinal_movement_in": 3.0},
                {"event_id": "LW-002", "event_year": 2023, "pier_id": "E1", "longitudinal_movement_in": 2.0},
                {"event_id": "LW-002", "event_year": 2023, "pier_id": "E2", "longitudinal_movement_in": 1.0},
            ]
        )

        result = compute_movement_sensitivity(events, movement)

        self.assertIn("E1_longitudinal_movement_in", result.columns)
        self.assertIn("E2_longitudinal_movement_in", result.columns)
        self.assertTrue(pd.isna(result.loc[0, "E1_movement_per_day_below_7"]))
        self.assertEqual(result.loc[1, "E1_movement_per_day_below_7"], 0.2)
        self.assertEqual(result.loc[1, "E2_movement_per_cumulative_deficit_below_7"], 0.05)
        self.assertEqual(result.loc[1, "E1_movement_per_LWSI"], 2.0)

    def test_empty_input_returns_expected_columns(self):
        result = compute_movement_sensitivity(pd.DataFrame(), pd.DataFrame())
        self.assertIn("LWSI", result.columns)
        self.assertIn("E1_movement_per_LWSI", result.columns)
        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
