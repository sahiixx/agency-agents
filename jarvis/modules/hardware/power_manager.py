"""Power management placeholder."""

from __future__ import annotations


class PowerManager:
    """Toggle simple power-saving state."""

    def __init__(self) -> None:
        self.power_saving = False

    def set_power_saving(self, enabled: bool) -> None:
        self.power_saving = enabled
