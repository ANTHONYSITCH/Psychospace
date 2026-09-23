import copy
import json
import unittest

from ai.core.baseline import calculate_baseline
from ai.core.data_loader import SIGNALS, load_checkins, load_sensor_readings
from ai.core.drift_engine import WEIGHTS, analyze_drift, classify_score


class DriftTests(unittest.TestCase):
    def setUp(self):
        self.checkins = load_checkins()
        self.sensors = load_sensor_readings()
        self.baseline = calculate_baseline(self.checkins)

    def test_initial_period_stable_and_final_higher(self):
        stable = analyze_drift(self.checkins[:7], self.baseline)
        final = analyze_drift(self.checkins, self.baseline)
        self.assertEqual(stable["level"], "stable")
        self.assertLess(stable["drift_score"], 20)
        self.assertGreater(final["drift_score"], stable["drift_score"])
        self.assertEqual(final["level"], "high")
        self.assertEqual(set(final["affected_signals"]), set(SIGNALS))

    def test_weighted_score_is_really_calculated(self):
        final = analyze_drift(self.checkins, self.baseline)
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1)
        recent_sleep = sum(r["sleep_hours"] for r in self.checkins[-3:]) / 3
        expected = (self.baseline["sleep_hours_avg"] - recent_sleep) / (0.25 * self.baseline["sleep_hours_avg"])
        self.assertAlmostEqual(final["affected_signals"]["sleep_hours"]["severity"], expected, places=6)
        score = sum(d["severity"] * WEIGHTS[s] for s, d in final["affected_signals"].items()) * 100
        self.assertAlmostEqual(final["drift_score"], score, places=2)

    def test_score_bounds_and_thresholds(self):
        for days in range(7, 16):
            result = analyze_drift(self.checkins[:days], self.baseline)
            self.assertTrue(0 <= result["drift_score"] <= 100)
            self.assertEqual(result["level"], classify_score(result["drift_score"]))
        for score, level in ((0, "stable"), (19.99, "stable"), (20, "mild"),
                             (39.99, "mild"), (40, "moderate"), (59.99, "moderate"),
                             (60, "high"), (100, "high")):
            self.assertEqual(classify_score(score), level)

    def test_isolated_bad_datum_not_high(self):
        rows = copy.deepcopy(self.checkins[:7])
        rows[-1]["fatigue"] = 10
        result = analyze_drift(rows, self.baseline)
        self.assertLess(result["drift_score"], 60)
        self.assertNotEqual(result["level"], "high")

    def test_opposite_directions_do_not_increase_score(self):
        rows = copy.deepcopy(self.checkins)
        for row in rows[-3:]:
            row.update(sleep_hours=10, mood=10, stress=1, fatigue=1,
                       energy=10, social_level=10, activity_minutes=100)
        result = analyze_drift(rows, self.baseline)
        self.assertEqual(result["drift_score"], 0)
        self.assertEqual(result["affected_signals"], {})

    def test_only_one_changed_signal_is_bounded_by_weight(self):
        rows = copy.deepcopy(self.checkins)
        for row in rows[-3:]:
            row.update(sleep_hours=10, mood=10, stress=1, fatigue=10,
                       energy=10, social_level=10, activity_minutes=100)
        result = analyze_drift(rows, self.baseline)
        self.assertEqual(result["drift_score"], 15)
        self.assertEqual(set(result["affected_signals"]), {"fatigue"})
        self.assertIn("Fatigue", result["explanation"])
        self.assertNotIn("Sleep", result["explanation"])

    def test_persistence_and_real_changes(self):
        result = analyze_drift(self.checkins, self.baseline)
        for signal, item in result["affected_signals"].items():
            mean = sum(r[signal] for r in self.checkins[-3:]) / 3
            self.assertAlmostEqual(item["recent"], mean, places=6)
            self.assertAlmostEqual(item["change"], mean - item["baseline"], places=6)
            self.assertEqual(item["persistence_days"], 3)
            self.assertTrue(0.25 <= item["severity"] <= 1)

    def test_explanations_have_no_forbidden_terms(self):
        for days in range(7, 16):
            explanation = analyze_drift(self.checkins[:days], self.baseline)["explanation"].lower()
            for forbidden in ("depressed", "depression", "anxiety disorder", "psychiatric disorder", "diagnosis", "mentally ill"):
                self.assertNotIn(forbidden, explanation)

    def test_movement_confirmation_and_context(self):
        result = analyze_drift(self.checkins, self.baseline, self.sensors)
        context = result["sensor_context"]
        self.assertTrue(context["movement"]["confirms_activity_decrease"])
        self.assertEqual(set(context), {"heart_rate", "spo2", "movement"})
        self.assertEqual(context["movement"]["reading_count"], 6)
        self.assertEqual(result["drift_score"], analyze_drift(self.checkins, self.baseline)["drift_score"])

    def test_heart_rate_and_spo2_do_not_trigger_drift(self):
        sensors = copy.deepcopy(self.sensors)
        for row in sensors:
            if row["sensor_type"] in ("heart_rate", "spo2"):
                row["value"] *= 2
        result = analyze_drift(self.checkins[:7], self.baseline, sensors)
        control = analyze_drift(self.checkins[:7], self.baseline)
        self.assertEqual(result["drift_score"], control["drift_score"])
        self.assertEqual(result["level"], "stable")

    def test_future_sensor_data_excluded(self):
        stable = analyze_drift(self.checkins[:7], self.baseline, self.sensors)
        sensors = [r for r in self.sensors if r["timestamp"] <= self.checkins[6]["timestamp"]]
        self.assertEqual(stable, analyze_drift(self.checkins[:7], self.baseline, sensors))

    def test_confidence_reflects_missing_days(self):
        rows = self.checkins[:13] + self.checkins[14:]
        result = analyze_drift(rows, self.baseline)
        self.assertEqual(result["recent_window_days"], 2)
        self.assertAlmostEqual(result["confidence"], 2 / 3, places=6)
        self.assertEqual(analyze_drift(self.checkins, self.baseline)["confidence"], 1)

    def test_zero_reference_durations(self):
        rows = copy.deepcopy(self.checkins)
        for row in rows[:7]:
            row.update(sleep_hours=0, activity_minutes=0)
        result = analyze_drift(rows, calculate_baseline(rows))
        self.assertNotIn("sleep_hours", result["affected_signals"])
        self.assertNotIn("activity_minutes", result["affected_signals"])
        json.dumps(result, allow_nan=False)

    def test_invalid_inputs_rejected(self):
        for window in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                analyze_drift(self.checkins, self.baseline, recent_window=window)
        with self.assertRaises(ValueError):
            analyze_drift(self.checkins[:3], self.baseline)
        baseline = {**self.baseline, "user_id": "OTHER"}
        with self.assertRaises(ValueError):
            analyze_drift(self.checkins, baseline)
        sensors = copy.deepcopy(self.sensors)
        for row in sensors:
            row["user_id"] = "OTHER"
        with self.assertRaises(ValueError):
            analyze_drift(self.checkins, self.baseline, sensors)

    def test_deterministic_and_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.checkins, self.baseline, self.sensors))
        result = analyze_drift(self.checkins, self.baseline, self.sensors)
        self.assertEqual(result, analyze_drift(list(reversed(self.checkins)), self.baseline, list(reversed(self.sensors))))
        self.assertEqual(before, (self.checkins, self.baseline, self.sensors))
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
