"""Macro recorder and replay helper."""

from __future__ import annotations

from typing import Callable


class MacroRecorder:
    """Store and replay command sequences by name."""

    def __init__(self) -> None:
        self._macros: dict[str, list[str]] = {}

    def record(self, name: str, commands: list[str]) -> None:
        """Save macro commands."""
        self._macros[name] = commands

    def replay(self, name: str, executor: Callable[[str], str]) -> list[str]:
        """Replay all commands through executor callback."""
        outputs = []
        for command in self._macros.get(name, []):
            outputs.append(executor(command))
        return outputs
