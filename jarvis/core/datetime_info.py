"""Date and time helpers."""

from __future__ import annotations

from datetime import datetime


class DateTimeInfo:
    """Expose current date/time for voice responses."""

    def now_iso(self) -> str:
        return datetime.now().isoformat(timespec="seconds")
