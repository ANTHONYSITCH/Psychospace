import copy
import json
import tempfile
import unittest
from pathlib import Path

from ai.core.baseline import calculate_baseline
from ai.core.data_loader import SEEDS_PATH, SIGNALS, load_checkins, load_sensor_readings


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.checkins = load_checkins()

    def test_first_seven_days_match_real_seed(self):
        baseline = calculate_baseline(self.checkins)
        seed = json.loads((SEEDS_PATH / "astro-001-baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(set(baseline), set(seed))
        self.assertEqual(baseline["user_id"], "ASTRO-001")
        self.assertEqual(baseline["observation_days"], 7)
        for field in SIGNALS:
            expected = sum(row[field] for row in self.checkins[:7]) / 7
            self.assertAlmostEqual(baseline[field + "_avg"], expected, places=6)
            self.assertAlmostEqual(baseline[field + "_avg"], seed[field + "_avg"], places=6)

    def test_reference_does_not_use_later_days(self):
        baseline = calculate_baseline(self.checkins)
        self.assertEqual(baseline, calculate_baseline(self.checkins[:7]))
        self.assertEqual(baseline, calculate_baseline(list(reversed(self.checkins))))

    def test_custom_observation_period(self):
        baseline = calculate_baseline(self.checkins, observation_days=3)
        self.assertEqual(baseline["observation_days"], 3)
        self.assertAlmostEqual(baseline["activity_minutes_avg"], sum(r["activity_minutes"] for r in self.checkins[:3]) / 3, places=6)

    def test_invalid_day_counts_and_insufficient_data(self):
        for count in (0, -1, True, 1.5, 16):
            with self.subTest(count=count), self.assertRaises(ValueError):
                calculate_baseline(self.checkins, count)

    def test_missing_fields_and_invalid_values(self):
        for field, value in (("mood", 11), ("energy", True), ("sleep_hours", -1),
                             ("activity_minutes", float("nan")), ("timestamp", "2080-02-30T18:00:00Z")):
            rows = copy.deepcopy(self.checkins)
            rows[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                calculate_baseline(rows)
        rows = copy.deepcopy(self.checkins)
        del rows[0]["mood"]
        with self.assertRaises(ValueError):
            calculate_baseline(rows)

    def test_mixed_users_and_duplicate_days_rejected(self):
        rows = copy.deepcopy(self.checkins)
        rows[0]["user_id"] = "OTHER"
        with self.assertRaises(ValueError):
            calculate_baseline(rows)
        with self.assertRaises(ValueError):
            calculate_baseline(self.checkins + [self.checkins[0]])

    def test_loaders_real_structure_and_no_mutation(self):
        before = copy.deepcopy(self.checkins)
        calculate_baseline(self.checkins)
        self.assertEqual(before, self.checkins)
        sensors = load_sensor_readings()
        self.assertEqual(len(self.checkins), 15)
        self.assertEqual(len(sensors), 90)
        self.assertEqual({r["sensor_type"] for r in sensors}, {"heart_rate", "spo2", "movement"})

    def test_file_errors_are_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            with self.assertRaisesRegex(ValueError, "Impossible de lire"):
                load_checkins(path)
            path.write_text("{bad", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Impossible de lire"):
                load_sensor_readings(path)
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkins(path)
            self.assertEqual(load_sensor_readings(path), [])


if __name__ == "__main__":
    unittest.main()
