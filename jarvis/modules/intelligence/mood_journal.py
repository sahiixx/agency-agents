"""Mood logging and reporting."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class MoodJournal:
    """Persist mood snapshots to JSON."""

    def __init__(self, path: str = "~/.jarvis/mood.json") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def log(self, mood: str) -> None:
        values = json.loads(self.path.read_text(encoding="utf-8"))
        values.append({"timestamp": datetime.now().isoformat(timespec="seconds"), "mood": mood})
        self.path.write_text(json.dumps(values, indent=2), encoding="utf-8")
