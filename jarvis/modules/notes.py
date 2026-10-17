"""Voice notes storage module."""

from __future__ import annotations

from datetime import datetime

from jarvis.config import DATA_DIR


class NotesModule:
    """Persist notes to text files."""

    def save_note(self, text: str) -> str:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        now = datetime.now().astimezone()
        file_path = DATA_DIR / f"note_{now.strftime('%Y%m%d')}.txt"
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{now.isoformat()} - {text}\n")
        return f"Note saved to {file_path}."
