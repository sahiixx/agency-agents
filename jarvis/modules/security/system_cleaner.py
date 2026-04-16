"""Cross-platform system cleanup helper."""

from __future__ import annotations

from pathlib import Path


class SystemCleaner:
    """Clean temporary files from safe directories."""

    def clean_temp(self, temp_root: str = "~/.jarvis/tmp") -> int:
        root = Path(temp_root).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        removed = 0
        for child in root.glob("*"):
            if child.is_file():
                child.unlink(missing_ok=True)
                removed += 1
        return removed
