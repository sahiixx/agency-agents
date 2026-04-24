"""Clipboard utilities with AI transformations."""

from __future__ import annotations

from collections import deque
from typing import Any

try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover
    pyperclip = None

from .ai_brain import AIBrain


class ClipboardAI:
    def __init__(self, brain: AIBrain, max_history: int = 50):
        self.brain = brain
        self.history: deque[str] = deque(maxlen=max_history)

    def read_clipboard(self) -> str:
        if pyperclip is None:
            return "Install pyperclip for clipboard support: pip install pyperclip"
        text = pyperclip.paste()
        if text:
            self.history.appendleft(text)
        return text

    def summarize_latest(self) -> str:
        text = self.read_clipboard()
        return self.brain.ask(f"Summarize this:\n{text}").text if text else ""
