"""SQLite-backed long-term memory for JARVIS."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class PersistentMemory:
    """Store and retrieve user facts by key/category."""

    def __init__(self, db_path: str = "~/.jarvis/memory.db") -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS memory (key TEXT PRIMARY KEY, value TEXT, category TEXT)"
        )
        self.conn.commit()

    def remember(self, key: str, value: str, category: str = "general") -> None:
        self.conn.execute(
            "INSERT INTO memory(key, value, category) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category",
            (key, value, category),
        )
        self.conn.commit()

    def recall(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM memory WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def forget(self, key: str) -> None:
        self.conn.execute("DELETE FROM memory WHERE key = ?", (key,))
        self.conn.commit()
