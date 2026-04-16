"""Eye tracking placeholder."""

from __future__ import annotations


class EyeTracker:
    """Track eye-aware accessibility state."""

    def __init__(self) -> None:
        self.enabled = False

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled
