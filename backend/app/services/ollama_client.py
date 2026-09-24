"""HTTP client restricted to a local Ollama instance and locally stored models."""

import os
import logging
from time import perf_counter
from urllib.parse import urlsplit

import httpx

from ..config import get_ollama_options
from .chat_performance import current_performance

logger = logging.getLogger(__name__)


class OllamaUnavailable(Exception):
    """A safe, user-facing service failure."""


def generate_reply(messages):
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "").strip()
    try:
        options = get_ollama_options()
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path or not model or "cloud" in model.lower()):
            raise OllamaUnavailable("Configurer une URL Ollama locale et un modèle local via OLLAMA_MODEL.")
        # No proxy inherited from the machine; no redirects or automatic model downloads.
        with httpx.Client(timeout=httpx.Timeout(options.timeout_seconds, connect=min(5, options.timeout_seconds)), trust_env=False, follow_redirects=False) as client:
            info = client.post(url + "/api/show", json={"model": model})
            info.raise_for_status()
            details = info.json()
            if (not isinstance(details, dict) or details.get("remote_host") or details.get("remote_model")
                    or not details.get("model_info")):
                raise OllamaUnavailable("Le modèle doit être installé localement dans Ollama.")
            started = perf_counter()
            response = client.post(url + "/api/chat", json={
                "model": model, "messages": messages, "stream": False,
                "options": {"temperature": options.temperature, "num_predict": options.num_predict, "num_ctx": options.num_ctx},
            })
            response.raise_for_status()
            data = response.json()
            reply = data.get("message", {}) if isinstance(data, dict) else {}
            content = reply.get("content") if isinstance(reply, dict) else None
            if (not isinstance(content, str) or not content.strip() or reply.get("role") != "assistant"
                    or data.get("done") is not True or data.get("error")):
                raise OllamaUnavailable("Ollama a renvoyé une réponse invalide.")
            logger.info("Ollama generation completed in %.2f seconds", perf_counter() - started)
            performance = current_performance.get()
            if performance is not None:
                performance.collect_ollama(data)
            return content.strip()
    except (httpx.HTTPError, ValueError) as exc:
        raise OllamaUnavailable("Ollama indisponible, modèle absent, délai dépassé ou réponse invalide.") from exc
