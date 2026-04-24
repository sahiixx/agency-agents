"""Offline-first speech-to-text using faster-whisper with fallback support."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Iterable

try:
    from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    WhisperModel = None


class WhisperSTT:
    """Transcribes audio with faster-whisper when available."""

    SUPPORTED_MODELS = {"tiny", "base", "small", "medium", "large-v3"}

    def __init__(self, model_name: str = "base", use_whisper: bool = True):
        self.model_name = model_name if model_name in self.SUPPORTED_MODELS else "base"
        self.use_whisper = use_whisper and WhisperModel is not None
        self._model = None
        if use_whisper and WhisperModel is None:
            self._note = "Install faster-whisper for local STT: pip install faster-whisper"
        else:
            self._note = ""

    @property
    def note(self) -> str:
        return self._note

    def _load(self):
        if not self.use_whisper:
            return None
        if self._model is None:
            self._model = WhisperModel(self.model_name)
        return self._model

    def transcribe_file(self, audio_path: str) -> str:
        model = self._load()
        if model is None:
            return ""
        segments, _info = model.transcribe(audio_path)
        return " ".join(segment.text.strip() for segment in segments).strip()

    def transcribe_stream(self, chunks: Iterable[bytes], fallback_callable=None) -> str:
        if self.use_whisper:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
                for chunk in chunks:
                    temp.write(chunk)
                temp_path = Path(temp.name)
            try:
                return self.transcribe_file(str(temp_path))
            finally:
                temp_path.unlink(missing_ok=True)

        if callable(fallback_callable):
            return str(fallback_callable(chunks))
        return ""
