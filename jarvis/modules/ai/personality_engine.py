"""Dynamic personality modes for JARVIS responses."""

from __future__ import annotations

from dataclasses import dataclass


_MODE_PREFIX = {
    "professional": "Certainly.",
    "casual": "Sure thing!",
    "sarcastic": "Oh absolutely, because that sounds easy.",
    "motivational": "You've got this!",
    "teacher": "Let's break it down.",
}


@dataclass(slots=True)
class PersonalityEngine:
    mode: str = "professional"

    def set_mode(self, mode: str) -> None:
        if mode not in _MODE_PREFIX:
            raise ValueError(f"Unsupported personality mode: {mode}")
        self.mode = mode

    def format_response(self, text: str) -> str:
        return f"{_MODE_PREFIX[self.mode]} {text}"
