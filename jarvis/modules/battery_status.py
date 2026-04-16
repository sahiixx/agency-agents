"""Battery status module."""

from __future__ import annotations

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


class BatteryStatus:
    """Check battery percentage and charging state."""

    def status(self) -> str:
        if psutil is None:
            return "psutil is not available."
        battery = psutil.sensors_battery()
        if battery is None:
            return "No battery detected."
        plugged = "charging" if battery.power_plugged else "on battery"
        return f"Battery is at {battery.percent:.0f}% and {plugged}."
