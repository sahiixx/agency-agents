"""Background maintenance mode."""

from __future__ import annotations


class DreamMode:
    """Toggleable idle-time automation."""

    def __init__(self) -> None:
        self.enabled = False

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
