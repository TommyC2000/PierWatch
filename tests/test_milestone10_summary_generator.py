import math
import unittest

from src.summary_generator import SUMMARY_KEYS, _fmt, generate_engineering_summary


# ── Synthetic fixtures ────────────────────────────────────────────────────────

def _event(event_id="LW-050", year=2022, event_class="Critical / 2022-like"):
    return {
        "event_id": event_id,
        "event_year": year,
        "start_date": "2022-08-29",
        "end_date": "2022-12-10",
        "duration_days": 104,
        "min_stage_ft": -0.35,
        "days_below_12": 103,
        "days_below_7": 62,
        "cumulative_deficit_below_7": 150.0,
        "event_class": event_class,
        "LWSI": 0.463,
    }


def _movement_rows():
    return [
        {"pier_id": "E1", "longitudinal_movement_in": 4.238, "data_availability": "Available"},
        {"pier_id": "E2", "longitudinal_movement_in": 3.849, "data_availability": "Available"},
        {"pier_id": "E3", "longitudinal_movement_in": -0.017, "data_availability": "Available"},
    ]


def _coupling():
    return {
        "event_id": "LW-050",
        "event_year": 2022,
        "E1_longitudinal_movement_in": 4.238,
        "E2_longitudinal_movement_in": 3.849,
        "average_abs_movement_in": 4.044,
        "coupling_ratio": 1.101,
        "differential_movement_in": 0.390,
        "tolerance_in": 0.607,
        "coupling_status": "Coupled",
        "interpretation": "E-1 and E-2 moved with similar magnitude and direction.",
    }


def _risk():
    return {
        "remaining_allowable_in": 0.5,
        "predicted_additional_movement_in": 0.5,
        "remaining_after_scenario_in": 0.0,
        "risk_ratio": 1.0,
        "risk_level": "Span Jacking Likely",
        "recommendation": "Coordinate engineering review and consider span-jacking preparation.",
    }


def _sensitivity():
    return {
        "event_id": "LW-050",
        "event_year": 2022,
        "LWSI": 0.463,
        "E1_longitudinal_movement_in": 4.238,
        "E2_longitudinal_movement_in": 3.849,
        "E1_movement_per_LWSI": 9.15,
        "E2_movement_per_LWSI": 8.31,
    }


def _quality_summary():
    return {
        "n_high": 11,
        "n_medium": 0,
        "n_low": 0,
        "n_poor": 0,
        "n_insufficient": 0,
        "n_total": 11,
        "avg_confidence_score": 0.9996,
    }


def _thermal_stats():
    return {
        "slope": -0.0366,
        "intercept": 0.261,
        "r_squared": 0.210,
        "record_count": 488,
        "status": "ok",
    }


# ── Tests for generate_engineering_summary ────────────────────────────────────

class SummaryStructureTests(unittest.TestCase):
    def _full_call(self):
        return generate_engineering_summary(
            selected_event_row=_event(),
            movement_rows=_movement_rows(),
            coupling_row=_coupling(),
            pp15_risk_result=_risk(),
            sensitivity_row=_sensitivity(),
            sensor_quality_summary=_quality_summary(),
            pp15_thermal_stats=_thermal_stats(),
            include_disclaimer=True,
        )

    def test_returns_dict_with_all_summary_keys(self):
        result = self._full_call()
        self.assertIsInstance(result, dict)
        for key in SUMMARY_KEYS:
            self.assertIn(key, result, msg=f"Missing key: {key}")

    def test_full_summary_text_is_nonempty(self):
        result = self._full_call()
        self.assertIsInstance(result["full_summary_text"], str)
        self.assertGreater(len(result["full_summary_text"]), 200)

    def test_executive_summary_is_nonempty(self):
        result = self._full_call()
        self.assertIsInstance(result["executive_summary"], str)
        self.assertGreater(len(result["executive_summary"]), 50)

    def test_disclaimer_present_when_requested(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), include_disclaimer=True
        )
        self.assertIn("screening-level", result["disclaimer"].lower())
        self.assertIn("DISCLAIMER", result["full_summary_text"].upper())

    def test_disclaimer_absent_when_not_requested(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), include_disclaimer=False
        )
        self.assertEqual(result["disclaimer"], "")

    def test_recommended_next_steps_generated(self):
        result = self._full_call()
        steps = result["recommended_next_steps"]
        self.assertGreater(len(steps), 50)
        self.assertIn("monitoring", steps.lower())

    def test_span_jacking_risk_appears_in_steps(self):
        result = self._full_call()
        steps = result["recommended_next_steps"]
        self.assertIn("Span Jacking Likely", steps)

    def test_coupled_status_appears_in_steps(self):
        result = self._full_call()
        steps = result["recommended_next_steps"]
        # "Coupled" movement detected -> extra step 6
        self.assertIn("coupled", steps.lower())

    def test_pp15_risk_fields_in_pp15_section(self):
        result = self._full_call()
        section = result["pp15_risk_summary"]
        self.assertIn("Span Jacking Likely", section)
        self.assertIn("0.500", section)  # remaining / predicted

    def test_pier_movement_values_in_text(self):
        result = self._full_call()
        text = result["pier_movement_summary"]
        self.assertIn("4.238", text)
        self.assertIn("3.849", text)

    def test_coupling_ratio_in_coupling_section(self):
        result = self._full_call()
        self.assertIn("1.101", result["coupling_summary"])
        self.assertIn("Coupled", result["coupling_summary"])

    def test_sensitivity_lwsi_in_sensitivity_section(self):
        result = self._full_call()
        self.assertIn("0.463", result["sensitivity_summary"])

    def test_thermal_r2_in_thermal_section(self):
        result = self._full_call()
        self.assertIn("0.210", result["thermal_context_summary"])

    def test_sensor_count_in_confidence_section(self):
        result = self._full_call()
        self.assertIn("11", result["sensor_confidence_summary"])


