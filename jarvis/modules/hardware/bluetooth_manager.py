"""Bluetooth manager placeholder."""

from __future__ import annotations


class BluetoothManager:
    """Manage remembered bluetooth devices."""

    def __init__(self) -> None:
        self.connected: str | None = None

    def connect(self, device: str) -> None:
        self.connected = device

    def disconnect(self) -> None:
        self.connected = None
