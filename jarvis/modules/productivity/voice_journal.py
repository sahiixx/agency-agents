"""Markdown voice journal entries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class VoiceJournal:
    """Persist transcribed daily journal entries."""

    def __init__(self, root: str = "~/Documents/JARVIS/Journal") -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def add_entry(self, text: str, mood: str = "neutral") -> Path:
        stamp = datetime.now()
        target = self.root / f"{stamp:%Y-%m-%d}.md"
        with target.open("a", encoding="utf-8") as fp:
            fp.write(f"\n## {stamp:%H:%M:%S} [{mood}]\n{text}\n")
        return target
