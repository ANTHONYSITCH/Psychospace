"""Diagnostic manuel hors runtime : python -m backend.scripts.benchmark_whisper --synthetic."""
import argparse
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
import wave

from backend.app.config import load_local_ollama_config


PHRASE = "Ça va, je suis juste fatigué aujourd'hui et je pense que demain, ça ira mieux."


def candidates(cpu_count):
    return [threads for threads in (2, 4, 6, 8) if threads <= (cpu_count or 1)]


def run(args, timeout=120, **kwargs):
    return subprocess.run(args, shell=False, stdin=subprocess.DEVNULL, capture_output=True,
                          timeout=timeout, check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, **kwargs)


def synthetic_wav(directory):
    """Only a fixed synthetic sentence; never records a user's microphone."""
    if os.name != 'nt':
        raise ValueError("La génération Hortense nécessite Windows ; utiliser --wav.")
    raw, wav = directory / 'synthetic.wav', directory / 'input.wav'
    environment = {**os.environ, 'PS_BENCH_AUDIO': str(raw)}
    # Fixed script, path passed as an environment value, never interpolated into shell code.
    script = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voice.SelectVoice('Microsoft Hortense Desktop')
    $voice.SetOutputToWaveFile($env:PS_BENCH_AUDIO)
    $voice.Speak("Ça va, je suis juste fatigué aujourd'hui et je pense que demain, ça ira mieux.")
} finally { $voice.Dispose() }
"""
    run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script], env=environment)
    ffmpeg = os.environ.get('FFMPEG_PATH', '')
    if not ffmpeg or not Path(ffmpeg).is_file():
        raise ValueError('FFmpeg local non configuré.')
    run([ffmpeg, '-nostdin', '-v', 'error', '-y', '-i', str(raw), '-ar', '16000', '-ac', '1',
         '-c:a', 'pcm_s16le', str(wav)])
    return wav


def benchmark(wav, directory, threads_list, executable, model):
    results = {threads: [] for threads in threads_list}
    # Alternate configurations to reduce ordering bias. No persistent server or warm-up.
    for repetition in range(3):
        order = threads_list if repetition % 2 == 0 else list(reversed(threads_list))
        for threads in order:
            output = directory / f'text-{threads}-{repetition}'
            started = time.perf_counter()
            run([executable, '-m', model, '-f', str(wav), '-l', 'fr', '-nt', '-np',
                 '-otxt', '-of', str(output), '-t', str(threads)])
            elapsed = (time.perf_counter() - started) * 1000
            text = output.with_suffix('.txt').read_text(encoding='utf-8-sig').strip()
            results[threads].append((elapsed, text))
            print(f'{threads} threads — run {repetition + 1} : {elapsed:.3f} ms — {text}', flush=True)
    for threads, runs in results.items():
        print(f'{threads} threads — moyenne : {statistics.mean(ms for ms, _ in runs):.3f} ms', flush=True)
    if results:
        winner = min(results, key=lambda threads: statistics.mean(ms for ms, _ in results[threads]))
        print(f'Plus rapide sur cet essai : {winner} threads. Configuration inchangée.', flush=True)
        texts = {text for runs in results.values() for _, text in runs}
        print(f'Transcriptions identiques entre les runs : {"oui" if len(texts) == 1 else "non"}.', flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description='Comparer Whisper local, modèle base, langue française, trois runs par configuration.')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--wav', type=Path, help='WAV local PCM 16 bits mono 16 kHz existant, lu sans modification ni copie.')
    source.add_argument('--synthetic', action='store_true', help='Créer une phrase Hortense temporaire, supprimée en fin de test.')
    args = parser.parse_args()
    load_local_ollama_config()  # Loads paths only; does not contact Ollama or change its settings.
    executable = os.environ.get('WHISPER_CLI_PATH', '')
    model = os.environ.get('WHISPER_MODEL_PATH', '')
    if not executable or not Path(executable).is_file() or not Path(model).is_file() or Path(model).name != 'ggml-base.bin':
        parser.error('Configurer whisper-cli local et le modèle ggml-base.bin existant.')
    logical = os.cpu_count() or 1
    options = candidates(logical)
    print(f'CPU logiques : {logical}. Configurations testées : {options}.', flush=True)
    print(f'Ignorées faute de CPU : {[t for t in (2, 4, 6, 8) if t not in options]}.', flush=True)
    if not options:
        parser.error('Au moins deux CPU logiques sont nécessaires pour ce benchmark.')
    try:
        with tempfile.TemporaryDirectory(prefix='psychospace-benchmark-') as temporary:
            directory = Path(temporary)
            wav = synthetic_wav(directory) if args.synthetic else args.wav.resolve()
            with wave.open(str(wav), 'rb') as audio:
                if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 16000, 'NONE'):
                    raise ValueError('Le WAV doit être PCM signé 16 bits, mono, 16 kHz.')
                print(f'Durée audio : {audio.getnframes() / audio.getframerate():.3f} s.', flush=True)
            if args.synthetic:
                print(f'Audio synthétique local : {PHRASE}', flush=True)
            benchmark(wav, directory, options, executable, model)
        print('Fichiers temporaires supprimés ; aucun réglage sauvegardé.', flush=True)
    except (OSError, ValueError, wave.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f'Échec du benchmark ({type(error).__name__}) ; nettoyage temporaire effectué.\n')


if __name__ == '__main__':
    main()
