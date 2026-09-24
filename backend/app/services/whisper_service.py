"""Ephemeral, local-only speech transcription. No database or network access."""
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path

from .voice_performance import VoicePerformance


class VoiceError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


MIME_SUFFIXES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/wav": ".wav",
                 "audio/mpeg": ".mp3", "audio/mp4": ".mp4"}
UNAVAILABLE = "La transcription vocale locale n'est pas disponible pour le moment."


def whisper_threads():
    """Conservative automatic budget; an explicit positive integer overrides it."""
    configured = os.environ.get("WHISPER_THREADS", "").strip()
    if configured:
        try:
            value = int(configured)
            if value < 1:
                raise ValueError
            return value
        except ValueError:
            raise VoiceError(503, UNAVAILABLE) from None
    # Half the logical CPUs, capped at four. One CPU is the unavoidable minimum.
    return min(4, max(1, (os.cpu_count() or 1) // 2))


def max_audio_bytes():
    try:
        value = int(os.environ.get("WHISPER_MAX_AUDIO_BYTES", "10485760"))
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        raise VoiceError(503, UNAVAILABLE) from None


def audio_suffix(content_type):
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime not in MIME_SUFFIXES:
        raise VoiceError(400, "Ce format audio n'est pas pris en charge.")
    return MIME_SUFFIXES[mime]


def transcribe(audio: bytes, content_type: str, *, performance=None):
    start = time.perf_counter()
    if performance is None:
        performance = VoicePerformance()
    if not audio:
        raise VoiceError(400, "L'audio est vide.")
    if len(audio) > max_audio_bytes():
        raise VoiceError(413, "L'audio est trop volumineux.")
    suffix = audio_suffix(content_type)
    paths = [os.environ.get(key, "") for key in ("FFMPEG_PATH", "WHISPER_CLI_PATH", "WHISPER_MODEL_PATH")]
    # UNC paths would access a network share, contrary to the local-only contract.
    if any(not p or p.startswith(("\\\\", "//")) or not Path(p).is_file() for p in paths):
        raise VoiceError(503, UNAVAILABLE)
    ffmpeg, whisper, model = paths
    language = os.environ.get("WHISPER_LANGUAGE", "fr")
    threads = whisper_threads()
    try:
        timeout = float(os.environ.get("WHISPER_TIMEOUT_SECONDS", "30"))
        if not math.isfinite(timeout) or timeout <= 0 or not language.isalpha():
            raise ValueError
    except ValueError:
        raise VoiceError(503, UNAVAILABLE) from None

    def run(args):
        remaining = timeout - (time.perf_counter() - start)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, timeout)
        return subprocess.run(args, shell=False, stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=remaining, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    try:
        cleanup_start = None
        try:
            with tempfile.TemporaryDirectory(prefix="psychospace-voice-") as directory:
                try:
                    source = Path(directory) / ("input" + suffix)
                    wav = Path(directory) / "audio.wav"
                    output = Path(directory) / "transcript"
                    with performance.measure("write_ms"):
                        source.write_bytes(audio)  # Close the handle before starting Windows processes.
                    with performance.measure("ffmpeg_ms"):
                        converted = run([ffmpeg, "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file,pipe",
                                         "-i", str(source), "-t", "30", "-ar", "16000", "-ac", "1",
                                         "-c:a", "pcm_s16le", str(wav)])
                    if converted.returncode:
                        raise VoiceError(400, "L'audio n'a pas pu être décodé.")
                    with performance.measure("whisper_ms"):
                        performance.whisper_threads = threads
                        result = run([whisper, "-m", model, "-f", str(wav), "-l", language,
                                      "-nt", "-np", "-otxt", "-of", str(output), "-t", str(threads)])
                    if result.returncode:
                        raise VoiceError(503, UNAVAILABLE)
                    # Read the text output, never diagnostics from stdout/stderr.
                    with performance.measure("parse_ms"):
                        text = output.with_suffix(".txt").read_text(encoding="utf-8-sig").strip()
                finally:
                    cleanup_start = time.perf_counter()
        finally:
            if cleanup_start is not None:
                performance.timings["cleanup_ms"] = (time.perf_counter() - cleanup_start) * 1000
        return {"text": text, "language": language, "processing_ms": round((time.perf_counter() - start) * 1000)}
    except subprocess.TimeoutExpired:
        raise VoiceError(504, "La transcription locale a dépassé le délai prévu.") from None
    except (OSError, UnicodeError):
        raise VoiceError(503, UNAVAILABLE) from None
