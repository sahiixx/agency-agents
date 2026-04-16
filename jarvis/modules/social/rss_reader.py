"""RSS feed reader placeholder."""

from __future__ import annotations


class RssReader:
    """Manage feed list and return static summaries."""

    def __init__(self) -> None:
        self.feeds: list[str] = []

    def subscribe(self, url: str) -> None:
        self.feeds.append(url)
