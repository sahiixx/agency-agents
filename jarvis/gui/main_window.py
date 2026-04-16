"""Animated JARVIS desktop GUI (dependency-safe)."""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.utils.optional_deps import OptionalDependencyError, safe_import


@dataclass(slots=True)
class OrbState:
    mode: str = "idle"
    color: str = "#00BFFF"


class MainWindow:
    """Headless-safe GUI placeholder with state transitions."""

    def __init__(self) -> None:
        self.state = OrbState()

    def toggle_listening(self) -> str:
        if self.state.mode == "listening":
            self.state.mode = "idle"
            self.state.color = "#00BFFF"
        else:
            self.state.mode = "listening"
            self.state.color = "#00FF88"
        return self.state.mode


def create_gui() -> object | None:
    """Create a PyQt6 app if dependency exists; otherwise return None."""
    try:
        safe_import("PyQt6", "pip install PyQt6")
    except OptionalDependencyError:
        return None
    return MainWindow()
