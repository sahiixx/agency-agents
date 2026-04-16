"""Network scanning interface."""

from __future__ import annotations

from jarvis.utils.optional_deps import OptionalDependencyError, safe_import


class NetworkScanner:
    """Discover devices with optional scapy dependency."""

    def scan(self) -> dict[str, object]:
        try:
            safe_import("scapy", "pip install scapy")
        except OptionalDependencyError as exc:
            return {"ok": False, "devices": [], "reason": str(exc)}
        return {"ok": True, "devices": []}
