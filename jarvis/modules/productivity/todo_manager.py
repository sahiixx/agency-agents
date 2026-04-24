"""SQLite-backed voice todo manager."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class TodoManager:
    """Manage tasks with priority and completion status."""

    def __init__(self, db_path: str = "~/.jarvis/todo.db") -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "task TEXT NOT NULL,"
            "priority TEXT NOT NULL DEFAULT 'medium',"
            "due_date TEXT DEFAULT '',"
            "done INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        self.conn.commit()

    def add_task(self, task: str, priority: str = "medium", due_date: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO tasks(task, priority, due_date) VALUES(?,?,?)",
            (task, priority, due_date),
        )
        self.conn.commit()
        row_id = cur.lastrowid
        return int(row_id) if row_id is not None else 0

    def list_tasks(self) -> list[dict[str, str | int | bool]]:
        rows = self.conn.execute("SELECT id, task, priority, due_date, done FROM tasks ORDER BY id").fetchall()
        return [
            {"id": r[0], "task": r[1], "priority": r[2], "due_date": r[3], "done": bool(r[4])}
            for r in rows
        ]

    def mark_done(self, task_id: int) -> None:
        self.conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
        self.conn.commit()
