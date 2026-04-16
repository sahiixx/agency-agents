"""Calendar integration with graceful offline fallback."""

from __future__ import annotations

import json
from pathlib import Path


class CalendarManager:
    """Store events locally when cloud integrations are unavailable."""

    def __init__(self, path: str = "~/.jarvis/calendar.json") -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def add_event(self, title: str, when: str) -> None:
        events = self.list_events()
        events.append({"title": title, "when": when})
        self.path.write_text(json.dumps(events, indent=2), encoding="utf-8")

    def list_events(self) -> list[dict[str, str]]:
        return json.loads(self.path.read_text(encoding="utf-8"))
