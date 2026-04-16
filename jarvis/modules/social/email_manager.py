"""Email reading and draft scaffolding."""

from __future__ import annotations


class EmailManager:
    """High-level email API placeholder."""

    def read_latest(self) -> list[str]:
        return []

    def draft_reply(self, subject: str, intent: str) -> str:
        return f"Subject: Re: {subject}\n\n{intent}\n"
