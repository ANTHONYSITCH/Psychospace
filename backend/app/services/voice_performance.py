"""Request-local timing only: never collect audio, text, paths or commands."""
from contextlib import contextmanager
import logging
import time


# Inherit Uvicorn's console handler so INFO timings appear with the normal launch command.
logger = logging.getLogger("uvicorn.error.voice")


class VoicePerformance:
    def __init__(self):
        self.started = time.perf_counter()
        self.whisper_threads = None
        self.timings = dict.fromkeys(("upload_ms", "write_ms", "ffmpeg_ms", "whisper_ms",
                                      "parse_ms", "cleanup_ms", "total_ms"), 0.0)

    @contextmanager
    def measure(self, stage):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.timings[stage] = (time.perf_counter() - started) * 1000

    def finish(self):
        self.timings["total_ms"] = (time.perf_counter() - self.started) * 1000
        result = {key: round(value, 3) for key, value in self.timings.items()}
        logger.info("[VOICE PERF] %s whisper_threads=%s",
                    " ".join(f"{key}={value:.3f}" for key, value in result.items()),
                    self.whisper_threads if self.whisper_threads is not None else "non_lancé")
        return result
