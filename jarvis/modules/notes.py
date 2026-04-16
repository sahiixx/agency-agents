"""Voice notes storage module."""

from __future__ import annotations

from datetime import datetime

from config import DATA_DIR


class NotesModule:
    """Persist notes to text files."""

    def save_note(self, text: str) -> str:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        file_path = DATA_DIR / f"note_{datetime.now().strftime('%Y%m%d')}.txt"
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat()} - {text}\\n")
        return f"Note saved to {file_path}."
