#!/usr/bin/env python3
"""
api_server.py — Real Scraping OS Backend

FastAPI + SQLite + Real execution. Not a prototype.

Run:
    source .venv/bin/activate
    python3 api_server.py

Then open http://localhost:8000/
"""

from __future__ import annotations
import json
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = Path("data/scraping_os.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Database ─────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            engine TEXT NOT NULL,
            url TEXT NOT NULL,
            selector TEXT,
            status TEXT DEFAULT 'queued',
            created_at REAL,
            started_at REAL,
            completed_at REAL,
            results TEXT,
            error TEXT,
            items_scraped INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS proxies (
            id TEXT PRIMARY KEY,
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            location TEXT,
            proxy_type TEXT DEFAULT 'http',
            status TEXT DEFAULT 'active',
            failures INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            source TEXT,
            data TEXT,
            scraped_at REAL
        )
    """)
    # Seed default proxies
    c.execute("SELECT COUNT(*) FROM proxies")
    if c.fetchone()[0] == 0:
        defaults = [
            ("us-proxy-1.example.com", 8080, "US-East", "residential"),
            ("eu-proxy-1.example.com", 3128, "EU-West", "datacenter"),
            ("asia-proxy-1.example.com", 8080, "SG", "residential"),
            ("rotating.example.com", 443, "Global", "rotating"),
        ]
        for host, port, loc, ptype in defaults:
            c.execute(
                "INSERT INTO proxies (id, host, port, location, proxy_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4())[:8], host, port, loc, ptype, "active")
            )
    conn.commit()
    conn.close()


def db_exec(sql: str, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(sql, params)
    if fetch:
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    conn.commit()
    rowid = c.lastrowid
    conn.close()
    return rowid


# ── Pydantic Models ──────────────────────────────────────────────────────────

class CreateJob(BaseModel):
    name: str
    engine: str  # crawlee | scrapling | auto
    url: str
    selector: str | None = None
    max_requests: int = 20


class CreateProxy(BaseModel):
    host: str
    port: int
    location: str = ""
    proxy_type: str = "http"


# ── FastAPI ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Scraping OS API", lifespan=lifespan)


# ── Frontend (served at root) ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse(content=open(Path(__file__).parent / "real_dashboard.html").read())


# ── Jobs API ─────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs():
    jobs = db_exec("SELECT * FROM jobs ORDER BY created_at DESC", fetch=True)
    for j in jobs:
        j["results"] = json.loads(j["results"]) if j["results"] else []
    return {"jobs": jobs}


@app.post("/api/jobs")
def create_job(payload: CreateJob):
    job_id = str(uuid.uuid4())[:8]
    db_exec(
        "INSERT INTO jobs (id, name, engine, url, selector, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (job_id, payload.name, payload.engine, payload.url, payload.selector, "queued", time.time())
    )
    return {"id": job_id, "status": "queued"}


@app.post("/api/jobs/{job_id}/run")
def run_job(job_id: str):
    job = db_exec("SELECT * FROM jobs WHERE id = ?", (job_id,), fetch=True)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    job = job[0]
    db_exec("UPDATE jobs SET status = ?, started_at = ? WHERE id = ?", ("running", time.time(), job_id))

    # Run the actual scrape in a subprocess so it doesn't block
    # We'll use a simple Python script that tries scrapling first, then falls back to urllib
    script = f'''
import json, sys, time
url = {repr(job["url"])}
selector = {repr(job["selector"])}
engine = {repr(job["engine"])}

results = []
error = None

# Try scrapling first
try:
    from scrapling.fetchers import Fetcher
    page = Fetcher.fetch(url)
    if selector:
        items = page.css(selector)
        for item in items[:20]:
            data = {{"_source": url, "_timestamp": time.time()}}
            text = item.css("::text").get()
            if text:
                data["text"] = text.strip()[:200]
            href = item.css("a::attr(href)").get()
            if href:
                data["link"] = href
            results.append(data)
    else:
        results.append({{"_source": url, "title": page.css("title::text").get()}})
except Exception as e:
    error = str(e)
    # Fallback: basic urllib + regex
    try:
        import urllib.request, re
        req = urllib.request.Request(url, headers={{"User-Agent": "Mozilla/5.0"}})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I)
        results.append({{"_source": url, "title": title.group(1) if title else None, "html_length": len(html)}})
    except Exception as e2:
        error += " | Fallback failed: " + str(e2)

output = {{"results": results, "error": error, "count": len(results)}}
print(json.dumps(output))
'''

    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            output = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            output = {"results": [], "error": proc.stderr or "No output", "count": 0}

        results = output.get("results", [])
        error = output.get("error")

        # Save results
        db_exec(
            "UPDATE jobs SET status = ?, completed_at = ?, results = ?, error = ?, items_scraped = ? WHERE id = ?",
            ("done" if not error else "failed", time.time(), json.dumps(results), error, len(results), job_id)
        )
        for r in results:
            db_exec(
                "INSERT INTO results (job_id, source, data, scraped_at) VALUES (?, ?, ?, ?)",
                (job_id, r.get("_source", job["url"]), json.dumps(r), time.time())
            )

        return {"id": job_id, "status": "done" if not error else "failed", "items": len(results), "error": error}

    except subprocess.TimeoutExpired:
        db_exec("UPDATE jobs SET status = ?, error = ? WHERE id = ?", ("failed", "Timeout", job_id))
        return {"id": job_id, "status": "failed", "error": "Timeout"}


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    db_exec("DELETE FROM jobs WHERE id = ?", (job_id,))
    db_exec("DELETE FROM results WHERE job_id = ?", (job_id,))
    return {"deleted": True}


# ── Proxies API ──────────────────────────────────────────────────────────────

@app.get("/api/proxies")
def list_proxies():
    return {"proxies": db_exec("SELECT * FROM proxies", fetch=True)}


@app.post("/api/proxies")
def add_proxy(payload: CreateProxy):
    pid = str(uuid.uuid4())[:8]
    db_exec(
        "INSERT INTO proxies (id, host, port, location, proxy_type, status) VALUES (?, ?, ?, ?, ?, ?)",
        (pid, payload.host, payload.port, payload.location, payload.proxy_type, "active")
    )
    return {"id": pid}


@app.delete("/api/proxies/{proxy_id}")
def delete_proxy(proxy_id: str):
    db_exec("DELETE FROM proxies WHERE id = ?", (proxy_id,))
    return {"deleted": True}


# ── Results API ──────────────────────────────────────────────────────────────

@app.get("/api/results")
def list_results(job_id: str | None = None):
    if job_id:
        rows = db_exec("SELECT * FROM results WHERE job_id = ? ORDER BY scraped_at DESC", (job_id,), fetch=True)
    else:
        rows = db_exec("SELECT * FROM results ORDER BY scraped_at DESC LIMIT 100", fetch=True)
    for r in rows:
        r["data"] = json.loads(r["data"])
    return {"results": rows}


# ── Stats ────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    jobs = db_exec("SELECT status, COUNT(*) as c FROM jobs GROUP BY status", fetch=True)
    total_results = db_exec("SELECT COUNT(*) as c FROM results", fetch=True)[0]["c"]
    proxies = db_exec("SELECT COUNT(*) as c FROM proxies WHERE status = 'active'", fetch=True)[0]["c"]
    return {
        "jobs": {j["status"]: j["c"] for j in jobs},
        "total_results": total_results,
        "active_proxies": proxies,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  🚀 SCRAPING OS API — REAL BACKEND")
    print("  " + "=" * 50)
    print("  Docs:    http://localhost:8000/docs")
    print("  Dashboard: http://localhost:8000/")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
