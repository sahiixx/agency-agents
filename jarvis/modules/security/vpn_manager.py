"""VPN command state wrapper."""

from __future__ import annotations


class VpnManager:
    """Track local VPN state."""

    def __init__(self) -> None:
        self.connected = False

    def connect(self) -> str:
        self.connected = True
        return "VPN connected"

    def disconnect(self) -> str:
        self.connected = False
        return "VPN disconnected"
