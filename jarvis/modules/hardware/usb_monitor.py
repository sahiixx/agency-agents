"""USB monitoring placeholder."""

from __future__ import annotations


class UsbMonitor:
    """Track connected USB device names."""

    def __init__(self) -> None:
        self.devices: list[str] = []

    def connected(self, name: str) -> None:
        self.devices.append(name)
