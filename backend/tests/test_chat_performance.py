from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend.app.config import load_local_ollama_config
from backend.app.main import create_app
from backend.app.services.chat_performance import ChatPerformance, current_performance
from backend.app.services.ollama_client import generate_reply, OllamaUnavailable
from backend.scripts.benchmark_chat import run_benchmark, MESSAGE

METRICS = dict(load_duration=2_000_000_000, prompt_eval_count=200,
               prompt_eval_duration=3_000_000_000, eval_count=50,
               eval_duration=5_000_000_000, total_duration=10_000_000_000)


class MetricTests(unittest.TestCase):
    def test_units_and_rates_without_invented_first_token(self):
        performance = ChatPerformance()
        performance.collect_ollama(METRICS)
        self.assertEqual(performance.metrics['ollama_load_ms'], 2000)
        self.assertEqual(performance.metrics['ollama_prompt_eval_ms'], 3000)
        self.assertEqual(performance.metrics['ollama_eval_ms'], 5000)
        self.assertEqual(performance.metrics['ollama_total_ms'], 10000)
        self.assertEqual(performance.metrics['prompt_tokens'], 200)
        self.assertEqual(performance.metrics['generated_tokens'], 50)
        self.assertEqual(performance.metrics['tokens_per_second'], 10)
        self.assertIsNone(performance.metrics['first_token_ms'])
        self.assertIsNone(performance.metrics['generation_ms'])

    def test_absent_invalid_and_zero_metrics_never_break_response(self):
        for value in (None, 'privé', True, -1, float('nan'), float('inf'), {}, 2**80):
            with self.subTest(value=value):
                performance = ChatPerformance()
                performance.collect_ollama({key: value for key in METRICS})
                self.assertTrue(all(performance.metrics[key] is None for key in METRICS))
                self.assertIsNone(performance.metrics['tokens_per_second'])
        performance = ChatPerformance()
        performance.collect_ollama(dict(eval_count=0, eval_duration=0))
        self.assertEqual(performance.metrics['generated_tokens'], 0)
        self.assertIsNone(performance.metrics['tokens_per_second'])

    def test_timer_finally_and_context_isolation(self):
        with patch('backend.app.services.chat_performance.time.perf_counter', side_effect=[1, 2, 2.25, 3]):
            performance = ChatPerformance()
            with self.assertRaises(ValueError), performance.active(), performance.measure('persist_ms'):
                self.assertIs(current_performance.get(), performance)
                raise ValueError('privé')
            self.assertIsNone(current_performance.get())
            with self.assertLogs('uvicorn.error.chat') as logs:
                result = performance.finish()
        self.assertEqual(result['persist_ms'], 250)
        self.assertEqual(result['total_ms'], 2000)
        self.assertNotIn('privé', logs.output[0])
        self.assertIsNone(ChatPerformance().metrics['eval_count'])

    def test_real_client_collects_only_metrics_without_changing_payload(self):
        calls = []
        def handle(request):
            calls.append(request)
            if request.url.path == '/api/show':
                return httpx.Response(200, json={'model_info': {'architecture': 'local'}})
            return httpx.Response(200, json={'done': True, 'message': {'role': 'assistant', 'content': 'Réponse privée'}, **METRICS})
        original = httpx.Client
        performance = ChatPerformance()
        with patch.dict(os.environ, OLLAMA_URL='http://127.0.0.1:11434', OLLAMA_MODEL='local'), \
             patch('backend.app.services.ollama_client.httpx.Client', side_effect=lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs)), \
             performance.active():
            self.assertEqual(generate_reply([{'role': 'user', 'content': 'Question privée'}]), 'Réponse privée')
        self.assertEqual(performance.metrics['eval_count'], 50)
        payload = json.loads(calls[-1].content)
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['messages'], [{'role': 'user', 'content': 'Question privée'}])
        with self.assertLogs('uvicorn.error.chat') as logs:
            performance.finish()
        self.assertNotIn('privée', logs.output[0])


class ChatPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.dict(os.environ, CHAT_PERF_DEBUG='false'))
        self.path = self.root / 'test.db'
        self.client = self.enterContext(TestClient(create_app(self.path)))
        self.prompts = []
        def generate(messages):
            self.prompts.append(messages)
            current_performance.get().collect_ollama(METRICS)
            return 'Réponse strictement privée.'
        self.generate = self.enterContext(patch('backend.app.routes.chat.generate_reply', side_effect=generate))

    def post(self):
        return self.client.post('/api/chat', json={'user_id': 'ASTRO-001', 'message': MESSAGE})

    def test_normal_contract_and_private_logs(self):
        with self.assertLogs('uvicorn.error.chat') as logs:
            response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {'user_id', 'role', 'content', 'timestamp'})
        self.assertEqual(len(logs.output), 1)
        self.assertIn('[CHAT PERF]', logs.output[0])
        for message in self.prompts[0]:
            self.assertNotIn(message['content'], logs.output[0])
        self.assertNotIn('Réponse strictement privée', logs.output[0])
        history = self.client.get('/api/chat/ASTRO-001').json()
        self.assertEqual(len(history), 2)
        self.assertTrue(all('performance' not in message for message in history))

    def test_debug_adds_metrics_with_all_stages_and_prompt_length(self):
        with patch.dict(os.environ, CHAT_PERF_DEBUG='true'):
            response = self.post()
        self.assertEqual(response.status_code, 200)
        performance = response.json()['performance']
        for name in ('context_ms', 'prompt_ms', 'ollama_ms', 'persist_ms', 'total_ms'):
            self.assertGreaterEqual(performance[name], 0)
        self.assertEqual(performance['prompt_chars'], sum(len(item['content']) for item in self.prompts[0]))
        self.assertEqual(performance['prompt_tokens'], 200)
        self.assertEqual(performance['tokens_per_second'], 10)
        self.assertIsNone(performance['first_token_ms'])
        self.assertIsNone(performance['generation_ms'])

    def test_failure_keeps_error_contract_and_no_messages(self):
        self.generate.side_effect = OllamaUnavailable('Moteur indisponible')
        with patch.dict(os.environ, CHAT_PERF_DEBUG='true'), self.assertLogs('uvicorn.error.chat') as logs:
            response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(set(response.json()), {'success', 'error'})
        self.assertEqual(self.client.get('/api/chat/ASTRO-001').json(), [])
        self.assertIn('persist_ms=0.0', logs.output[0])
        self.assertIsNone(current_performance.get())

    def test_unknown_user_is_still_404(self):
        response = self.client.post('/api/chat', json={'user_id': 'UNKNOWN', 'message': MESSAGE})
        self.assertEqual(response.status_code, 404)
        self.generate.assert_not_called()

    def test_validation_error_is_timed_without_logging_input(self):
        with self.assertLogs('uvicorn.error.chat') as logs:
            response = self.client.post('/api/chat', json={'user_id': 'ASTRO-001', 'message': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('total_ms=', logs.output[0])
        self.assertIn('ollama_ms=0.0', logs.output[0])
        self.generate.assert_not_called()

    def test_benchmark_identical_prompts_three_calls_no_primary_writes(self):
        self.post()  # Existing history must be preserved, not dropped for the benchmark.
        self.prompts.clear()
        before = self.client.get('/api/chat/ASTRO-001').json()
        with redirect_stdout(io.StringIO()) as output:
            results = run_benchmark(self.path)
        self.assertEqual(len(results), 3)
        self.assertEqual(len(self.prompts), 3)
        self.assertEqual(self.prompts[0], self.prompts[1])
        self.assertEqual(self.prompts[1], self.prompts[2])
        self.assertEqual(before, self.client.get('/api/chat/ASTRO-001').json())
        self.assertEqual(os.environ['CHAT_PERF_DEBUG'], 'false')
        self.assertNotIn(MESSAGE, output.getvalue())
        self.assertNotIn('Réponse strictement privée', output.getvalue())

    def test_debug_configuration_load_and_precedence(self):
        (self.root / '.env.local').write_text('CHAT_PERF_DEBUG=true\n', encoding='utf-8')
        with patch('backend.app.config.PROJECT_ROOT', self.root), patch.dict(os.environ):
            os.environ.pop('CHAT_PERF_DEBUG', None)
            load_local_ollama_config()
            self.assertEqual(os.environ['CHAT_PERF_DEBUG'], 'true')
            os.environ['CHAT_PERF_DEBUG'] = 'false'
            load_local_ollama_config()
            self.assertEqual(os.environ['CHAT_PERF_DEBUG'], 'false')
