import json
import os
import sqlite3
from contextlib import contextmanager, closing
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend.app.database import get_connection
from backend.app.config import load_local_ollama_config, get_ollama_options
from backend.app.main import create_app
from backend.app.services.context_builder import build_context
from backend.app.services.companion_prompt import SYSTEM_PROMPT
from backend.app.services.ollama_client import OllamaUnavailable, generate_reply


class ChatTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(directory) / "chat.db"
        self.client = self.enterContext(TestClient(create_app(self.path)))
        self.fake = self.enterContext(patch("backend.app.routes.chat.generate_reply", return_value="On peut prendre un moment calme."))

    def post(self, **changes):
        return self.client.post("/api/chat", json={"user_id": "ASTRO-001", "message": "Je suis fatigué.", **changes})

    def context(self, user="ASTRO-001"):
        with get_connection(self.path) as connection:
            return build_context(connection, user)

    def test_profile(self):
        self.assertEqual(self.context()["profile"]["first_name"], "Alex")

    def test_baseline(self):
        self.assertIsNotNone(self.context()["baseline"]["sleep_hours_avg"])

    def test_latest_drift_unchanged(self):
        with get_connection(self.path) as connection:
            row = dict(connection.execute("SELECT * FROM drift_events ORDER BY detected_at DESC LIMIT 1").fetchone())
        for key in ("level", "drift_score", "explanation"):
            self.assertEqual(self.context()["current_drift"][key], row[key])
        self.assertEqual(self.context()["current_drift"]["affected_signals"], json.loads(row["affected_signals"]))

    def test_memories_and_checkins(self):
        self.assertEqual(len(self.context()["memories"]), 6)
        self.assertEqual(len(self.context()["recent_checkins"]), 3)

    def test_history_limited(self):
        for index in range(7):
            self.post(message=str(index))
        history = self.client.get("/api/chat/ASTRO-001").json()
        self.assertEqual(self.context()["recent_chat"], [{k: row[k] for k in ("role", "content")} for row in history[-6:]])

    def test_connection_closed_during_generation_and_new_connection_for_writes(self):
        connections = []
        @contextmanager
        def tracked(path):
            with get_connection(path) as connection:
                connections.append(connection)
                yield connection
        def generate(messages):
            self.assertEqual(len(connections), 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                connections[0].execute("SELECT 1")
            with closing(sqlite3.connect(self.path, timeout=0)) as independent:
                with independent:
                    independent.execute("BEGIN IMMEDIATE")
                    self.assertEqual(independent.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0], 0)
                    independent.execute("UPDATE users SET first_name=first_name")
            return "Un moment calme peut aider."
        self.fake.side_effect = generate
        with patch("backend.app.routes.chat.get_connection", tracked):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(len(connections), 2)
        self.assertIsNot(connections[0], connections[1])
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def test_insert_failure_rolls_back_both_messages(self):
        self.post()
        before = self.client.get("/api/chat/ASTRO-001").json()
        for role in ("user", "assistant"):
            with get_connection(self.path) as connection:
                connection.execute("DROP TRIGGER IF EXISTS fail_chat")
                connection.execute(f"CREATE TRIGGER fail_chat BEFORE INSERT ON chat_messages "
                                   f"WHEN NEW.role = '{role}' BEGIN SELECT RAISE(ABORT, 'test failure'); END")
            with self.assertLogs("backend.app.main", level="ERROR"), self.assertRaises(sqlite3.IntegrityError):
                self.post()
            self.assertEqual(self.client.get("/api/chat/ASTRO-001").json(), before)

    def test_latest_drift_uses_dates_then_id_not_insertion_order(self):
        with get_connection(self.path) as connection:
            for identifier, date in (("Z-NEW", "2081-01-01T00:00:00.1Z"),
                                     ("A-TIE", "2081-01-01T00:00:00.100Z"),
                                     ("Z-OLDER", "2081-01-01T00:00:00Z"),
                                     ("LAST-INSERTED", "2080-06-01T00:00:00Z")):
                connection.execute("INSERT INTO drift_events (id,user_id,detected_at,level,drift_score,affected_signals,explanation) "
                                   "VALUES (?, 'ASTRO-001', ?, 'high', 0.9, '[]', 'Stored explanation')", (identifier, date))
        with patch("pathlib.Path.read_text", side_effect=AssertionError("No seeds")):
            drift = self.context()["current_drift"]
        self.assertEqual(drift["id"], "Z-NEW")
        self.assertEqual(drift["level"], "high")
        self.assertEqual(drift["drift_score"], 0.9)

    def test_compact_payload_omits_metadata_and_preserves_main_signals(self):
        self.post()
        payload = self.fake.call_args.args[0][1]["content"].split("\n", 1)[1]
        facts = json.loads(payload)
        for key in ('"id"', '"timestamp"', '"detected_at"', '"category"', '"observation_days"'):
            self.assertNotIn(key, payload)
        self.assertEqual(len(facts["recent_checkins"]["rows"]), 3)
        self.assertEqual(facts["current_drift"]["drift_score"], self.context()["current_drift"]["drift_score"])
        self.assertEqual(facts["memories"], [m["content"] for m in self.context()["memories"]])

    def test_post_persists_both_messages_and_get_contract(self):
        result = self.post()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(set(result.json()), {"user_id", "role", "content", "timestamp"})
        history = self.client.get("/api/chat/ASTRO-001").json()
        self.assertEqual([row["role"] for row in history], ["user", "assistant"])
        self.assertEqual(history[0]["content"], "Je suis fatigué.")
        self.assertEqual(history[1]["content"], result.json()["content"])
        with TestClient(create_app(self.path)) as restarted:
            self.assertEqual(restarted.get("/api/chat/ASTRO-001").json(), history)

    def test_invalid_messages(self):
        for message in ("", " \n", None, 42):
            self.assertEqual(self.post(message=message).status_code, 400)
        self.fake.assert_not_called()

    def test_unknown_user(self):
        self.assertEqual(self.post(user_id="UNKNOWN").status_code, 404)
        self.assertEqual(self.client.get("/api/chat/UNKNOWN").status_code, 404)
        self.fake.assert_not_called()

    def test_unavailable_rolls_back_only_failed_exchange(self):
        self.post()
        before = self.client.get("/api/chat/ASTRO-001").json()
        self.fake.side_effect = OllamaUnavailable("Indisponible")
        self.assertEqual(self.post().status_code, 503)
        self.assertEqual(self.client.get("/api/chat/ASTRO-001").json(), before)

    def test_no_automatic_memories(self):
        before = self.client.get("/api/memories/ASTRO-001").json()
        self.post(message="Retiens que j'aime le piano.")
        self.assertEqual(self.client.get("/api/memories/ASTRO-001").json(), before)

    def test_prompt_rules_and_current_message_once(self):
        self.post()
        messages = self.fake.call_args.args[0]
        self.assertIn("Ne pose jamais de diagnostic", SYSTEM_PROMPT)
        for term in ("FACTS", "INFERENCES", "Drift Engine", "N'invente", "famille"):
            self.assertIn(term, SYSTEM_PROMPT)
        self.assertEqual(sum(item["content"] == "Je suis fatigué." for item in messages), 1)

    def test_no_file_reads_during_requests(self):
        with patch("pathlib.Path.read_text", side_effect=AssertionError("No seed reads")), patch("builtins.open", side_effect=AssertionError("No files")):
            self.assertEqual(self.post().status_code, 200)
            self.assertEqual(self.client.get("/api/chat/ASTRO-001").status_code, 200)

    def test_empty_context_and_user_isolation(self):
        with get_connection(self.path) as connection:
            connection.execute("INSERT INTO users VALUES ('OTHER', 'Sam', NULL, NULL, '2026-01-01T00:00:00Z')")
        self.post()
        context = self.context("OTHER")
        self.assertIsNone(context["baseline"])
        self.assertIsNone(context["current_drift"])
        for key in ("memories", "recent_chat", "recent_checkins"):
            self.assertEqual(context[key], [])
        self.assertEqual(self.client.get("/api/chat/OTHER").json(), [])

    def test_deleted_memory_absent_from_next_prompt(self):
        with get_connection(self.path) as connection:
            connection.execute("DELETE FROM memories WHERE user_id = 'ASTRO-001'")
        self.post()
        self.assertEqual(json.loads(self.fake.call_args.args[0][1]["content"].split("\n", 1)[1])["memories"], [])


class OllamaClientTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"OLLAMA_URL": "http://localhost:11434", "OLLAMA_MODEL": "test-local"}))

    def run_mock(self, chat_response=None, show_response=None, error=None):
        calls = []
        def handle(request):
            calls.append(request)
            if error:
                raise error
            if request.url.path == "/api/show":
                return show_response or httpx.Response(200, json={"model_info": {"architecture": "test"}})
            return chat_response or httpx.Response(200, json={"done": True, "message": {"role": "assistant", "content": "Bonjour."}})
        real_client = httpx.Client
        with patch("backend.app.services.ollama_client.httpx.Client", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs)):
            result = generate_reply([{"role": "user", "content": "Bonjour"}])
        return result, calls

    def test_local_payload(self):
        result, calls = self.run_mock()
        self.assertEqual(result, "Bonjour.")
        payload = json.loads(calls[-1].content)
        self.assertEqual(payload["model"], "test-local")
        self.assertFalse(payload["stream"])
        self.assertEqual(calls[-1].url.host, "localhost")

    def test_configurable_options_and_private_logging(self):
        with patch.dict(os.environ, {"OLLAMA_TIMEOUT_SECONDS": "123", "OLLAMA_NUM_PREDICT": "99", "OLLAMA_TEMPERATURE": "0.2"}), \
                patch("backend.app.services.ollama_client.perf_counter", side_effect=[10, 12.345]), \
                self.assertLogs("backend.app.services.ollama_client", level="INFO") as logs:
            _, calls = self.run_mock()
        payload = json.loads(calls[-1].content)
        self.assertEqual(payload["options"]["num_predict"], 99)
        self.assertEqual(payload["options"]["temperature"], 0.2)
        self.assertEqual(calls[-1].extensions["timeout"]["read"], 123)
        self.assertEqual(len(logs.output), 1)
        self.assertTrue(logs.output[0].endswith("Ollama generation completed in 2.35 seconds"))

    def test_network_and_timeout(self):
        for error in (httpx.ConnectError("offline"), httpx.ReadTimeout("timeout")):
            with self.assertRaises(OllamaUnavailable):
                self.run_mock(error=error)

    def test_missing_model_and_remote_model(self):
        for response in (httpx.Response(404), httpx.Response(200, json={"remote_host": "cloud", "model_info": {"a": 1}})):
            with self.assertRaises(OllamaUnavailable):
                self.run_mock(show_response=response)

    def test_invalid_responses(self):
        for response in (httpx.Response(200, text="broken"), httpx.Response(500), httpx.Response(302, headers={"Location": "https://example.com"}),
                         *[httpx.Response(200, json=item) for item in ([], {}, {"message": None}, {"done": True, "message": {"role": "assistant", "content": " "}})]):
            with self.assertRaises(OllamaUnavailable):
                self.run_mock(chat_response=response)

    def test_external_urls_and_cloud_names_refused(self):
        for setting in ({"OLLAMA_URL": "https://example.com"}, {"OLLAMA_URL": "http://localhost@evil.com"},
                        {"OLLAMA_MODEL": "test-cloud"}, {"OLLAMA_MODEL": ""}):
            with patch.dict(os.environ, setting), patch("backend.app.services.ollama_client.httpx.Client") as client:
                with self.assertRaises(OllamaUnavailable):
                    generate_reply([])
                client.assert_not_called()


