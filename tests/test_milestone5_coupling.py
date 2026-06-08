import unittest

import pandas as pd

from src.movement_analysis import compute_coupling_metrics


class CouplingMetricsTests(unittest.TestCase):
    def test_classifies_coupled_when_ratio_and_tolerance_pass(self):
        movement = pd.DataFrame(
            [
                {"event_id": "LW-001", "event_year": 2026, "pier_id": "E1", "longitudinal_movement_in": 4.0},
                {"event_id": "LW-001", "event_year": 2026, "pier_id": "E2", "longitudinal_movement_in": 4.2},
            ]
        )

        coupling = compute_coupling_metrics(movement)
        row = coupling.iloc[0]

        self.assertEqual(row["coupling_status"], "Coupled")
        self.assertAlmostEqual(row["coupling_ratio"], 4.0 / 4.2)
        self.assertAlmostEqual(row["differential_movement_in"], 0.2)
        self.assertAlmostEqual(row["tolerance_in"], 0.615)
        self.assertIn("similar magnitude and direction", row["interpretation"])

    def test_classifies_stable_minimal_before_ratio_checks(self):
        movement = pd.DataFrame(
            [
                {"event_id": "LW-002", "event_year": 2026, "pier_id": "E1", "longitudinal_movement_in": 0.05},
                {"event_id": "LW-002", "event_year": 2026, "pier_id": "E2", "longitudinal_movement_in": 0.08},
            ]
        )

        row = compute_coupling_metrics(movement).iloc[0]

        self.assertEqual(row["coupling_status"], "Stable / Minimal Movement")
        self.assertIn("small", row["interpretation"])

    def test_classifies_opposite_signs_as_not_coupled(self):
        movement = pd.DataFrame(
            [
                {"event_id": "LW-003", "event_year": 2026, "pier_id": "E1", "longitudinal_movement_in": 1.0},
                {"event_id": "LW-003", "event_year": 2026, "pier_id": "E2", "longitudinal_movement_in": -1.1},
            ]
        )

        row = compute_coupling_metrics(movement).iloc[0]

        self.assertEqual(row["coupling_status"], "Not Coupled")

    def test_classifies_missing_e1_or_e2_as_insufficient_data(self):
        movement = pd.DataFrame(
            [
                {"event_id": "LW-004", "event_year": 2026, "pier_id": "E1", "longitudinal_movement_in": 1.0},
            ]
        )

        row = compute_coupling_metrics(movement).iloc[0]

        self.assertEqual(row["coupling_status"], "Insufficient Data")
        self.assertTrue(pd.isna(row["E2_longitudinal_movement_in"]))

    def test_classifies_same_direction_outside_ratio_as_not_strongly_coupled(self):
        movement = pd.DataFrame(
            [
                {"event_id": "LW-005", "event_year": 2026, "pier_id": "E1", "longitudinal_movement_in": 1.0},
                {"event_id": "LW-005", "event_year": 2026, "pier_id": "E2", "longitudinal_movement_in": 2.0},
            ]
        )

        row = compute_coupling_metrics(movement).iloc[0]

        self.assertEqual(row["coupling_status"], "Not Strongly Coupled")
        self.assertIn("not strongly coupled", row["interpretation"])


if __name__ == "__main__":
    unittest.main()
