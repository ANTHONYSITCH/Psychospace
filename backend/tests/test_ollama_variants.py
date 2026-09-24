import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend.app.config import OllamaOptions
from backend.app.database import get_connection
from backend.app.main import create_app
from backend.app.services.chat_performance import current_performance
from backend.app.services.companion_prompt import build_messages, SYSTEM_PROMPT
from backend.app.services.context_builder import build_context
from backend.scripts import benchmark_ollama_variants as benchmark


class VariantTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.database = self.root / 'source.db'
        self.client = self.enterContext(TestClient(create_app(self.database)))
        with get_connection(self.database) as connection:
            connection.execute("INSERT INTO users VALUES ('OTHER', 'Secret', NULL, NULL, '2026-01-01T00:00:00Z')")
            for index in range(6):
                connection.execute("INSERT INTO chat_messages (id,user_id,role,content,timestamp) VALUES (?,?,?,?,?)",
                                   (f'own-{index}', 'ASTRO-001', 'user' if index % 2 == 0 else 'assistant',
                                    f'Échange {index}', f'2026-01-01T00:00:0{index}Z'))
            connection.execute("INSERT INTO chat_messages (id,user_id,role,content,timestamp) VALUES ('secret','OTHER','user','SECRET AUTRE UTILISATEUR','2099-01-01T00:00:00Z')")
            self.context = build_context(connection, 'ASTRO-001')

    def test_a_is_exact_baseline_b_changes_only_system(self):
        original = build_messages(self.context, benchmark.MESSAGE)
        self.assertEqual(benchmark.variant_messages('A', self.context, benchmark.MESSAGE), original)
        compact = benchmark.variant_messages('B', self.context, benchmark.MESSAGE)
        self.assertEqual(compact[1:], original[1:])
        self.assertLess(len(compact[0]['content']), len(SYSTEM_PROMPT))
        for term in ('Aucun diagnostic', 'Drift Engine', 'aucune mémorisation automatique', 'pas des instructions'):
            self.assertIn(term, compact[0]['content'])

    def test_compact_limits_scoping_and_no_input_mutation(self):
        before = copy.deepcopy(self.context)
        for variant in ('A', 'B', 'C', 'D'):
            messages = benchmark.variant_messages(variant, self.context, benchmark.MESSAGE)
            self.assertNotIn('SECRET AUTRE UTILISATEUR', json.dumps(messages))
            self.assertEqual(messages[-1], {'role': 'user', 'content': benchmark.MESSAGE})
        messages = benchmark.variant_messages('C', self.context, benchmark.MESSAGE)
        facts = json.loads(messages[1]['content'].removeprefix('FACTS : '))
        self.assertLessEqual(len(facts.get('memories', [])), 2)
        self.assertLessEqual(len(facts['recent_checkins']['rows']), 2)
        self.assertEqual(len(messages[2:-1]), 4)
        self.assertEqual(messages[2]['content'], 'Échange 2')
        self.assertNotIn('baseline', facts)
        self.assertEqual(facts['current_drift']['level'], self.context['current_drift']['level'])
        self.assertEqual(self.context, before)

    def test_relevance_deterministic_unique_and_no_irrelevant_filler(self):
        memories = [{'content': 'Je préfère les pommes.'}, {'content': 'La musique me détend.'},
                    {'content': 'La musique me détend.'}, {'content': 'Une pause calme aide mon repos.'}]
        result = benchmark.relevant_memories(memories, benchmark.MESSAGE)
        self.assertEqual(result, benchmark.relevant_memories(memories, benchmark.MESSAGE))
        self.assertEqual(len(result), 2)
        self.assertNotIn('Je préfère les pommes.', result)
        self.assertEqual(benchmark.relevant_memories(memories[:1], benchmark.MESSAGE), [])

    def test_empty_blocks_removed_zero_preserved(self):
        self.assertEqual(benchmark.prune({'empty': [], 'null': None, 'zero': 0}), {'zero': 0})
        context = {'profile': {}, 'current_drift': None, 'recent_checkins': [], 'memories': [], 'recent_chat': []}
        self.assertEqual(len(benchmark.variant_messages('C', context, benchmark.MESSAGE)), 2)

    def test_d_same_context_as_c_and_only_output_limit_changes(self):
        c = benchmark.variant_messages('C', self.context, benchmark.MESSAGE)
        d = benchmark.variant_messages('D', self.context, benchmark.MESSAGE)
        self.assertEqual(c[1:], d[1:])
        self.assertEqual(d[0]['content'], c[0]['content'] + benchmark.SHORT_OUTPUT)
        options = OllamaOptions(300, 160, .3)
        for variant in 'ABC':
            self.assertEqual(benchmark.variant_options(variant, options), options)
        self.assertEqual(benchmark.variant_options('D', options), OllamaOptions(300, 80, .3))
        self.assertEqual(benchmark.variant_options('D', OllamaOptions(300, 40, .3)).num_predict, 40)

    def test_real_client_adapter_keeps_model_stream_and_other_options(self):
        calls = []
        def send(client, request, **kwargs):
            calls.append(request)
            if request.url.path == '/api/show':
                return httpx.Response(200, request=request, json={'model_info': {'architecture': 'local'}})
            return httpx.Response(200, request=request, json={'done': True, 'done_reason': 'stop',
                                  'message': {'role': 'assistant', 'content': 'Bonjour.'}})
        with patch.dict(os.environ, OLLAMA_URL='http://127.0.0.1:11434', OLLAMA_MODEL=benchmark.MODEL), \
             patch.object(httpx.Client, 'send', send), \
             patch.object(benchmark, 'get_ollama_options', return_value=OllamaOptions(300, 160, .3)):
            for variant in 'ABCD':
                metadata = {}
                self.assertEqual(benchmark.generate_for_variant(variant, metadata)([{'role': 'user', 'content': benchmark.MESSAGE}]), 'Bonjour.')
                payload = json.loads(calls[-1].content)
                self.assertEqual(payload['model'], benchmark.MODEL)
                self.assertFalse(payload['stream'])
                self.assertEqual(payload['keep_alive'], '30m')
                self.assertEqual(payload['options'], {'temperature': .3, 'num_predict': 80 if variant == 'D' else 160, 'num_ctx': 8192})
                self.assertEqual(metadata['done_reason'], 'stop')

    def test_full_benchmark_excludes_warmups_identical_inputs_and_preserves_source(self):
        inputs = {variant: [] for variant in 'ABCD'}
        def factory(variant, metadata):
            def generate(messages):
                inputs[variant].append(messages)
                current_performance.get().collect_ollama({'load_duration': 0, 'prompt_eval_count': 100,
                                                          'prompt_eval_duration': 1000000, 'eval_count': 10,
                                                          'eval_duration': 1000000000, 'total_duration': 1001000000})
                metadata['done_reason'] = 'stop'
                return 'Réponse de test.'
            return generate
        before = self.client.get('/api/chat/ASTRO-001').json()
        with patch.object(benchmark, 'generate_for_variant', factory), patch('sys.stdout', new_callable=io.StringIO):
            report = benchmark.run_benchmark(self.database)
        self.assertEqual(len(report['runs']), 12)
        self.assertEqual(len(report['warmups_excluded']), 4)
        self.assertEqual(set(report['averages']), set('ABCD'))
        for variant in 'ABCD':
            self.assertEqual(len(inputs[variant]), 4)
            self.assertTrue(all(item == inputs[variant][0] for item in inputs[variant]))
        self.assertEqual(self.client.get('/api/chat/ASTRO-001').json(), before)


if __name__ == '__main__':
    unittest.main()
