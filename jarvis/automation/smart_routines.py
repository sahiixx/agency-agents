"""Context-aware automation routines."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SmartRoutine:
    name: str
    triggers: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


class SmartRoutineEngine:
    def __init__(self):
        self.routines: dict[str, SmartRoutine] = {}

    def add_routine(self, routine: SmartRoutine) -> None:
        self.routines[routine.name] = routine

    def get_actions_for_event(self, event: str) -> list[str]:
        actions = []
        for routine in self.routines.values():
            if event in routine.triggers:
                actions.extend(routine.actions)
        return actions
