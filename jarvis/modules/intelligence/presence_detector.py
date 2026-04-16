"""Presence and attention state."""

from __future__ import annotations


class PresenceDetector:
    """Track whether user is present at desk."""

    def __init__(self) -> None:
        self.present = True

    def set_present(self, value: bool) -> None:
        self.present = value

    def status(self) -> str:
        return "present" if self.present else "away"
