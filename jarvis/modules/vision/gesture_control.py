"""Gesture control with configurable mapping."""

from __future__ import annotations

import json
from pathlib import Path

try:
    import mediapipe as mp  # type: ignore
except Exception:  # pragma: no cover
    mp = None


class GestureControl:
    DEFAULT_MAP = {
        "thumbs_up": "confirm",
        "palm": "stop",
        "victory": "screenshot",
        "fist": "mute",
    }

    def __init__(self, mapping_file: str = "gestures.json"):
        self.mapping_file = Path(mapping_file)
        self.available = mp is not None
        self.mapping = self.DEFAULT_MAP.copy()
        if self.mapping_file.exists():
            self.mapping.update(json.loads(self.mapping_file.read_text()))

    def command_for_gesture(self, gesture: str) -> str:
        return self.mapping.get(gesture, "")

    def save_mapping(self):
        self.mapping_file.write_text(json.dumps(self.mapping, indent=2))
