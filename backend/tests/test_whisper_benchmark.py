import io
from pathlib import Path
import unittest
from unittest.mock import patch

from backend.scripts import benchmark_whisper as benchmark


class BenchmarkTests(unittest.TestCase):
    def test_candidates_match_machine_capacity(self):
        for cpus, expected in ((None, []), (1, []), (2, [2]), (4, [2, 4]), (6, [2, 4, 6]), (8, [2, 4, 6, 8])):
            with self.subTest(cpus=cpus):
                self.assertEqual(benchmark.candidates(cpus), expected)

    def test_same_wav_model_and_decoding_three_runs_per_configuration(self):
        with patch.object(benchmark, 'run') as run, \
             patch.object(Path, 'read_text', return_value=' Bonjour.\n'), \
             patch('sys.stdout', new_callable=io.StringIO) as output:
            results = benchmark.benchmark(Path('same.wav'), Path('temporary'), [2, 4, 6, 8], 'whisper-cli', 'ggml-base.bin')
        self.assertEqual(run.call_count, 12)
        for threads, runs in results.items():
            self.assertEqual(len(runs), 3)
            self.assertTrue(all(text == 'Bonjour.' and ms >= 0 for ms, text in runs))
            self.assertIn(f'{threads} threads — moyenne', output.getvalue())
        for call in run.call_args_list:
            args = call.args[0]
            self.assertEqual(args[:8], ['whisper-cli', '-m', 'ggml-base.bin', '-f', 'same.wav', '-l', 'fr', '-nt'])
            self.assertEqual(args[8:11], ['-np', '-otxt', '-of'])
            self.assertEqual(args[-2], '-t')
        self.assertIn('Configuration inchangée', output.getvalue())
