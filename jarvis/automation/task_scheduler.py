"""Recurring task scheduler for JARVIS automation."""

from __future__ import annotations

import threading
import time
from typing import Callable

from utils.logger import setup_logger

try:
    import schedule  # type: ignore
except Exception:  # pragma: no cover
    schedule = None


class TaskScheduler:
    """Runs scheduled tasks in a background thread."""

    def __init__(self) -> None:
        self.logger = setup_logger("jarvis.task_scheduler")
        self._running = False
        self._thread: threading.Thread | None = None

    def every_minutes(self, minutes: int, func: Callable[[], None]) -> bool:
        """Schedule task every N minutes."""
        if schedule is None:
            return False
        schedule.every(max(1, minutes)).minutes.do(func)
        return True

    def start(self) -> None:
        """Start scheduler loop."""
        if schedule is None or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            try:
                schedule.run_pending()
            except Exception as exc:
                self.logger.exception("Scheduled task failed: %s", exc)
            time.sleep(1)

    def stop(self) -> None:
        """Stop scheduler loop."""
        self._running = False
