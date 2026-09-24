"""Manual benchmark of the real chat route and local Ollama, never imported by runtime."""
import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import time
from urllib.parse import urlsplit

import httpx
from fastapi.testclient import TestClient

from backend.app.config import get_database_path, load_local_ollama_config
from backend.app.main import create_app

MESSAGE = "Ça va, je suis juste fatigué aujourd'hui."


def backup(source, destination):
    with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True)) as reader:
        with closing(sqlite3.connect(destination)) as writer:
            reader.backup(writer)


def run_benchmark(source):
    previous = os.environ.get('CHAT_PERF_DEBUG')
    os.environ['CHAT_PERF_DEBUG'] = 'true'
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix='psychospace-chat-benchmark-') as temporary:
            directory = Path(temporary)
            snapshot = directory / 'snapshot.db'
            backup(source, snapshot)
            for number in range(1, 4):
                database = directory / f'run-{number}.db'
                backup(snapshot, database)
                # The snapshot already has the production schema/data. Do not run startup seeds.
                client = TestClient(create_app(database))
                print(f'Run {number} — {"potentiellement froid" if number == 1 else "chaud attendu"} : début.', flush=True)
                try:
                    started = time.perf_counter()
                    response = client.post('/api/chat', json={'user_id': 'ASTRO-001', 'message': MESSAGE})
                    http_ms = round((time.perf_counter() - started) * 1000, 3)
                    if response.status_code != 200:
                        print(f'Run {number} — échec HTTP {response.status_code}.', flush=True)
                        results.append({'run': number, 'status': response.status_code, 'http_ms': http_ms})
                        continue
                    metrics = response.json()['performance']
                    result = {'run': number, 'http_ms': http_ms, **metrics}
                    results.append(result)
                    # Whitelisted numeric metrics only: never print the response content.
                    print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
                finally:
                    client.close()
    finally:
        if previous is None:
            os.environ.pop('CHAT_PERF_DEBUG', None)
        else:
            os.environ['CHAT_PERF_DEBUG'] = previous
    print('Copies SQLite temporaires supprimées ; historique principal inchangé.', flush=True)
    return results


def main():
    load_local_ollama_config()
    url = os.environ.get('OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname not in {'localhost', '127.0.0.1', '::1'}
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise SystemExit('Le benchmark nécessite une URL Ollama locale.')
    try:
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=5) as client:
            # Read-only status: neither loads nor unloads any model.
            response = client.get(url + '/api/ps')
            response.raise_for_status()
            loaded = any(item.get('name') == os.environ.get('OLLAMA_MODEL')
                         for item in response.json().get('models', []))
        print(f'Modèle déjà chargé avant run 1 : {"oui" if loaded else "non"}. Aucun préchargement.', flush=True)
        results = run_benchmark(get_database_path())
    except (httpx.HTTPError, OSError, sqlite3.Error, ValueError, KeyError):
        raise SystemExit('Benchmark indisponible : vérifier Ollama local et la base SQLite existante.') from None
    if any('status' in result for result in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
