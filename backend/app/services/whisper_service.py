"""Ephemeral, local-only speech transcription. No database or network access."""
import math
import os
import subprocess
import tempfile
import time
from pathlib import Path


class VoiceError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


MIME_SUFFIXES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/wav": ".wav",
                 "audio/mpeg": ".mp3", "audio/mp4": ".mp4"}
UNAVAILABLE = "La transcription vocale locale n'est pas disponible pour le moment."


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


def transcribe(audio: bytes, content_type: str):
    start = time.monotonic()
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
    try:
        timeout = float(os.environ.get("WHISPER_TIMEOUT_SECONDS", "30"))
        if not math.isfinite(timeout) or timeout <= 0 or not language.isalpha():
            raise ValueError
    except ValueError:
        raise VoiceError(503, UNAVAILABLE) from None

    def run(args):
        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, timeout)
        return subprocess.run(args, shell=False, stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=remaining, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

    try:
        with tempfile.TemporaryDirectory(prefix="psychospace-voice-") as directory:
            source = Path(directory) / ("input" + suffix)
            wav = Path(directory) / "audio.wav"
            output = Path(directory) / "transcript"
            source.write_bytes(audio)  # Closes the handle before either Windows process starts.
            converted = run([ffmpeg, "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file,pipe",
                             "-i", str(source), "-t", "30", "-ar", "16000", "-ac", "1",
                             "-c:a", "pcm_s16le", str(wav)])
            if converted.returncode:
                raise VoiceError(400, "L'audio n'a pas pu être décodé.")
            result = run([whisper, "-m", model, "-f", str(wav), "-l", language,
                          "-nt", "-np", "-otxt", "-of", str(output)])
            if result.returncode:
                raise VoiceError(503, UNAVAILABLE)
            # Read the text output, never diagnostics from stdout/stderr.
            text = output.with_suffix(".txt").read_text(encoding="utf-8-sig").strip()
        return {"text": text, "language": language, "processing_ms": round((time.monotonic() - start) * 1000)}
    except subprocess.TimeoutExpired:
        raise VoiceError(504, "La transcription locale a dépassé le délai prévu.") from None
    except (OSError, UnicodeError):
        raise VoiceError(503, UNAVAILABLE) from None
