"""Live captions placeholder."""

from __future__ import annotations


class RealTimeCaptions:
    """Track live captions state."""

    def __init__(self) -> None:
        self.active = False

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False
