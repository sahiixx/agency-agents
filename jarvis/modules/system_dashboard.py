"""System metrics collection with alerting and SQLite persistence."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

try:
    import GPUtil  # type: ignore
except Exception:  # pragma: no cover
    GPUtil = None


@dataclass
class MetricSnapshot:
    cpu: float
    ram: float
    disk: float


class SystemDashboard:
    def __init__(self, db_path: str = "jarvis_metrics.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics(
                ts REAL,
                cpu REAL,
                ram REAL,
                disk REAL,
                gpu REAL
            )
            """
        )
        self.conn.commit()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def snapshot(self) -> MetricSnapshot:
        return MetricSnapshot(
            cpu=psutil.cpu_percent(interval=0.1),
            ram=psutil.virtual_memory().percent,
            disk=psutil.disk_usage("/").percent,
        )

    def alert_messages(self) -> list[str]:
        snap = self.snapshot()
        alerts = []
        if snap.cpu > 90:
            alerts.append("High CPU usage")
        if snap.ram > 85:
            alerts.append("High RAM usage")
        if snap.disk > 95:
            alerts.append("High disk usage")
        return alerts

    def _save(self):
        snap = self.snapshot()
        gpu = 0.0
        if GPUtil:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0].load * 100
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO metrics(ts, cpu, ram, disk, gpu)
                VALUES(?, ?, ?, ?, ?)
                """,
                (time.time(), snap.cpu, snap.ram, snap.disk, gpu),
            )
            self.conn.commit()

    def start(self, interval_seconds: int = 5):
        if self._thread and self._thread.is_alive():
            return

        def run():
            while not self._stop.is_set():
                self._save()
                self._stop.wait(interval_seconds)

        self._stop.clear()
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
