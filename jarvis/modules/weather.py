"""Weather lookup module."""

from __future__ import annotations

import requests  # type: ignore[import-untyped]


class WeatherModule:
    """Fetch current weather by city using wttr.in."""

    def current_weather(self, city: str) -> str:
        try:
            response = requests.get(f"https://wttr.in/{city}?format=3", timeout=10)
            if response.ok:
                return response.text.strip()
            return f"Could not fetch weather for {city}."
        except Exception as exc:
            return f"Weather lookup failed: {exc}"
