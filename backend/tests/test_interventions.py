import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.database import get_connection
from backend.app.main import create_app
from backend.app.services.intervention_service import recommend_intervention

BODY = {
    "id": "INT-TEST", "user_id": "ASTRO-001", "drift_event_id": "DRIFT-002",
    "created_at": "2081-01-01T12:00:00Z", "type": "music_break",
    "message": "Souhaites-tu écouter un peu de musique ?", "accepted": False, "completed": False,
}


class InterventionTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(folder) / "interventions.db"
        self.client = self.enterContext(TestClient(create_app(self.path)))

    def post(self, **changes):
        return self.client.post("/api/interventions", json={**BODY, **changes})

    def update(self, **fields):
        return self.client.patch("/api/interventions/INT-TEST", json=fields)

    def history(self, user="ASTRO-001"):
        return self.client.get(f"/api/interventions/{user}").json()

    def other_user(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users (user_id,first_name,created_at) VALUES ('OTHER','Sam','2080-01-01T00:00:00Z')")
            connection.execute("INSERT INTO drift_events (id,user_id,detected_at,level,affected_signals) "
                               "VALUES ('OTHER-DRIFT','OTHER','2080-01-01T00:00:00Z','low','[]')")

    def test_get_existing_and_boolean_contract(self):
        result = self.client.get("/api/interventions/ASTRO-001")
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.json())
        for row in result.json():
            self.assertEqual(set(row), set(BODY))
            self.assertIs(type(row["accepted"]), bool)
            self.assertIs(type(row["completed"]), bool)

    def test_unknown_user_and_drift(self):
        self.assertEqual(self.client.get("/api/interventions/UNKNOWN").status_code, 404)
        self.assertEqual(self.post(user_id="UNKNOWN").status_code, 404)
        self.assertEqual(self.post(drift_event_id="UNKNOWN").status_code, 404)

    def test_create_and_duplicate(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), BODY)
        self.assertEqual(self.post(message="Changed").status_code, 400)
        self.assertEqual(self.history()[-1], BODY)

    def test_cross_user_drift_rejected_and_get_isolated(self):
        self.other_user()
        self.assertEqual(self.history("OTHER"), [])
        self.assertEqual(self.post(drift_event_id="OTHER-DRIFT").status_code, 400)
        response = self.post(id="OTHER-INT", user_id="OTHER", drift_event_id="OTHER-DRIFT")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.history("OTHER"), [response.json()])
        self.assertNotIn("OTHER-INT", [row["id"] for row in self.history()])

    def test_invalid_fields(self):
        for field in ("id", "user_id", "drift_event_id", "type", "message"):
            for value in ("", " \n", None, 12):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.post(**{field: value}).status_code, 400)
        for field in ("accepted", "completed"):
            for value in (0, 1, "true", None):
                self.assertEqual(self.post(**{field: value}).status_code, 400)
        for date in ("invalid", "2080-02-30T00:00:00Z", "2080-01-01T00:00:00"):
            self.assertEqual(self.post(created_at=date).status_code, 400)
        self.assertEqual(self.post(accepted=False, completed=True).status_code, 400)
        self.assertEqual(self.post(extra="invalid").status_code, 400)
        for field in BODY:
            self.assertEqual(self.client.post("/api/interventions", json={k: v for k, v in BODY.items() if k != field}).status_code, 400)

    def test_type_vocabulary_remains_extensible(self):
        self.assertEqual(self.post(type="custom_support").status_code, 201)

    def test_accept_complete_and_persistence(self):
        self.post()
        accepted = self.update(accepted=True)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json(), {**BODY, "accepted": True})
        completed = self.update(completed=True)
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json(), {**BODY, "accepted": True, "completed": True})
        with get_connection(self.path) as connection:
            row = connection.execute("SELECT accepted,completed FROM interventions WHERE id=?", (BODY["id"],)).fetchone()
            self.assertEqual(tuple(row), (1, 1))
        with TestClient(create_app(self.path)) as restarted:
            self.assertIn(completed.json(), restarted.get("/api/interventions/ASTRO-001").json())

    def test_patch_inconsistent_final_state_and_refusal(self):
        self.post()
        self.assertEqual(self.update(completed=True).status_code, 400)
        self.assertEqual(self.history()[-1], BODY)
        self.assertEqual(self.update(accepted=False).status_code, 200)
        self.assertEqual(self.update(accepted=True, completed=True).status_code, 200)
        self.assertEqual(self.update(accepted=False).status_code, 400)
        self.assertEqual(self.update(accepted=False, completed=False).json(), BODY)

    def test_patch_only_allowed_strict_boolean_fields(self):
        self.post()
        self.assertEqual(self.update().status_code, 400)
        for field in set(BODY) - {"accepted", "completed"}:
            self.assertEqual(self.update(**{field: BODY[field]}).status_code, 400)
        for value in (None, 0, 1, "false", [], {}):
            for field in ("accepted", "completed"):
                self.assertEqual(self.update(**{field: value}).status_code, 400)
        self.assertEqual(self.history()[-1], BODY)

    def test_unknown_intervention_and_sql_injection(self):
        self.assertEqual(self.client.patch("/api/interventions/UNKNOWN", json={"accepted": True}).status_code, 404)
        self.assertEqual(self.post(drift_event_id="' OR 1=1 --").status_code, 404)
        self.assertEqual(self.client.get("/api/interventions/' OR 1=1 --").status_code, 404)

    def test_chronological_order_and_fractional_dates(self):
        for identifier, timestamp in (("Z", "2081-01-01T12:00:00.1Z"), ("B", "2081-01-01T12:00:00Z"), ("A", "2081-01-01T12:00:00Z")):
            self.post(id=identifier, created_at=timestamp)
        self.assertEqual([row["id"] for row in self.history()][-3:], ["A", "B", "Z"])

    def test_no_seed_reads_or_implicit_creation(self):
        before = self.history()
        with patch("pathlib.Path.read_text", side_effect=AssertionError("No seeds")):
            for _ in range(2):
                self.assertIsNotNone(recommend_intervention(self.path, "ASTRO-001"))
                self.assertEqual(self.history(), before)
            with patch("backend.app.routes.chat.generate_reply", return_value="Un moment calme peut aider."):
                self.assertEqual(self.client.post("/api/chat", json={"user_id": "ASTRO-001", "message": "Bonjour"}).status_code, 200)
            self.assertEqual(self.history(), before)
            self.assertEqual(self.post().status_code, 201)
            self.assertEqual(self.update(accepted=True).status_code, 200)

    def test_swagger_methods(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        for path, method in (("/api/interventions", "post"), ("/api/interventions/{user_id}", "get"),
                             ("/api/interventions/{intervention_id}", "patch")):
            self.assertEqual(set(paths[path]), {method})


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(folder) / "recommendation.db"
        self.client = self.enterContext(TestClient(create_app(self.path)))

    def recommend(self):
        return recommend_intervention(self.path, "ASTRO-001")

    def test_music_uses_real_memory_and_latest_drift(self):
        result = self.recommend()
        self.assertEqual(result["type"], "music_break")
        self.assertEqual(result["memory_id"], "MEM-001")
        self.assertEqual(result["drift_event_id"], "DRIFT-002")
        self.assertIn("fatigue", result["explanation"]["affected_signals"])
        self.assertEqual(result, self.recommend())

    def test_physical_activity_by_priority(self):
        with get_connection(self.path) as connection:
            connection.execute("UPDATE memories SET importance=10 WHERE id='MEM-002'")
        result = self.recommend()
        self.assertEqual(result["type"], "short_activity")
        self.assertEqual(result["memory_id"], "MEM-002")

    def test_activity_requires_relevant_signal(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM memories WHERE id != 'MEM-002'")
            connection.execute("UPDATE drift_events SET affected_signals='[\"fatigue\"]'")
        self.assertIsNone(self.recommend()["memory_id"])

    def test_need_for_space_is_conditional(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM memories WHERE id != 'MEM-003'")
        result = self.recommend()
        self.assertEqual(result["type"], "quiet_break")
        self.assertEqual(result["memory_id"], "MEM-003")
        self.assertNotIn("conflit", result["message"])

    def test_missing_memories_do_not_invent_preferences(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM memories")
        result = self.recommend()
        self.assertIsNone(result["memory_id"])
        self.assertIsNone(result["explanation"]["memory_content"])
        self.assertNotIn("musique", result["message"])

    def test_negative_or_unknown_preferences_are_not_used(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM memories WHERE id != 'MEM-001'")
        for content in ("La musique n'aide pas Alex.", "Music does not help Alex.", "Alex aime les étoiles."):
            with get_connection(self.path) as connection:
                connection.execute("UPDATE memories SET content=?", (content,))
            self.assertIsNone(self.recommend()["memory_id"])

    def test_english_coping_memory(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM memories WHERE id != 'MEM-001'")
            connection.execute("UPDATE memories SET content='Music helps Alex under pressure.', category='coping_strategy'")
        self.assertEqual(self.recommend()["type"], "music_break")

    def test_no_drift_means_no_recommendation(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users (user_id,first_name,created_at) VALUES ('OTHER','Sam','2080-01-01T00:00:00Z')")
        self.assertIsNone(recommend_intervention(self.path, "OTHER"))

    def test_latest_drift_and_user_isolation(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users (user_id,first_name,created_at) VALUES ('OTHER','Sam','2080-01-01T00:00:00Z')")
            connection.execute("INSERT INTO drift_events (id,user_id,detected_at,level,affected_signals) "
                               "VALUES ('LATEST','ASTRO-001','2081-01-01T00:00:00Z','low','[\"energy\"]')")
            connection.execute("INSERT INTO drift_events (id,user_id,detected_at,level,affected_signals) "
                               "VALUES ('LAST-INSERTED','ASTRO-001','2080-01-01T00:00:00Z','low','[\"fatigue\"]')")
        result = self.recommend()
        self.assertEqual(result["drift_event_id"], "LATEST")
        self.assertEqual(result["type"], "short_activity")
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO drift_events (id,user_id,detected_at,level,affected_signals) "
                               "VALUES ('OTHER-DRIFT','OTHER','2082-01-01T00:00:00Z','low','[\"fatigue\"]')")
        self.assertIsNone(recommend_intervention(self.path, "OTHER")["memory_id"])


if __name__ == "__main__":
    unittest.main()
