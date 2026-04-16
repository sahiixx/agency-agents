"""Current date/time information module."""

from __future__ import annotations

from datetime import datetime


class DatetimeInfo:
    """Return formatted date and time details."""

    def now(self) -> str:
        current = datetime.now()
        return current.strftime("It is %I:%M %p on %A, %B %d, %Y.")
