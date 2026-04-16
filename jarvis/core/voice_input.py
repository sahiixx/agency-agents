"""Speech-to-text microphone listener for JARVIS."""

from __future__ import annotations

from config import WAKE_WORD
from utils.logger import setup_logger

try:
    import speech_recognition as sr  # type: ignore
except Exception:  # pragma: no cover
    sr = None


class VoiceInput:
    """Handles voice and keyboard input with wake-word support."""

    def __init__(self) -> None:
        self.logger = setup_logger("jarvis.voice_input")
        self._recognizer = sr.Recognizer() if sr else None
        self._microphone = None
        self._keyboard_fallback = True
        if self._recognizer and sr:
            try:
                self._microphone = sr.Microphone()
                self._keyboard_fallback = False
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=1)
            except Exception as exc:
                self.logger.warning("Microphone unavailable, using keyboard fallback: %s", exc)

    def listen(self, require_wake_word: bool = True) -> str:
        """Listen for a command and optionally enforce wake word."""
        if self._keyboard_fallback or not self._recognizer or not self._microphone:
            prompt = "You: " if not require_wake_word else f"You ({WAKE_WORD} ...): "
            text = input(prompt).strip().lower()
            if not require_wake_word:
                return text
            if text.startswith(WAKE_WORD):
                return text.replace(WAKE_WORD, "", 1).strip()
            if text.startswith("hey jarvis"):
                return text.replace("hey jarvis", "", 1).strip()
            return ""

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = self._recognizer.recognize_google(audio).lower().strip()
            if not require_wake_word:
                return text
            if text.startswith(WAKE_WORD):
                return text.replace(WAKE_WORD, "", 1).strip()
            if text.startswith("hey jarvis"):
                return text.replace("hey jarvis", "", 1).strip()
            return ""
        except Exception as exc:
            self.logger.debug("Voice capture/recognition failed: %s", exc)
            return ""
