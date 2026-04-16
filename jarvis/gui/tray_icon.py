"""System tray integration placeholder."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TrayIcon:
    """Cross-platform tray abstraction."""

    muted: bool = False
    notifications: list[str] = field(default_factory=list)

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted

    def notify(self, message: str) -> None:
        self.notifications.append(message)
