import unittest

from src.pp15_risk import (
    classify_pp15_risk,
    compute_pp15_risk,
    generate_pp15_recommendation,
    simulate_additional_movement,
)


class PP15RiskTests(unittest.TestCase):
    def test_simulates_additional_movement_with_non_negative_inputs(self):
        self.assertEqual(simulate_additional_movement(5, 0.10), 0.5)
        self.assertEqual(simulate_additional_movement(-5, 0.10), 0.0)
        self.assertEqual(simulate_additional_movement(5, -0.10), 0.0)

    def test_classifies_risk_from_predicted_movement_and_remaining_allowance(self):
        self.assertEqual(classify_pp15_risk(0.24, 0.5), "Normal")
        self.assertEqual(classify_pp15_risk(0.25, 0.5), "Watch")
        self.assertEqual(classify_pp15_risk(0.40, 0.5), "Critical")
        self.assertEqual(classify_pp15_risk(0.50, 0.5), "Span Jacking Likely")

    def test_non_positive_remaining_allowance_is_already_critical(self):
        self.assertEqual(classify_pp15_risk(0.0, 0.0), "Span Jacking Likely")
        self.assertEqual(classify_pp15_risk(0.1, -0.1), "Span Jacking Likely")

    def test_generates_recommendations(self):
        self.assertEqual(generate_pp15_recommendation("Normal"), "Continue routine monitoring.")
        self.assertEqual(generate_pp15_recommendation("Watch"), "Increase review frequency during low-water period.")
        self.assertEqual(generate_pp15_recommendation("Critical"), "Verify PP-15 joint clearance and prepare contingency plan.")
        self.assertEqual(
            generate_pp15_recommendation("Span Jacking Likely"),
            "Coordinate engineering review and consider span-jacking preparation.",
        )

    def test_compute_pp15_risk_returns_scenario_outputs(self):
        result = compute_pp15_risk(remaining_allowable_in=0.5, predicted_additional_movement_in=0.5)
        self.assertEqual(result["risk_level"], "Span Jacking Likely")
        self.assertEqual(result["remaining_after_scenario_in"], 0.0)
        self.assertEqual(result["risk_ratio"], 1.0)
        self.assertEqual(result["recommendation"], "Coordinate engineering review and consider span-jacking preparation.")


if __name__ == "__main__":
    unittest.main()
