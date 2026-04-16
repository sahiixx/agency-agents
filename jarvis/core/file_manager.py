"""File operations for JARVIS automation."""

from __future__ import annotations

from pathlib import Path


class FileManager:
    """Minimal file helper API."""

    def create_text_file(self, path: str, content: str) -> Path:
        target = Path(path).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target