class SummaryMissingInputTests(unittest.TestCase):
    def test_no_event_returns_graceful_message(self):
        result = generate_engineering_summary(selected_event_row=None)
        self.assertIn("No event selected", result["executive_summary"])
        self.assertIsInstance(result["full_summary_text"], str)

    def test_no_movement_rows_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), movement_rows=None
        )
        self.assertIn(SUMMARY_KEYS[0], result)

    def test_no_coupling_row_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), coupling_row=None
        )
        self.assertEqual(result["coupling_summary"], "Not available for the selected event.")

    def test_no_risk_result_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), pp15_risk_result=None
        )
        self.assertIsInstance(result["full_summary_text"], str)

    def test_no_sensitivity_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), sensitivity_row=None
        )
        self.assertEqual(result["sensitivity_summary"], "Not available for the selected event.")

    def test_no_thermal_stats_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), pp15_thermal_stats=None
        )
        self.assertEqual(result["thermal_context_summary"], "Not available for the selected event.")

    def test_no_quality_summary_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), sensor_quality_summary=None
        )
        self.assertIsInstance(result["full_summary_text"], str)

    def test_empty_movement_rows_list_does_not_crash(self):
        result = generate_engineering_summary(
            selected_event_row=_event(), movement_rows=[]
        )
        # All three piers should report "Insufficient GPS data"
        text = result["pier_movement_summary"]
        self.assertIn("Insufficient GPS data", text)

    def test_nan_movement_values_do_not_crash(self):
        import math
        rows_with_nan = [
            {"pier_id": "E1", "longitudinal_movement_in": float("nan")},
            {"pier_id": "E2", "longitudinal_movement_in": None},
        ]
        result = generate_engineering_summary(
            selected_event_row=_event(), movement_rows=rows_with_nan
        )
        self.assertIsInstance(result["pier_movement_summary"], str)

    def test_all_none_inputs_returns_valid_dict(self):
        result = generate_engineering_summary(
            selected_event_row=_event(),
            movement_rows=None,
            coupling_row=None,
            pp15_risk_result=None,
            sensitivity_row=None,
            sensor_quality_summary=None,
            pp15_thermal_stats=None,
        )
        for key in SUMMARY_KEYS:
            self.assertIn(key, result)
        self.assertGreater(len(result["full_summary_text"]), 100)


class FmtHelperTests(unittest.TestCase):
    def test_formats_float(self):
        self.assertEqual(_fmt(3.14159, ".2f"), "3.14")

    def test_returns_na_for_none(self):
        self.assertEqual(_fmt(None), "N/A")

    def test_returns_na_for_nan(self):
        self.assertEqual(_fmt(float("nan")), "N/A")

    def test_returns_na_for_inf(self):
        self.assertEqual(_fmt(float("inf")), "N/A")

    def test_appends_unit(self):
        self.assertEqual(_fmt(1.5, ".1f", " in"), "1.5 in")

    def test_custom_na_string(self):
        self.assertEqual(_fmt(None, na="—"), "—")


if __name__ == "__main__":
    unittest.main()
