"""Local RAG knowledge base with graceful fallback when vector deps are unavailable."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


class KnowledgeBase:
    def __init__(self, db_path: str = "jarvis_knowledge.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY, path TEXT UNIQUE, content TEXT)"
        )
        self.conn.commit()
        self.faiss_available = faiss is not None

    def add_document(self, path: str, content: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO docs(path, content) VALUES(?, ?)", (path, content))
        self.conn.commit()

    def remove_document(self, path: str) -> None:
        self.conn.execute("DELETE FROM docs WHERE path = ?", (path,))
        self.conn.commit()

    def search(self, query: str, limit: int = 5) -> List[Tuple[str, str]]:
        rows = self.conn.execute(
            "SELECT path, content FROM docs WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def auto_index(self, roots: Iterable[Path]) -> int:
        count = 0
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() in {".txt", ".md"} and path.is_file():
                    self.add_document(str(path), path.read_text(errors="ignore"))
                    count += 1
        return count
