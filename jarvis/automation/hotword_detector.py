"""Wake word detector for 'Hey JARVIS'."""

from __future__ import annotations

from config import WAKE_WORD


class HotwordDetector:
    """Simple wake-word detection utility."""

    def is_wake_word_present(self, text: str) -> bool:
        """Return True when command includes wake word."""
        normalized = text.lower().strip()
        return normalized.startswith(WAKE_WORD) or normalized.startswith("hey jarvis")
