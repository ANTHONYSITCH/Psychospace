import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.config import SEEDS_PATH
from backend.app.database import get_connection
from backend.app.main import create_app


MEMORY = {
    "id": "MEM-DEMO-001", "user_id": "ASTRO-001", "category": "coping_strategy",
    "content": "Listening to music helps Alex decompress after stressful situations.",
    "importance": 4, "source": "user", "created_at": "2080-04-16T18:00:00Z",
}


class MemoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "memories.db"
        self.client = self.enterContext(TestClient(create_app(self.path)))

    def test_get_matches_seed_memories_without_reading_files(self):
        expected = json.loads((SEEDS_PATH / "astro-001-memories.json").read_text(encoding="utf-8"))
        with patch("pathlib.Path.read_text", side_effect=AssertionError("No files for requests")):
            response = self.client.get("/api/memories/ASTRO-001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_unknown_user_get_and_post(self):
        for user_id in ("UNKNOWN", "' OR 1=1 --"):
            self.assertEqual(self.client.get(f"/api/memories/{user_id}").status_code, 404)
            response = self.client.post("/api/memories", json={**MEMORY, "user_id": user_id})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "not_found")

    def test_create_and_verify_sqlite(self):
        response = self.client.post("/api/memories", json=MEMORY)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), MEMORY)
        with get_connection(self.path) as connection:
            row = connection.execute("SELECT * FROM memories WHERE id = ?", (MEMORY["id"],)).fetchone()
        self.assertEqual(dict(row), MEMORY)

    def test_duplicate_id_rejected_without_overwriting(self):
        self.client.post("/api/memories", json=MEMORY)
        response = self.client.post("/api/memories", json={**MEMORY, "content": "Different"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/memories/ASTRO-001").json()[-1], MEMORY)

    def test_empty_fields_invalid_importance_and_timestamp(self):
        cases = [(field, " ") for field in ("id", "user_id", "category", "content", "source")]
        cases += [("importance", value) for value in (0, 11, 2.5, True, "4")]
        cases += [("created_at", value) for value in ("invalid", "2080-02-30T18:00:00Z", "2080-04-16T18:00:00")]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                response = self.client.post("/api/memories", json={**MEMORY, field: value})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "invalid_data")
        self.assertEqual(len(self.client.get("/api/memories/ASTRO-001").json()), 6)

    def test_missing_and_extra_fields_rejected(self):
        for payload in ({k: v for k, v in MEMORY.items() if k != "source"}, {**MEMORY, "extra": 1}):
            self.assertEqual(self.client.post("/api/memories", json=payload).status_code, 400)

    def test_update_allowed_fields_and_sqlite(self):
        self.client.post("/api/memories", json=MEMORY)
        corrected = {**MEMORY, "category": "custom_category", "content": "Alex prefers quiet instrumental music.",
                     "importance": 7, "source": "user_correction"}
        response = self.client.put("/api/memories/MEM-DEMO-001", json=corrected)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), corrected)
        with get_connection(self.path) as connection:
            self.assertEqual(dict(connection.execute("SELECT * FROM memories WHERE id = ?", (MEMORY["id"],)).fetchone()), corrected)

    def test_immutable_fields_and_incomplete_put_rejected(self):
        self.client.post("/api/memories", json=MEMORY)
        for field, value in (("id", "OTHER"), ("user_id", "ASTRO-002"), ("created_at", "2080-04-17T18:00:00Z")):
            response = self.client.put("/api/memories/MEM-DEMO-001", json={**MEMORY, field: value})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.put("/api/memories/MEM-DEMO-001", json={"content": "Correction"}).status_code, 400)
        self.assertEqual(self.client.get("/api/memories/ASTRO-001").json()[-1], MEMORY)

    def test_unknown_memory_put_delete_and_injection(self):
        for identifier in ("UNKNOWN", "' OR 1=1 --"):
            self.assertEqual(self.client.put(f"/api/memories/{identifier}", json=MEMORY).status_code, 404)
            self.assertEqual(self.client.delete(f"/api/memories/{identifier}").status_code, 404)
        self.assertEqual(len(self.client.get("/api/memories/ASTRO-001").json()), 6)

    def test_delete_persists_across_restart_without_seed_restore(self):
        response = self.client.delete("/api/memories/MEM-001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        with get_connection(self.path) as connection:
            self.assertIsNone(connection.execute("SELECT id FROM memories WHERE id = ?", ("MEM-001",)).fetchone())
        with TestClient(create_app(self.path)) as restarted:
            rows = restarted.get("/api/memories/ASTRO-001").json()
            self.assertEqual(len(rows), 5)
            self.assertNotIn("MEM-001", [row["id"] for row in rows])

    def test_users_are_isolated_and_empty_history(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users (user_id, first_name, created_at) VALUES (?, ?, ?)",
                               ("ASTRO-002", "Sam", "2080-04-01T00:00:00Z"))
        response = self.client.get("/api/memories/ASTRO-002")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        other = {**MEMORY, "id": "MEM-OTHER", "user_id": "ASTRO-002"}
        self.client.post("/api/memories", json=other)
        self.client.post("/api/memories", json=MEMORY)
        self.client.put("/api/memories/MEM-DEMO-001", json={**MEMORY, "content": "Correction"})
        self.client.delete("/api/memories/MEM-DEMO-001")
        self.assertEqual(self.client.get("/api/memories/ASTRO-002").json(), [other])
        self.assertNotIn("MEM-OTHER", [row["id"] for row in self.client.get("/api/memories/ASTRO-001").json()])

    def test_ordering_and_common_dataset_unchanged(self):
        before = {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in SEEDS_PATH.iterdir() if file.is_file()}
        for identifier, timestamp in (("Z", "2080-04-16T18:00:00.1Z"), ("B", "2080-04-16T18:00:00Z"),
                                      ("A", "2080-04-16T18:00:00Z")):
            self.client.post("/api/memories", json={**MEMORY, "id": identifier, "created_at": timestamp})
        self.assertEqual([row["id"] for row in self.client.get("/api/memories/ASTRO-001").json()][-3:], ["A", "B", "Z"])
        self.client.delete("/api/memories/MEM-001")
        after = {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in SEEDS_PATH.iterdir() if file.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
