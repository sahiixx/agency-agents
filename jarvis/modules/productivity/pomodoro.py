"""Pomodoro timer model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PomodoroTimer:
    work_minutes: int = 25
    break_minutes: int = 5
    sessions_completed: int = 0

    def start_focus(self) -> str:
        return f"Focus time started for {self.work_minutes} minutes."

    def start_break(self) -> str:
        self.sessions_completed += 1
        return f"Take a break for {self.break_minutes} minutes."
