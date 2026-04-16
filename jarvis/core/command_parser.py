"""Command parser with v2 intent matching + v3 convenience accessors."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

try:
    from config import COMMANDS_FILE  # type: ignore
    from utils.helpers import load_json  # type: ignore
except Exception:  # pragma: no cover
    from jarvis.config import COMMANDS_FILE
    from jarvis.utils.helpers import load_json

try:
    from fuzzywuzzy import process  # type: ignore
except Exception:  # pragma: no cover
    process = None


@dataclass(slots=True)
class ParsedCommand:
    intent: str
    action: str
    command: str
    score: int
    payload: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class CommandParser:
    """Parse free-form text into intent metadata."""

    def __init__(self) -> None:
        self.registry = load_json(COMMANDS_FILE, {"intents": []})

    def parse(self, text: str) -> ParsedCommand:
        cleaned = text.strip()
        normalized = cleaned.lower()
        if normalized.startswith("jarvis, add task:"):
            return ParsedCommand(
                intent="todo",
                action="todo.add",
                command=text,
                score=100,
                payload=cleaned.split(":", 1)[-1].strip(),
            )
        if normalized.startswith("jarvis, what's on my todo list"):
            return ParsedCommand(intent="todo", action="todo.list", command=text, score=100)
        if not normalized:
            return ParsedCommand(intent="unknown", action="none", command=text, score=0)

        intents = self.registry.get("intents", [])
        for intent in intents:
            for keyword in intent.get("keywords", []):
                if keyword in normalized:
                    return ParsedCommand(
                        intent=intent.get("name", "unknown"),
                        action=intent.get("action", "none"),
                        command=text,
                        score=100,
                    )

        candidates: dict[str, dict[str, Any]] = {}
        for intent in intents:
            for keyword in intent.get("keywords", []):
                candidates[keyword] = intent
        if not candidates:
            return ParsedCommand(intent="chat", action="chat", command=text, score=50, payload=cleaned)

        if process is not None:
            match = process.extractOne(normalized, list(candidates.keys()))
            if match:
                matched_keyword, score = match
                if score >= 60:
                    intent = candidates[matched_keyword]
                    return ParsedCommand(
                        intent=intent.get("name", "unknown"),
                        action=intent.get("action", "none"),
                        command=text,
                        score=int(score),
                    )
        else:
            matches = difflib.get_close_matches(normalized, list(candidates.keys()), n=1, cutoff=0.6)
            if matches:
                intent = candidates[matches[0]]
                return ParsedCommand(
                    intent=intent.get("name", "unknown"),
                    action=intent.get("action", "none"),
                    command=text,
                    score=60,
                )

        return ParsedCommand(intent="unknown", action="none", command=text, score=0, payload=cleaned)
