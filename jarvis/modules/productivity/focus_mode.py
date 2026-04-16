"""Deep focus mode state."""

from __future__ import annotations


class FocusMode:
    """Track focus mode activation."""

    def __init__(self) -> None:
        self.active = False

    def enter(self) -> str:
        self.active = True
        return "Focus mode enabled"

    def exit(self) -> str:
        self.active = False
        return "Focus mode disabled"
