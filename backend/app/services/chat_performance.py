"""Request-scoped numeric metrics. Never retain or log conversational content."""
from contextlib import contextmanager
from contextvars import ContextVar
import logging
import time

logger = logging.getLogger('uvicorn.error.chat')
current_performance = ContextVar('chat_performance', default=None)
OLLAMA_FIELDS = ('load_duration', 'prompt_eval_count', 'prompt_eval_duration',
                 'eval_count', 'eval_duration', 'total_duration')


class ChatPerformance:
    def __init__(self):
        self.started = time.perf_counter()
        self.metrics = dict.fromkeys(('context_ms', 'prompt_ms', 'ollama_ms', 'persist_ms', 'total_ms'), 0.0)
        self.metrics.update(dict.fromkeys(('first_token_ms', 'generation_ms', 'prompt_chars',
                                          'prompt_tokens', 'generated_tokens', 'tokens_per_second',
                                          'ollama_load_ms', 'ollama_prompt_eval_ms', 'ollama_eval_ms',
                                          'ollama_total_ms', *OLLAMA_FIELDS)))

    @contextmanager
    def active(self):
        token = current_performance.set(self)
        try:
            yield self
        finally:
            current_performance.reset(token)

    @contextmanager
    def measure(self, name):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.metrics[name] = (time.perf_counter() - started) * 1000

    def collect_ollama(self, response):
        # An optional malformed metric must not change a valid chat response.
        for field in OLLAMA_FIELDS:
            value = response.get(field)
            self.metrics[field] = value if type(value) is int and 0 <= value <= 2**63 - 1 else None
        self.metrics['prompt_tokens'] = self.metrics['prompt_eval_count']
        self.metrics['generated_tokens'] = self.metrics['eval_count']
        for source, target in (('load_duration', 'ollama_load_ms'),
                               ('prompt_eval_duration', 'ollama_prompt_eval_ms'),
                               ('eval_duration', 'ollama_eval_ms'), ('total_duration', 'ollama_total_ms')):
            value = self.metrics[source]
            self.metrics[target] = value / 1_000_000 if value is not None else None
        count, duration = self.metrics['eval_count'], self.metrics['eval_duration']
        if count is not None and duration:
            self.metrics['tokens_per_second'] = count * 1_000_000_000 / duration

    def finish(self):
        self.metrics['total_ms'] = (time.perf_counter() - self.started) * 1000
        result = {key: round(value, 3) if isinstance(value, float) else value
                  for key, value in self.metrics.items()}
        logger.info('[CHAT PERF] %s', ' '.join(f'{key}={value if value is not None else "null"}'
                                            for key, value in result.items()))
        return result
