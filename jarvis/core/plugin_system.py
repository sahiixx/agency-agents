"""Simple plugin registry."""

from __future__ import annotations

from collections.abc import Callable


class PluginSystem:
    """Register and run lightweight command plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, Callable[[], str]] = {}

    def register(self, name: str, callback: Callable[[], str]) -> None:
        self._plugins[name] = callback

    def run(self, name: str) -> str:
        return self._plugins[name]()
