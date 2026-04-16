"""Display manager placeholder."""

from __future__ import annotations


class DisplayManager:
    """Track selected display mode."""

    def __init__(self) -> None:
        self.mode = "single"

    def set_mode(self, mode: str) -> str:
        self.mode = mode
        return self.mode
