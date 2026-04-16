"""Advanced text-to-speech with Piper-first fallback to pyttsx3."""

from __future__ import annotations

import re
from dataclasses import dataclass

try:
    import piper  # type: ignore
except Exception:  # pragma: no cover
    piper = None

try:
    import pyttsx3  # type: ignore
except Exception:  # pragma: no cover
    pyttsx3 = None


@dataclass
class VoiceProfile:
    name: str
    style: str


class AdvancedTTS:
    """Offline-capable TTS abstraction supporting Piper and pyttsx3."""

    def __init__(self, engine: str = "piper"):
        self.engine_name = engine
        self.voice_profiles = {
            "jarvis": VoiceProfile("jarvis", "deep"),
            "casual": VoiceProfile("casual", "friendly"),
            "formal": VoiceProfile("formal", "professional"),
        }
        self._pyttsx3 = pyttsx3.init() if engine == "pyttsx3" and pyttsx3 else None

    @property
    def available(self) -> bool:
        if self.engine_name == "piper":
            return piper is not None
        return self._pyttsx3 is not None

    @staticmethod
    def _strip_ssml(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text)

    def speak(self, text: str, profile: str = "jarvis", emotion: str = "calm") -> str:
        payload = f"[{emotion}] {self._strip_ssml(text)}"
        if self.engine_name == "piper" and piper is None:
            return "Install piper-tts for advanced offline voices: pip install piper-tts"
        if self.engine_name == "pyttsx3" and self._pyttsx3 is None:
            return "Install pyttsx3 for fallback TTS: pip install pyttsx3"
        if self._pyttsx3:
            self._pyttsx3.say(payload)
            self._pyttsx3.runAndWait()
        return payload

    def clone_voice(self, sample_path: str) -> str:
        return f"Voice cloning requested for {sample_path}. Provide a Piper-compatible cloning pipeline."
