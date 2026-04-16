"""Clipboard access and simple history."""

from __future__ import annotations

from collections import deque


class ClipboardManager:
    """Manage clipboard operations with history."""

    def __init__(self) -> None:
        self._history: deque[str] = deque(maxlen=20)
        self._clipboard_cache = ""

    def copy(self, text: str) -> str:
        self._clipboard_cache = text
        self._history.appendleft(text)
        return "Copied text to clipboard buffer."

    def paste(self) -> str:
        return self._clipboard_cache

    def history(self) -> list[str]:
        return list(self._history)
