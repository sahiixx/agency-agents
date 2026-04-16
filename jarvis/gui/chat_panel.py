"""Chat history panel model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass(slots=True)
class ChatMessage:
    timestamp: str
    role: str
    text: str


@dataclass(slots=True)
class ChatPanel:
    """Store/search/export chat history."""

    history: list[ChatMessage] = field(default_factory=list)

    def add(self, role: str, text: str) -> None:
        self.history.append(ChatMessage(datetime.now().isoformat(timespec="seconds"), role, text))

    def search(self, query: str) -> list[ChatMessage]:
        q = query.lower()
        return [m for m in self.history if q in m.text.lower()]

    def export_txt(self) -> str:
        return "\n".join(f"[{m.timestamp}] {m.role}: {m.text}" for m in self.history)

    def export_json(self) -> str:
        return json.dumps([m.__dict__ for m in self.history], ensure_ascii=False, indent=2)
