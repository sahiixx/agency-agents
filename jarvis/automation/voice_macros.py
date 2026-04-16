"""Voice macro recording and playback."""

from __future__ import annotations

import json
from pathlib import Path


class VoiceMacros:
    def __init__(self):
        self.macros: dict[str, list[str]] = {}
        self._recording_name = None

    def start_recording(self, name: str):
        self._recording_name = name
        self.macros[name] = []

    def record_step(self, command: str):
        if self._recording_name:
            self.macros[self._recording_name].append(command)

    def stop_recording(self):
        self._recording_name = None

    def play(self, name: str) -> list[str]:
        return list(self.macros.get(name, []))

    def export_json(self, path: str):
        Path(path).write_text(json.dumps(self.macros, indent=2))

    def import_json(self, path: str):
        self.macros.update(json.loads(Path(path).read_text()))
