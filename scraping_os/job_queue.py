#!/usr/bin/env python3
"""
scraping_os/job_queue.py — Persistent job queue for scraping tasks.

JSON-backed queue with status tracking, pause/resume, and result storage.

Usage:
    queue = JobQueue("jobs.json")
    job_id = queue.add("product_scraper", {"url": "https://example.com", "selector": ".product"})
    queue.start(job_id)
    # ... run scraper ...
    queue.complete(job_id, results=[...])
"""

from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


class JobStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    name: str
    engine: str  # "crawlee" | "scrapling" | "auto"
    config: dict[str, Any]
    status: str = JobStatus.QUEUED.value
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    results: list[dict] = field(default_factory=list)
    error: str | None = None
    items_scraped: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        return cls(**data)


class JobQueue:
    """
    Persistent JSON-backed job queue.

    Usage:
        queue = JobQueue("data/jobs.json")
        job = queue.add("my_scraper", "scrapling", {"url": "..."})
        queue.start(job.id)
        queue.complete(job.id, results=[...])
    """

    def __init__(self, path: str | Path = "data/jobs.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.jobs = {jid: Job.from_dict(j) for jid, j in data.items()}

    def _save(self):
        self.path.write_text(json.dumps({jid: j.to_dict() for jid, j in self.jobs.items()}, indent=2))

    def add(self, name: str, engine: str, config: dict[str, Any]) -> Job:
        """Add a new job to the queue."""
        job = Job(
            id=str(uuid.uuid4())[:8],
            name=name,
            engine=engine,
            config=config,
        )
        self.jobs[job.id] = job
        self._save()
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def start(self, job_id: str):
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.RUNNING.value
            job.started_at = time.time()
            self._save()

    def pause(self, job_id: str):
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.PAUSED.value
            self._save()

    def complete(self, job_id: str, results: list[dict] | None = None):
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.DONE.value
            job.completed_at = time.time()
            if results:
                job.results = results
                job.items_scraped = len(results)
            self._save()

    def fail(self, job_id: str, error: str):
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.FAILED.value
            job.completed_at = time.time()
            job.error = error
            self._save()

    def list_all(self) -> list[Job]:
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)

    def list_by_status(self, status: JobStatus) -> list[Job]:
        return [j for j in self.list_all() if j.status == status.value]

    def clear_completed(self):
        to_remove = [jid for jid, j in self.jobs.items() if j.status in (JobStatus.DONE.value, JobStatus.FAILED.value)]
        for jid in to_remove:
            del self.jobs[jid]
        self._save()

    def stats(self) -> dict[str, int]:
        return {
            "total": len(self.jobs),
            "queued": len(self.list_by_status(JobStatus.QUEUED)),
            "running": len(self.list_by_status(JobStatus.RUNNING)),
            "paused": len(self.list_by_status(JobStatus.PAUSED)),
            "done": len(self.list_by_status(JobStatus.DONE)),
            "failed": len(self.list_by_status(JobStatus.FAILED)),
        }
