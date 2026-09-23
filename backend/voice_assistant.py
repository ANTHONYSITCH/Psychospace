from __future__ import annotations

import os
from typing import Optional

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:  # pragma: no cover
    sr = None


class VoiceAssistant:
    """Local voice layer for ARIA. Optional: works if dependencies are installed."""

    def __init__(self, language: str = "fr-FR"):
        self.language = language
        self.engine = None
        self.recognizer = None

        if pyttsx3 is not None:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 170)
            self.engine.setProperty("volume", 0.9)

        if sr is not None:
            self.recognizer = sr.Recognizer()

    def speak(self, text: str) -> bool:
        if not text or self.engine is None:
            return False
        try:
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception:
            return False

    def listen_once(self, timeout: int = 10, phrase_time_limit: int = 8) -> Optional[str]:
        if self.recognizer is None:
            return None

        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            return self.recognizer.recognize_google(audio, language=self.language)
        except Exception:
            return None

    def is_available(self) -> bool:
        return self.engine is not None or self.recognizer is not None


if __name__ == "__main__":
    assistant = VoiceAssistant()
    print("voice_available:", assistant.is_available())
