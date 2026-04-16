"""Discord integration placeholder."""

from __future__ import annotations


class DiscordBot:
    """Expose a minimal relay API."""

    def send_status(self, message: str) -> dict[str, str]:
        return {"status": "queued", "message": message}
