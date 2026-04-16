"""Reminder scheduling module."""

from __future__ import annotations

import threading


class ReminderModule:
    """Set timed reminders with callback notifications."""

    def __init__(self) -> None:
        self.reminders: list[str] = []

    def set_reminder(self, seconds: int, message: str, callback) -> str:
        """Set reminder after N seconds and notify through callback."""
        self.reminders.append(message)

        def _notify() -> None:
            callback(f"Reminder: {message}")

        timer = threading.Timer(max(1, seconds), _notify)
        timer.daemon = True
        timer.start()
        return f"Reminder set for {seconds} seconds from now."
