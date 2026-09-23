import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai.core.baseline import calculate_baseline
from ai.core.drift_engine import analyze_drift
from backend.app.database import get_connection
from backend.app.main import create_app
from backend.app.services.ai_service import adapt_drift_result


class AIIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "integration.db"
        self.client = self.enterContext(TestClient(create_app(self.path), raise_server_exceptions=False))

    def snapshot(self):
        with get_connection(self.path) as connection:
            return {
                table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY id")]
                for table in ("daily_checkins", "sensor_readings")
            }

    def test_calculate_persist_and_read_baseline(self):
        with patch("backend.app.services.ai_service.calculate_baseline", wraps=calculate_baseline) as engine:
            response = self.client.post("/api/baseline/ASTRO-001/calculate")
        self.assertEqual(response.status_code, 201)
        engine.assert_called_once()
        baseline = response.json()
        self.assertEqual(baseline["observation_days"], 7)
        for field, expected in {"sleep_hours_avg": 7.342857, "mood_avg": 7.428571,
                                "stress_avg": 3, "fatigue_avg": 3, "energy_avg": 8,
                                "social_level_avg": 8, "activity_minutes_avg": 55}.items():
            self.assertAlmostEqual(baseline[field], expected, places=6)
        self.assertEqual(self.client.get("/api/baseline/ASTRO-001").json(), baseline)
        with get_connection(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM baselines").fetchone()[0], 2)

    def test_baseline_reads_sqlite_changes_without_loading_seeds(self):
        with get_connection(self.path) as connection:
            connection.execute("UPDATE daily_checkins SET sleep_hours = 8")
        with patch("pathlib.Path.read_text", side_effect=AssertionError("No files during requests")):
            response = self.client.post("/api/baseline/ASTRO-001/calculate")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["sleep_hours_avg"], 8)

    def test_get_baseline_does_not_calculate(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM baselines")
        with patch("backend.app.services.ai_service.calculate_baseline") as engine:
            response = self.client.get("/api/baseline/ASTRO-001")
            self.assertEqual(response.status_code, 404)
            engine.assert_not_called()

    def test_unknown_users(self):
        for method, route in (("get", "/api/baseline/UNKNOWN"), ("post", "/api/baseline/UNKNOWN/calculate"),
                              ("get", "/api/drift/UNKNOWN"), ("post", "/api/drift/UNKNOWN/analyze")):
            response = getattr(self.client, method)(route)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_insufficient_and_incomplete_data(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM daily_checkins WHERE id > 6")
        response = self.client.post("/api/baseline/ASTRO-001/calculate")
        self.assertEqual(response.status_code, 400)
        self.assertIn("7 jours", response.json()["error"]["message"])
        self.assertEqual(self.client.post("/api/drift/ASTRO-001/analyze").status_code, 400)
        with get_connection(self.path) as connection:
            connection.execute("UPDATE daily_checkins SET sleep_hours = NULL WHERE id = 1")
        self.assertEqual(self.client.post("/api/baseline/ASTRO-001/calculate").status_code, 400)

    def test_missing_baseline_is_clear(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM baselines")
        response = self.client.post("/api/drift/ASTRO-001/analyze")
        self.assertEqual(response.status_code, 400)
        self.assertIn("calculez", response.json()["error"]["message"])

    def test_real_engine_event_context_and_history(self):
        before = self.snapshot()
        self.client.post("/api/baseline/ASTRO-001/calculate")
        with patch("backend.app.services.ai_service.analyze_drift", wraps=analyze_drift) as engine:
            with patch("pathlib.Path.read_text", side_effect=AssertionError("No seed reads")):
                response = self.client.post("/api/drift/ASTRO-001/analyze")
        self.assertEqual(response.status_code, 200)
        engine.assert_called_once()
        args, kwargs = engine.call_args
        internal = analyze_drift(*args, **kwargs)
        stable = analyze_drift(args[0][:7], args[1], sensor_readings=kwargs["sensor_readings"])
        self.assertGreater(internal["drift_score"], stable["drift_score"])
        self.assertTrue(0 <= internal["drift_score"] <= 100)
        self.assertEqual(set(internal["sensor_context"]), {"movement", "heart_rate", "spo2"})
        event = response.json()
        self.assertEqual(event["drift_score"], internal["drift_score"] / 100)
        self.assertTrue(0 <= event["drift_score"] <= 1)
        self.assertEqual(event["level"], internal["level"])
        self.assertGreater(len(event["affected_signals"]), 1)
        self.assertEqual(set(event), {"id", "user_id", "detected_at", "level", "drift_score",
                                      "confidence", "affected_signals", "explanation", "status"})
        for forbidden in ("depressed", "depression", "anxiety disorder", "psychiatric disorder", "diagnosis", "mentally ill"):
            self.assertNotIn(forbidden, event["explanation"].lower())
        history = self.client.get("/api/drift/ASTRO-001").json()
        self.assertEqual(history[-1], event)
        with get_connection(self.path) as connection:
            row = connection.execute("SELECT affected_signals FROM drift_events WHERE id = ?", (event["id"],)).fetchone()
            self.assertEqual(json.loads(row[0]), event["affected_signals"])
        self.assertEqual(self.snapshot(), before)

    def test_sqlite_improvement_and_extreme_sensors_return_no_event(self):
        with get_connection(self.path) as connection:
            connection.execute("UPDATE daily_checkins SET sleep_hours=9, mood=10, stress=1, fatigue=1, "
                               "energy=10, social_level=10, activity_minutes=100 WHERE id >= 13")
            connection.execute("UPDATE sensor_readings SET value=500 WHERE sensor_type IN ('heart_rate', 'spo2')")
        response = self.client.post("/api/drift/ASTRO-001/analyze")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(len(self.client.get("/api/drift/ASTRO-001").json()), 2)

    def test_empty_history_existing_user(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users (user_id, first_name, created_at) VALUES (?, ?, ?)",
                               ("ASTRO-002", "Sam", "2080-01-01T00:00:00Z"))
        self.assertEqual(self.client.get("/api/drift/ASTRO-002").json(), [])

    def test_internal_engine_error_not_exposed_or_saved(self):
        with patch("backend.app.services.ai_service.analyze_drift", side_effect=RuntimeError("secret internal trace")):
            with self.assertLogs("backend.app.main", level="ERROR"):
                response = self.client.post("/api/drift/ASTRO-001/analyze")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "internal_error")
        self.assertNotIn("secret", response.text)
        self.assertEqual(len(self.client.get("/api/drift/ASTRO-001").json()), 2)

    def test_repeated_calculations_and_analyses_keep_history(self):
        first = self.client.post("/api/baseline/ASTRO-001/calculate").json()
        second = self.client.post("/api/baseline/ASTRO-001/calculate").json()
        self.assertGreater(second["calculated_at"], first["calculated_at"])
        self.assertEqual(self.client.get("/api/baseline/ASTRO-001").json(), second)
        a = self.client.post("/api/drift/ASTRO-001/analyze").json()
        b = self.client.post("/api/drift/ASTRO-001/analyze").json()
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(self.client.get("/api/drift/ASTRO-001").json()[-2:], [a, b])

    def test_adapter_low_and_internal_fields_omitted(self):
        internal = {"user_id": "ASTRO-001", "drift_score": 25, "level": "mild", "confidence": 1,
                    "affected_signals": {"fatigue": {"severity": 0.5}}, "sensor_context": {},
                    "explanation": "Fatigue increased.", "recent_window_days": 3}
        event = adapt_drift_result(internal, "2080-04-16T00:00:00Z")
        self.assertEqual(event["level"], "low")
        self.assertEqual(event["drift_score"], 0.25)
        self.assertEqual(event["affected_signals"], ["fatigue"])
        self.assertNotIn("sensor_context", event)


if __name__ == "__main__":
    unittest.main()