class LocalConfigTests(unittest.TestCase):
    def test_defaults_and_invalid_options(self):
        with patch.dict(os.environ, {}, clear=True):
            options = get_ollama_options()
            self.assertEqual((options.timeout_seconds, options.num_predict, options.temperature), (60, 160, 0.3))
            for key, value in (("OLLAMA_TIMEOUT_SECONDS", "nan"), ("OLLAMA_NUM_PREDICT", "-1"),
                               ("OLLAMA_TEMPERATURE", "inf"), ("OLLAMA_TIMEOUT_SECONDS", "zero")):
                with patch.dict(os.environ, {key: value}), self.assertRaises(ValueError):
                    get_ollama_options()

    def test_loads_only_ollama_keys_and_preserves_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.local").write_text('OLLAMA_URL=http://localhost:11434\nOLLAMA_MODEL="local-test"\nUNRELATED=ignored\n', encoding="utf-8")
            with patch("backend.app.config.PROJECT_ROOT", root), patch.dict(os.environ, {"OLLAMA_URL": "http://127.0.0.1:11434"}, clear=True):
                load_local_ollama_config()
                self.assertEqual(os.environ["OLLAMA_MODEL"], "local-test")
                self.assertEqual(os.environ["OLLAMA_URL"], "http://127.0.0.1:11434")
                self.assertNotIn("UNRELATED", os.environ)

    def test_missing_local_file_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("backend.app.config.PROJECT_ROOT", Path(directory)), patch.dict(os.environ, {}, clear=True):
                load_local_ollama_config()
                self.assertNotIn("OLLAMA_MODEL", os.environ)


if __name__ == "__main__":
    unittest.main()
