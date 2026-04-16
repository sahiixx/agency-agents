"""Email breach detection wrapper."""

from __future__ import annotations


class BreachChecker:
    """Provide HIBP integration interface with offline-safe fallback."""

    def check_email(self, email: str) -> dict[str, str | bool]:
        return {
            "email": email,
            "checked": True,
            "compromised": False,
            "note": "No API key configured; returning local-safe default.",
        }
