"""Paths are independent of the process working directory."""

import os
import math
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
SEEDS_PATH = PROJECT_ROOT / "database" / "seeds"


def load_local_ollama_config() -> None:
    """Read local engine settings at startup; process environment takes precedence."""
    path = PROJECT_ROOT / ".env.local"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, separator, value = line.strip().partition("=")
            if separator and key.strip() in {"OLLAMA_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS",
                                             "OLLAMA_NUM_PREDICT", "OLLAMA_TEMPERATURE",
                                             "WHISPER_CLI_PATH", "WHISPER_MODEL_PATH", "FFMPEG_PATH",
                                             "WHISPER_LANGUAGE", "WHISPER_TIMEOUT_SECONDS", "WHISPER_MAX_AUDIO_BYTES"}:
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class OllamaOptions:
    timeout_seconds: float
    num_predict: int
    temperature: float
    num_ctx: int = 8192


def get_ollama_options():
    options = OllamaOptions(
        float(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "60")),
        int(os.environ.get("OLLAMA_NUM_PREDICT", "160")),
        float(os.environ.get("OLLAMA_TEMPERATURE", "0.3")),
    )
    if (not math.isfinite(options.timeout_seconds) or options.timeout_seconds <= 0
            or options.num_predict <= 0 or not math.isfinite(options.temperature)
            or not 0 <= options.temperature <= 2):
        raise ValueError("Invalid Ollama options")
    return options


def get_database_path() -> Path:
    """A simple path override; DATABASE_URL parsing is deferred."""
    path = Path(os.environ.get("PSYCHOSPACE_DB_PATH", "database/psychospace.db"))
    return path if path.is_absolute() else PROJECT_ROOT / path
