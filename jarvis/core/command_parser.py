"""Simple voice command parser for JARVIS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ParsedCommand:
    action: str
    payload: str = ""


class CommandParser:
    """Parse spoken command phrases into structured actions."""

    def parse(self, text: str) -> ParsedCommand:
        normalized = text.strip().lower()
        if normalized.startswith("jarvis, add task:"):
            return ParsedCommand(action="todo.add", payload=text.split(":", 1)[-1].strip())
        if normalized.startswith("jarvis, what's on my todo list"):
            return ParsedCommand(action="todo.list")
        return ParsedCommand(action="chat", payload=text.strip())
