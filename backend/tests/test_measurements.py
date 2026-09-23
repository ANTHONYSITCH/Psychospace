import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.database import get_connection
from backend.app.main import create_app


CHECKIN = {
    "user_id": "ASTRO-001", "timestamp": "2080-04-16T18:00:00Z",
    "sleep_hours": 6.5, "mood": 6, "stress": 5, "fatigue": 6,
    "energy": 5, "social_level": 4, "activity_minutes": 22.5,
}
SENSOR = {
    "user_id": "ASTRO-001", "sensor_type": "heart_rate", "value": 72,
    "unit": "bpm", "timestamp": "2080-04-16T17:00:00Z",
}


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "measurements.db"
        self.client = self.enterContext(TestClient(create_app(self.path)))

    def test_create_checkin_and_sqlite_persistence(self):
        response = self.client.post("/api/checkins", json=CHECKIN)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"success": True, "checkin_id": 16})
        with get_connection(self.path) as connection:
            row = dict(connection.execute("SELECT * FROM daily_checkins WHERE id = ?", (16,)).fetchone())
        row.pop("id")
        self.assertEqual(row, CHECKIN)
        with TestClient(create_app(self.path)) as restarted:
            self.assertEqual(restarted.get("/api/checkins/ASTRO-001").json()[-1], CHECKIN)

    def test_checkin_history_order_and_fields(self):
        later = {**CHECKIN, "timestamp": "2080-04-17T18:00:00Z"}
        self.assertEqual(self.client.post("/api/checkins", json=later).status_code, 201)
        self.assertEqual(self.client.post("/api/checkins", json=CHECKIN).status_code, 201)
        response = self.client.get("/api/checkins/ASTRO-001")
        self.assertEqual(response.status_code, 200)
        history = response.json()
        self.assertEqual(len(history), 17)
        self.assertEqual(history[-2:], [CHECKIN, later])
        self.assertTrue(all(set(row) == set(CHECKIN) for row in history))

    def test_checkin_invalid_scores_and_durations(self):
        for field in ("mood", "stress", "fatigue", "energy", "social_level"):
            for value in (0, 11, 1.5, True, "5"):
                with self.subTest(field=field, value=value):
                    response = self.client.post("/api/checkins", json={**CHECKIN, field: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"]["code"], "invalid_data")
        for field in ("sleep_hours", "activity_minutes"):
            self.assertEqual(self.client.post("/api/checkins", json={**CHECKIN, field: -1}).status_code, 400)
        self.assertEqual(len(self.client.get("/api/checkins/ASTRO-001").json()), 15)

    def test_checkin_boundaries(self):
        body = {**CHECKIN, "sleep_hours": 0, "activity_minutes": 0,
                "mood": 1, "stress": 10, "fatigue": 1, "energy": 10, "social_level": 1}
        self.assertEqual(self.client.post("/api/checkins", json=body).status_code, 201)

    def test_heart_rate_and_movement_persist(self):
        movement = {**SENSOR, "sensor_type": "movement", "value": 0.7, "unit": "m/s²"}
        for index, body in enumerate((SENSOR, movement), start=91):
            response = self.client.post("/api/sensors", json=body)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json(), {"success": True, "sensor_reading_id": index})
            with get_connection(self.path) as connection:
                row = dict(connection.execute("SELECT * FROM sensor_readings WHERE id = ?", (index,)).fetchone())
            row.pop("id")
            self.assertEqual(row, body)

    def test_sensor_types_are_extensible(self):
        for sensor_type, unit, value in (("spo2", "%", 98), ("temperature", "°C", -2.5)):
            body = {**SENSOR, "sensor_type": sensor_type, "unit": unit, "value": value}
            self.assertEqual(self.client.post("/api/sensors", json=body).status_code, 201)

    def test_sensor_history_chronology_and_ties(self):
        times = ["2080-04-16T17:00:00.1Z", "2080-04-16T17:00:00Z",
                 "2080-04-16T17:00:00.000001Z", "2080-04-16T17:00:00Z"]
        bodies = [{**SENSOR, "timestamp": stamp, "value": 70 + i} for i, stamp in enumerate(times)]
        for body in bodies:
            self.assertEqual(self.client.post("/api/sensors", json=body).status_code, 201)
        response = self.client.get("/api/sensors/ASTRO-001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[-4:], [bodies[1], bodies[3], bodies[2], bodies[0]])
        self.assertTrue(all(set(row) == set(SENSOR) for row in response.json()))

    def test_sensor_invalid_values_and_units(self):
        for field, value in (("sensor_type", " "), ("value", "72"), ("value", True),
                             ("value", None), ("unit", ""), ("unit", "%")):
            with self.subTest(field=field, value=value):
                self.assertEqual(self.client.post("/api/sensors", json={**SENSOR, field: value}).status_code, 400)
        for value in (float("nan"), float("inf"), -float("inf")):
            response = self.client.post("/api/sensors", content=json.dumps({**SENSOR, "value": value}),
                                        headers={"Content-Type": "application/json"})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.client.get("/api/sensors/ASTRO-001").json()), 90)

    def test_unknown_users_and_sql_injection(self):
        for route, body in (("checkins", CHECKIN), ("sensors", SENSOR)):
            for user_id in ("UNKNOWN", "' OR 1=1 --"):
                with self.subTest(route=route, user_id=user_id):
                    response = self.client.post(f"/api/{route}", json={**body, "user_id": user_id})
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(response.json()["error"]["code"], "not_found")
                    self.assertEqual(self.client.get(f"/api/{route}/{user_id}").status_code, 404)

    def test_existing_user_empty_histories_and_isolation(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users (user_id, first_name, created_at) VALUES (?, ?, ?)",
                               ("ASTRO-002", "Sam", "2080-04-01T00:00:00Z"))
        for route, body in (("checkins", CHECKIN), ("sensors", SENSOR)):
            response = self.client.get(f"/api/{route}/ASTRO-002")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), [])
            self.client.post(f"/api/{route}", json={**body, "user_id": "ASTRO-002"})
            self.assertTrue(all(row["user_id"] == "ASTRO-001"
                                for row in self.client.get(f"/api/{route}/ASTRO-001").json()))

    def test_invalid_timestamps(self):
        for route, body in (("checkins", CHECKIN), ("sensors", SENSOR)):
            for timestamp in ("invalid", "2080-02-30T18:00:00Z", "2080-04-16",
                              "2080-04-16T18:00:00", "2080-04-16T25:00:00Z", 123):
                with self.subTest(route=route, timestamp=timestamp):
                    self.assertEqual(self.client.post(f"/api/{route}",
                                     json={**body, "timestamp": timestamp}).status_code, 400)

    def test_missing_extra_fields_and_malformed_json(self):
        for route, body in (("checkins", CHECKIN), ("sensors", SENSOR)):
            missing = {key: value for key, value in body.items() if key != "timestamp"}
            for invalid in (missing, {**body, "extra": 1}, {**body, "user_id": " "}):
                self.assertEqual(self.client.post(f"/api/{route}", json=invalid).status_code, 400)
            self.assertEqual(self.client.post(f"/api/{route}", content="{invalid",
                             headers={"Content-Type": "application/json"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
