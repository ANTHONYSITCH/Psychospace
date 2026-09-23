import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import SEEDS_PATH
from backend.app.database import get_connection, initialize_database
from backend.app.main import create_app
from backend.app.seed_loader import load_seeds


class ProfileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "test.db"
        self.app = create_app(self.path)
        self.client = self.enterContext(TestClient(self.app, raise_server_exceptions=False))
        self.expected = json.loads((SEEDS_PATH / "astro-001-profile.json").read_text(encoding="utf-8"))

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "PsychoSpace API"})

    def test_user_and_all_seed_counts(self):
        counts = {"users": 1, "profiles": 1, "daily_checkins": 15, "sensor_readings": 90,
                  "memories": 6, "baselines": 1, "drift_events": 2, "interventions": 4, "chat_messages": 0}
        with get_connection(self.path) as connection:
            for table, expected in counts.items():
                self.assertEqual(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], expected)
            self.assertEqual(connection.execute("SELECT user_id FROM users").fetchone()[0], "ASTRO-001")
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_profile_matches_seed(self):
        response = self.client.get("/api/profile/ASTRO-001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], "ASTRO-001")
        self.assertEqual(response.json(), self.expected)

    def test_unknown_user_and_injection(self):
        for user_id in ("UNKNOWN", "' OR 1=1 --"):
            response = self.client.get(f"/api/profile/{user_id}")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_profile_reads_database_and_preserves_edits_on_restart(self):
        with get_connection(self.path) as connection:
            connection.execute("UPDATE users SET first_name = ? WHERE user_id = ?", ("Alex modifié", "ASTRO-001"))
        with TestClient(create_app(self.path)) as restarted:
            self.assertEqual(restarted.get("/api/profile/ASTRO-001").json()["first_name"], "Alex modifié")
        self.test_user_and_all_seed_counts()

    def test_repeated_initialization(self):
        initialize_database(self.path)
        initialize_database(self.path)
        self.assertFalse(load_seeds(self.path))
        self.test_user_and_all_seed_counts()

    def test_internal_error_does_not_expose_details(self):
        with get_connection(self.path) as connection:
            connection.execute("UPDATE profiles SET interests = ?", ("invalid JSON",))
        with self.assertLogs("backend.app.main", level="ERROR"):
            response = self.client.get("/api/profile/ASTRO-001")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"success": False, "error": {
            "code": "internal_error", "message": "Une erreur interne est survenue."
        }})

    def test_missing_profile(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM profiles WHERE user_id = ?", ("ASTRO-001",))
        self.assertEqual(self.client.get("/api/profile/ASTRO-001").status_code, 404)

    def test_only_requested_business_routes(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertEqual(set(paths), {
            "/health", "/api/profile/{user_id}", "/api/checkins",
            "/api/checkins/{user_id}", "/api/sensors", "/api/sensors/{user_id}",
        })
        self.assertEqual(set(paths["/api/profile/{user_id}"]), {"get"})

    def test_partial_schema_is_not_overwritten(self):
        path = self.path.with_name("partial.db")
        with get_connection(path) as connection:
            connection.execute("CREATE TABLE existing_data (value TEXT)")
            connection.execute("INSERT INTO existing_data VALUES (?)", ("preserve",))
        with self.assertRaisesRegex(RuntimeError, "schéma"):
            initialize_database(path)
        with get_connection(path) as connection:
            self.assertEqual(connection.execute("SELECT value FROM existing_data").fetchone()[0], "preserve")

    def test_failed_seed_rolls_back_and_can_retry(self):
        path = self.path.with_name("rollback.db")
        directory = self.path.parent / "seeds"
        shutil.copytree(SEEDS_PATH, directory)
        file = directory / "astro-001-interventions.json"
        interventions = json.loads(file.read_text(encoding="utf-8"))
        interventions[-1]["drift_event_id"] = "MISSING"
        file.write_text(json.dumps(interventions), encoding="utf-8")
        initialize_database(path)
        with self.assertRaises(sqlite3.IntegrityError):
            load_seeds(path, directory)
        with get_connection(path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0], 0)
        self.assertTrue(load_seeds(path))


if __name__ == "__main__":
    unittest.main()
