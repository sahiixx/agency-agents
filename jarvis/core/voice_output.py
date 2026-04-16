"""Text-to-speech output layer for JARVIS."""

from __future__ import annotations

import queue
import threading

from config import SPEECH_RATE, VOICE_INDEX
from utils.logger import setup_logger

try:
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    pyttsx3 = None


class VoiceOutput:
    """Queue-driven text-to-speech speaker."""

    def __init__(self) -> None:
        self.logger = setup_logger("jarvis.voice_output")
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._engine = None
        self._worker = threading.Thread(target=self._consume, daemon=True)
        self._ready = False
        self._init_engine()
        self._worker.start()

    def _init_engine(self) -> None:
        if pyttsx3 is None:
            self.logger.warning("pyttsx3 unavailable; falling back to console output")
            return
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", SPEECH_RATE)
            voices = self._engine.getProperty("voices") or []
            if voices:
                index = max(0, min(VOICE_INDEX, len(voices) - 1))
                self._engine.setProperty("voice", voices[index].id)
            self._ready = True
        except Exception as exc:
            self.logger.exception("Failed to initialize speech engine: %s", exc)

    def say(self, text: str) -> None:
        """Queue text to be spoken."""
        if text.strip():
            self._queue.put(text.strip())

    def _consume(self) -> None:
        while True:
            text = self._queue.get()
            try:
                if self._ready and self._engine is not None:
                    self._engine.say(text)
                    self._engine.runAndWait()
                else:
                    print(f"JARVIS: {text}")
            except Exception as exc:
                self.logger.exception("TTS error: %s", exc)
