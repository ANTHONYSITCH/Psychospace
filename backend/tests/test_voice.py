"""Voice endpoint: mocked native tools, real temporary files and HTTP requests."""
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.services import whisper_service as service
from backend.app.config import load_local_ollama_config
from starlette.requests import Request


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.client = self.enterContext(TestClient(create_app(self.root / 'test.db')))
        self.settings = {}
        for key in ('FFMPEG_PATH', 'WHISPER_CLI_PATH', 'WHISPER_MODEL_PATH'):
            path = self.root / key
            path.touch()
            self.settings[key] = str(path)
        self.settings.update(WHISPER_LANGUAGE='fr', WHISPER_TIMEOUT_SECONDS='30', WHISPER_MAX_AUDIO_BYTES='10485760', WHISPER_PERF_DEBUG='false', WHISPER_THREADS='')
        self.enterContext(patch.dict(os.environ, self.settings))
        self.directories = []
        self.text = 'Ça va, je suis juste fatigué.'
        self.run = self.enterContext(patch.object(service.subprocess, 'run', side_effect=self.native))

    def native(self, args, **kwargs):
        source = Path(args[args.index('-i') + 1] if '-i' in args else args[args.index('-f') + 1])
        self.directories.append(source.parent)
        self.assertTrue(source.is_file())
        # Reopening for writing verifies the producer has closed its file handle.
        with source.open('ab'):
            pass
        if '-i' in args:
            Path(args[-1]).write_bytes(b'fake wav')
        else:
            Path(args[args.index('-of') + 1] + '.txt').write_text(self.text, encoding='utf-8')
        return subprocess.CompletedProcess(args, 0, b'diagnostics must not appear', b'private path')

    def post(self, data=b'audio', mime='audio/webm;codecs=opus'):
        return self.client.post('/api/voice/transcribe', content=data, headers={'Content-Type': mime})

    def assert_clean(self):
        self.assertTrue(self.directories)
        self.assertTrue(all(not path.exists() for path in self.directories))

    def test_success_commands_and_cleanup(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(set(result), {'text', 'language', 'processing_ms'})
        self.assertEqual(result['text'], self.text)
        self.assertEqual(result['language'], 'fr')
        self.assertGreaterEqual(result['processing_ms'], 0)
        ffmpeg, whisper = [call.args[0] for call in self.run.call_args_list]
        self.assertEqual(ffmpeg[0], self.settings['FFMPEG_PATH'])
        for flag, value in [('-ar', '16000'), ('-ac', '1'), ('-c:a', 'pcm_s16le'), ('-protocol_whitelist', 'file,pipe'), ('-t', '30')]:
            self.assertEqual(ffmpeg[ffmpeg.index(flag) + 1], value)
        self.assertEqual(whisper[0], self.settings['WHISPER_CLI_PATH'])
        self.assertEqual(whisper[whisper.index('-m') + 1], self.settings['WHISPER_MODEL_PATH'])
        self.assertEqual(whisper[whisper.index('-l') + 1], 'fr')
        for flag in ['-nt', '-np']:
            self.assertIn(flag, whisper)
        self.assertNotIn('--translate', whisper)
        self.assertNotIn('-tr', whisper)
        for call in self.run.call_args_list:
            self.assertIs(call.kwargs['shell'], False)
            self.assertLessEqual(call.kwargs['timeout'], 30)
        self.assert_clean()

    def test_empty_audio(self):
        self.assertEqual(self.post(b'').status_code, 400)
        self.run.assert_not_called()

    def test_invalid_mime(self):
        self.assertEqual(self.post(mime='text/plain').status_code, 400)
        self.run.assert_not_called()

    def test_all_supported_mimes(self):
        for mime in service.MIME_SUFFIXES:
            with self.subTest(mime=mime):
                self.assertEqual(self.post(mime=mime).status_code, 200)

    def test_exact_size_limit_and_overflow(self):
        with patch.dict(os.environ, WHISPER_MAX_AUDIO_BYTES='5'):
            self.assertEqual(self.post(b'12345').status_code, 200)
            self.run.reset_mock()
            self.assertEqual(self.post(b'123456').status_code, 413)
            self.run.assert_not_called()

    def test_stream_without_content_length_is_bounded(self):
        with patch.dict(os.environ, WHISPER_MAX_AUDIO_BYTES='5'):
            self.assertEqual(self.post(iter([b'123', b'456'])).status_code, 413)
            self.run.assert_not_called()

    def test_missing_or_unconfigured_tools(self):
        for key in ('WHISPER_CLI_PATH', 'WHISPER_MODEL_PATH', 'FFMPEG_PATH'):
            for value in ('', str(self.root / 'absent'), '//server/private'):
                with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}):
                    response = self.post()
                    self.assertEqual(response.status_code, 503)
                    self.assertNotIn(str(self.root), response.text)
        self.run.assert_not_called()

    def test_invalid_configuration(self):
        for key, value in [('WHISPER_TIMEOUT_SECONDS', 'nan'), ('WHISPER_TIMEOUT_SECONDS', '-1'), ('WHISPER_MAX_AUDIO_BYTES', '0'), ('WHISPER_LANGUAGE', '--translate')]:
            with self.subTest(key=key), patch.dict(os.environ, {key: value}):
                self.assertEqual(self.post().status_code, 503)

    def test_timeout_each_stage_cleans_files(self):
        for stage in (1, 2):
            self.run.reset_mock()
            def timeout(args, **kwargs):
                self.native(args, **kwargs)
                if self.run.call_count == stage:
                    raise subprocess.TimeoutExpired(args, 30)
                return subprocess.CompletedProcess(args, 0)
            self.run.side_effect = timeout
            self.assertEqual(self.post().status_code, 504)
            self.assert_clean()

    def test_native_failures_sanitized_and_cleaned(self):
        for stage, code in ((1, 400), (2, 503)):
            self.run.reset_mock()
            def fail(args, **kwargs):
                self.native(args, **kwargs)
                return subprocess.CompletedProcess(args, 1 if self.run.call_count == stage else 0, b'secret', b'secret')
            self.run.side_effect = fail
            response = self.post()
            self.assertEqual(response.status_code, code)
            self.assertNotIn('secret', response.text)
            self.assert_clean()

    def test_os_error_cleans_files(self):
        def fail(args, **kwargs):
            self.native(args, **kwargs)
            raise OSError('private path')
        self.run.side_effect = fail
        self.assertEqual(self.post().status_code, 503)
        self.assert_clean()

    def test_empty_transcript_is_not_invented(self):
        self.text = ' \n'
        self.assertEqual(self.post().json()['text'], '')
        self.assert_clean()

    def test_no_database_or_network_access(self):
        with patch.object(sqlite3, 'connect', side_effect=AssertionError('No SQLite')), \
             patch('socket.socket.connect', side_effect=AssertionError('No network')), \
             patch('backend.app.services.ollama_client.generate_reply', side_effect=AssertionError('No Ollama')):
            self.assertEqual(self.post().status_code, 200)
        self.assert_clean()

    def test_performance_absent_by_default_and_when_disabled(self):
        for value in (None, 'false', '0', 'invalid'):
            with self.subTest(value=value), patch.dict(os.environ):
                if value is None:
                    os.environ.pop('WHISPER_PERF_DEBUG', None)
                else:
                    os.environ['WHISPER_PERF_DEBUG'] = value
                with self.assertLogs('uvicorn.error.voice', level='INFO') as logs:
                    response = self.post()
                self.assertEqual(set(response.json()), {'text', 'language', 'processing_ms'})
                self.assertEqual(len(logs.output), 1)
                self.assertIn('[VOICE PERF]', logs.output[0])

    def test_debug_timings_measure_separate_stages_and_preserve_contract(self):
        clock = [100.0]
        original_write = Path.write_bytes
        original_read = Path.read_text
        original_cleanup = tempfile.TemporaryDirectory.cleanup
        original_stream = Request.stream

        def write(path, data):
            if path.name.startswith('input.'):
                clock[0] += .008
            return original_write(path, data)

        def read(path, *args, **kwargs):
            if path.name == 'transcript.txt':
                clock[0] += .003
            return original_read(path, *args, **kwargs)

        def cleanup(directory):
            if Path(directory.name).name.startswith('psychospace-voice-'):
                clock[0] += .004
            return original_cleanup(directory)

        async def stream(request):
            clock[0] += .120
            async for chunk in original_stream(request):
                yield chunk

        def native(args, **kwargs):
            clock[0] += .640 if '-i' in args else 4.200
            return self.native(args, **kwargs)

        self.run.side_effect = native
        with patch.dict(os.environ, WHISPER_PERF_DEBUG='true'), \
             patch('time.perf_counter', side_effect=lambda: clock[0]), \
             patch.object(Path, 'write_bytes', write), patch.object(Path, 'read_text', read), \
             patch.object(tempfile.TemporaryDirectory, 'cleanup', cleanup), \
             patch.object(Request, 'stream', stream), \
             self.assertLogs('uvicorn.error.voice', level='INFO') as logs:
            response = self.post()
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(set(result), {'text', 'language', 'processing_ms', 'performance'})
        self.assertEqual(result['text'], self.text)
        self.assertEqual(result['language'], 'fr')
        self.assertEqual(result['processing_ms'], 4855)
        expected = dict(upload_ms=120, write_ms=8, ffmpeg_ms=640, whisper_ms=4200,
                        parse_ms=3, cleanup_ms=4, total_ms=4975)
        self.assertEqual(result['performance'], expected)
        for key, value in expected.items():
            self.assertIn(f'{key}={value:.3f}', logs.output[0])
        for private in (self.text, str(self.root), 'diagnostics', 'private path'):
            self.assertNotIn(private, logs.output[0])
        self.assert_clean()

    def test_debug_errors_preserve_status_body_and_cleanup_with_timings_logged(self):
        def timeout(args, **kwargs):
            self.native(args, **kwargs)
            raise subprocess.TimeoutExpired(args, 30)
        self.run.side_effect = timeout
        with patch.dict(os.environ, WHISPER_PERF_DEBUG='1'):
            for data, mime, status in ((b'', 'audio/wav', 400), (b'a', 'text/plain', 400),
                                       (b'a', 'audio/wav', 504)):
                with self.subTest(status=status), self.assertLogs('uvicorn.error.voice', level='INFO') as logs:
                    response = self.post(data, mime)
                self.assertEqual(response.status_code, status)
                self.assertEqual(set(response.json()), {'success', 'error'})
                self.assertNotIn('performance', response.json())
                self.assertIn('cleanup_ms=', logs.output[0])
                self.assertIn('total_ms=', logs.output[0])
                self.assertNotIn(str(self.root), logs.output[0])
        self.assert_clean()

    def test_timings_are_not_shared_between_requests(self):
        with patch.dict(os.environ, WHISPER_PERF_DEBUG='true'):
            self.assertEqual(self.post().status_code, 200)
            with self.assertLogs('uvicorn.error.voice', level='INFO') as logs:
                self.assertEqual(self.post(b'').status_code, 400)
        for stage in ('write_ms', 'ffmpeg_ms', 'whisper_ms', 'parse_ms', 'cleanup_ms'):
            self.assertIn(f'{stage}=0.000', logs.output[0])

    def test_local_debug_configuration_respects_environment(self):
        (self.root / '.env.local').write_text('WHISPER_PERF_DEBUG=true\n', encoding='utf-8')
        with patch('backend.app.config.PROJECT_ROOT', self.root), patch.dict(os.environ):
            os.environ.pop('WHISPER_PERF_DEBUG', None)
            load_local_ollama_config()
            self.assertEqual(os.environ['WHISPER_PERF_DEBUG'], 'true')
            os.environ['WHISPER_PERF_DEBUG'] = 'false'
            load_local_ollama_config()
            self.assertEqual(os.environ['WHISPER_PERF_DEBUG'], 'false')

    def test_automatic_threads_reserve_capacity_and_are_capped(self):
        for cpus, expected in ((None, 1), (1, 1), (2, 1), (3, 1), (4, 2), (6, 3), (8, 4), (32, 4)):
            with self.subTest(cpus=cpus), patch.object(service.os, 'cpu_count', return_value=cpus):
                self.assertEqual(service.whisper_threads(), expected)
                if cpus and cpus > 1:
                    self.assertLess(expected, cpus)

    def test_explicit_threads_passed_only_to_whisper_and_logged(self):
        with patch.dict(os.environ, WHISPER_THREADS='4'), self.assertLogs('uvicorn.error.voice', level='INFO') as logs:
            response = self.post()
        self.assertEqual(response.status_code, 200)
        ffmpeg, whisper = [call.args[0] for call in self.run.call_args_list]
        self.assertEqual(ffmpeg[ffmpeg.index('-t') + 1], '30')
        self.assertEqual(whisper[whisper.index('-t') + 1], '4')
        self.assertEqual(whisper.count('-t'), 1)
        self.assertEqual(whisper[whisper.index('-l') + 1], 'fr')
        self.assertEqual(whisper[whisper.index('-m') + 1], self.settings['WHISPER_MODEL_PATH'])
        self.assertEqual(set(whisper) & {'--translate', '-tr', '-bs', '-bo', '-tp'}, set())
        self.assertIn('whisper_threads=4', logs.output[0])
        self.assertEqual(set(response.json()), {'text', 'language', 'processing_ms'})
        self.assert_clean()

    def test_automatic_threads_passed_to_cli_without_configuration(self):
        with patch.dict(os.environ), patch.object(service.os, 'cpu_count', return_value=4):
            os.environ.pop('WHISPER_THREADS', None)
            self.assertEqual(self.post().status_code, 200)
        whisper = self.run.call_args_list[1].args[0]
        self.assertEqual(whisper[whisper.index('-t') + 1], '2')

    def test_invalid_threads_fail_safely_before_native_processes(self):
        for value in ('0', '-1', '2.5', 'abc', '2 --translate'):
            with self.subTest(value=value), patch.dict(os.environ, WHISPER_THREADS=value):
                response = self.post()
                self.assertEqual(response.status_code, 503)
                self.assertNotIn(value, response.json()['error']['message'])
        self.run.assert_not_called()

    def test_thread_configuration_respects_process_environment(self):
        (self.root / '.env.local').write_text('WHISPER_THREADS=4\n', encoding='utf-8')
        with patch('backend.app.config.PROJECT_ROOT', self.root), patch.dict(os.environ):
            os.environ.pop('WHISPER_THREADS', None)
            load_local_ollama_config()
            self.assertEqual(service.whisper_threads(), 4)
            os.environ['WHISPER_THREADS'] = '2'
            load_local_ollama_config()
            self.assertEqual(service.whisper_threads(), 2)


if __name__ == '__main__':
    unittest.main()
