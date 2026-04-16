"""Usage analytics and pattern learning."""

from __future__ import annotations

from collections import Counter


class LearningEngine:
    """Track commands and suggest common shortcuts."""

    def __init__(self) -> None:
        self._commands: Counter[str] = Counter()

    def track(self, command: str) -> None:
        self._commands[command.lower().strip()] += 1

    def top_commands(self, limit: int = 5) -> list[tuple[str, int]]:
        return self._commands.most_common(limit)
