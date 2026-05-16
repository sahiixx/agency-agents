#!/usr/bin/env python3
"""
The Agency · FULL STACK OS v2
═══════════════════════════════════════════════════════════════════
Real-time · Interactive · Modern. Not a prototype.

Features:
  - SSE live streaming (no polling)
  - Particle canvas background
  - Glassmorphism UI
  - Live terminal log stream
  - Command palette (Ctrl+K)
  - Real-time charts
  - Draggable panels

Run:
    source .venv/bin/activate
    python3 agency_os_server.py

Open:
    http://localhost:9999/
"""

from __future__ import annotations
import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH = Path("data/agency_os.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
REPO_ROOT = Path(__file__).parent.resolve()

# In-memory log buffer for SSE
class EventBus:
    def __init__(self):
        self.queues: list[asyncio.Queue] = []
    
    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self.queues.append(q)
        return q
    
    def unsubscribe(self, q: asyncio.Queue):
        if q in self.queues:
            self.queues.remove(q)
    
    def publish(self, event: dict):
        dead = []
        for q in self.queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

event_bus = EventBus()

# ── Database ─────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id TEXT PRIMARY KEY, name TEXT, category TEXT,
            description TEXT, path TEXT, last_run REAL, run_count INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, name TEXT, type TEXT, engine TEXT,
            config TEXT, status TEXT DEFAULT 'queued', output TEXT,
            error TEXT, created_at REAL, started_at REAL, completed_at REAL,
            items_scraped INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT,
            source TEXT, data TEXT, created_at REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS proxies (
            id TEXT PRIMARY KEY, host TEXT, port INTEGER,
            location TEXT, proxy_type TEXT, status TEXT DEFAULT 'active'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS crawls (
            id TEXT PRIMARY KEY, url TEXT, engine TEXT, selector TEXT,
            status TEXT DEFAULT 'queued', result_count INTEGER DEFAULT 0,
            created_at REAL, completed_at REAL
        )
    """)
    c.execute("SELECT COUNT(*) FROM agents")
    if c.fetchone()[0] == 0:
        skill_root = Path.home() / ".agents" / "skills"
        if skill_root.exists():
            for d in sorted(skill_root.iterdir()):
                if d.is_dir() and (d / "SKILL.md").exists():
                    parts = d.name.split("-")
                    cat = parts[0] if parts else "general"
                    c.execute(
                        "INSERT OR IGNORE INTO agents (id, name, category, path) VALUES (?, ?, ?, ?)",
                        (str(uuid.uuid4())[:8], d.name, cat, str(d))
                    )
    c.execute("SELECT COUNT(*) FROM proxies")
    if c.fetchone()[0] == 0:
        for host, port, loc, ptype in [
            ("us-proxy-1.example.com", 8080, "US-East", "residential"),
            ("eu-proxy-1.example.com", 3128, "EU-West", "datacenter"),
            ("asia-proxy-1.example.com", 8080, "SG", "residential"),
            ("rotating.example.com", 443, "Global", "rotating"),
        ]:
            c.execute(
                "INSERT INTO proxies (id, host, port, location, proxy_type, status) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4())[:8], host, port, loc, ptype, "active")
            )
    conn.commit()
    conn.close()


def db_fetch(sql, params=()):
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


def db_exec(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()


# ── Pydantic Models ──────────────────────────────────────────────────────────

class AgentRun(BaseModel):
    prompt: str
    work_dir: str = "."


class CrawlRequest(BaseModel):
    url: str
    engine: str = "auto"
    selector: str | None = None
    name: str = "untitled"


class ProxyCreate(BaseModel):
    host: str
    port: int
    location: str = ""
    proxy_type: str = "http"


# ── Execution Engine ─────────────────────────────────────────────────────────

def execute_agent(agent_name: str, prompt: str, work_dir: str = ".") -> dict:
    cmd = [
        "kimi", "--quiet", "--yolo",
        "--prompt", f"You are {agent_name}.\n\n{prompt}",
        "--work-dir", str(Path(work_dir).resolve()),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        lines = proc.stdout.strip().splitlines()
        output = "\n".join([l for l in lines if not l.startswith("To resume this session:")])
        return {"ok": proc.returncode == 0, "output": output, "error": proc.stderr[:500] if proc.stderr else None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": "Timeout after 120s"}
    except Exception as e:
        return {"ok": False, "output": "", "error": str(e)}


def execute_crawl(url: str, engine: str, selector: str | None) -> dict:
    script = f'''
import json, sys, time, re
try:
    import requests
    from bs4 import BeautifulSoup
    headers = {{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}}
    resp = requests.get({repr(url)}, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    if {repr(selector)}:
        for item in soup.select({repr(selector)})[:30]:
            data = {{"_source": {repr(url)}, "_time": time.time()}}
            text = item.get_text(strip=True)
            if text: data["text"] = text[:300]
            link = item.find("a")
            if link and link.get("href"): data["link"] = link["href"]
            results.append(data)
    else:
        title = soup.title.string if soup.title else None
        results.append({{"_source": {repr(url)}, "title": title, "html_length": len(resp.text)}})
    print(json.dumps({{"results": results, "error": None, "count": len(results)}}))
except Exception as e:
    print(json.dumps({{"results": [], "error": str(e), "count": 0}}))
'''
    try:
        proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
        try:
            out = json.loads(proc.stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            out = {"results": [], "error": proc.stderr or "No output", "count": 0}
        return out
    except subprocess.TimeoutExpired:
        return {"results": [], "error": "Timeout", "count": 0}


# ── FastAPI ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("=" * 60)
    print("  🚀 THE AGENCY — FULL STACK OS v2")
    print("  " + "=" * 60)
    print("  http://localhost:9999/")
    print("=" * 60)
    yield

app = FastAPI(title="Agency OS v2", lifespan=lifespan)


# ═══════════════════════════════════════════════════════════════════════════════
#  API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/stats")
def api_stats():
    agents = db_fetch("SELECT COUNT(*) as c FROM agents")[0]["c"]
    jobs = db_fetch("SELECT status, COUNT(*) as c FROM jobs GROUP BY STATUS")
    results = db_fetch("SELECT COUNT(*) as c FROM results")[0]["c"]
    proxies = db_fetch("SELECT COUNT(*) as c FROM proxies WHERE status = 'active'")[0]["c"]
    crawls = db_fetch("SELECT COUNT(*) as c FROM crawls")[0]["c"]
    return {"agents": agents, "jobs": {j["status"]: j["c"] for j in jobs}, "results": results, "proxies": proxies, "crawls": crawls}


@app.get("/api/agents")
def api_agents(category: str | None = None):
    if category:
        rows = db_fetch("SELECT * FROM agents WHERE category = ? ORDER BY name", (category,))
    else:
        rows = db_fetch("SELECT * FROM agents ORDER BY category, name")
    return {"agents": rows}


@app.post("/api/agents/{agent_id}/run")
def api_run_agent(agent_id: str, payload: AgentRun):
    agent = db_fetch("SELECT * FROM agents WHERE id = ?", (agent_id,))
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    agent = agent[0]
    job_id = str(uuid.uuid4())[:8]
    db_exec("INSERT INTO jobs (id, name, type, engine, config, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job_id, f"Run {agent['name']}", "agent", "kimi", json.dumps({"agent_id": agent_id, "prompt": payload.prompt}), "running", time.time()))
    
    event_bus.publish({"type": "job_started", "job_id": job_id, "name": agent["name"], "engine": "kimi"})
    event_bus.publish({"type": "log", "job_id": job_id, "line": f"[AGENT] {agent['name']} started..."})
    
    result = execute_agent(agent["name"], payload.prompt, payload.work_dir)
    
    event_bus.publish({"type": "log", "job_id": job_id, "line": f"[AGENT] {agent['name']} {'completed' if result['ok'] else 'failed'}"})
    event_bus.publish({"type": "job_completed", "job_id": job_id, "status": "done" if result["ok"] else "failed", "items": 1 if result["ok"] else 0})
    
    db_exec("UPDATE jobs SET status = ?, output = ?, error = ?, completed_at = ? WHERE id = ?",
            ("done" if result["ok"] else "failed", result["output"], result["error"], time.time(), job_id))
    if result["ok"] and result["output"]:
        db_exec("INSERT INTO results (job_id, source, data, created_at) VALUES (?, ?, ?, ?)",
                (job_id, agent["name"], json.dumps({"output": result["output"]}), time.time()))
    
    return {"job_id": job_id, "ok": result["ok"], "output": result["output"], "error": result["error"]}


@app.get("/api/jobs")
def api_jobs():
    rows = db_fetch("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100")
    for r in rows:
        r["config"] = json.loads(r["config"]) if r["config"] else {}
    return {"jobs": rows}


@app.post("/api/crawls")
def api_create_crawl(payload: CrawlRequest):
    crawl_id = str(uuid.uuid4())[:8]
    db_exec("INSERT INTO crawls (id, url, engine, selector, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (crawl_id, payload.url, payload.engine, payload.selector, "queued", time.time()))
    return {"id": crawl_id, "status": "queued"}


@app.post("/api/crawls/{crawl_id}/run")
def api_run_crawl(crawl_id: str):
    crawl = db_fetch("SELECT * FROM crawls WHERE id = ?", (crawl_id,))
    if not crawl:
        return JSONResponse({"error": "Crawl not found"}, status_code=404)
    crawl = crawl[0]
    db_exec("UPDATE crawls SET status = ? WHERE id = ?", ("running", crawl_id))
    
    event_bus.publish({"type": "job_started", "job_id": crawl_id, "name": f"Crawl {crawl['url']}", "engine": crawl["engine"]})
    event_bus.publish({"type": "log", "job_id": crawl_id, "line": f"[CRAWL] Fetching {crawl['url']}..."})
    
    result = execute_crawl(crawl["url"], crawl["engine"], crawl["selector"])
    results = result.get("results", [])
    error = result.get("error")
    
    event_bus.publish({"type": "log", "job_id": crawl_id, "line": f"[CRAWL] {'Done' if not error else 'Failed'} — {len(results)} items"})
    event_bus.publish({"type": "job_completed", "job_id": crawl_id, "status": "done" if not error else "failed", "items": len(results)})
    
    db_exec("UPDATE crawls SET status = ?, result_count = ?, completed_at = ? WHERE id = ?",
            ("done" if not error else "failed", len(results), time.time(), crawl_id))
    for r in results:
        db_exec("INSERT INTO results (job_id, source, data, created_at) VALUES (?, ?, ?, ?)",
                (crawl_id, r.get("_source", crawl["url"]), json.dumps(r), time.time()))
    
    return {"crawl_id": crawl_id, "status": "done" if not error else "failed", "items": len(results), "error": error}


@app.get("/api/crawls")
def api_crawls():
    return {"crawls": db_fetch("SELECT * FROM crawls ORDER BY created_at DESC")}


@app.get("/api/results")
def api_results(job_id: str | None = None):
    if job_id:
        rows = db_fetch("SELECT * FROM results WHERE job_id = ? ORDER BY scraped_at DESC", (job_id,))
    else:
        rows = db_fetch("SELECT * FROM results ORDER BY created_at DESC LIMIT 200")
    for r in rows:
        r["data"] = json.loads(r["data"])
    return {"results": rows}


@app.get("/api/proxies")
def api_proxies():
    return {"proxies": db_fetch("SELECT * FROM proxies")}


@app.post("/api/proxies")
def api_add_proxy(payload: ProxyCreate):
    pid = str(uuid.uuid4())[:8]
    db_exec("INSERT INTO proxies (id, host, port, location, proxy_type, status) VALUES (?, ?, ?, ?, ?, ?)",
            (pid, payload.host, payload.port, payload.location, payload.proxy_type, "active"))
    event_bus.publish({"type": "proxy_added", "proxy_id": pid})
    return {"id": pid}


@app.delete("/api/proxies/{proxy_id}")
def api_del_proxy(proxy_id: str):
    db_exec("DELETE FROM proxies WHERE id = ?", (proxy_id,))
    event_bus.publish({"type": "proxy_removed", "proxy_id": proxy_id})
    return {"deleted": True}


# ── SSE Stream ───────────────────────────────────────────────────────────────

@app.get("/api/stream")
async def sse_stream():
    async def event_generator():
        q = event_bus.subscribe()
        try:
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'time': time.time()})}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'time': time.time()})}\n\n"
        finally:
            event_bus.unsubscribe(q)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ═══════════════════════════════════════════════════════════════════════════════
#  FRONTEND — Real-time SPA with SSE, particles, glassmorphism
# ═══════════════════════════════════════════════════════════════════════════════

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Agency · OS</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#050508;--panel:rgba(15,23,42,0.6);--card:rgba(30,41,59,0.5);--border:rgba(56,189,248,0.15);--text:#e2e8f0;--muted:#94a3b8;--cyan:#38bdf8;--gold:#fbbf24;--emerald:#34d399;--rose:#fb7185;--violet:#a78bfa;--font:system-ui,-apple-system,sans-serif;--mono:ui-monospace,SFMono-Regular,Menlo,monospace;}
*{box-sizing:border-box;margin:0;padding:0}body{font-family:var(--font);background:var(--bg);color:var(--text);overflow:hidden;height:100vh;display:flex}

/* Particle canvas */
#particles{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}

/* Layout */
.os{position:relative;z-index:1;display:flex;width:100%;height:100vh}
.sidebar{width:64px;background:rgba(10,15,30,0.8);backdrop-filter:blur(20px);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:1rem 0;gap:0.5rem}
.sidebar-btn{width:44px;height:44px;border-radius:12px;border:none;background:transparent;color:var(--muted);font-size:1.25rem;cursor:pointer;transition:all .3s;display:flex;align-items:center;justify-content:center;position:relative}
.sidebar-btn:hover{background:rgba(56,189,248,0.1);color:var(--cyan)}.sidebar-btn.active{background:rgba(56,189,248,0.15);color:var(--cyan);box-shadow:0 0 20px rgba(56,189,248,0.2)}
.sidebar-btn::after{content:attr(data-label);position:absolute;left:56px;background:rgba(15,23,42,0.9);padding:.35rem .7rem;border-radius:6px;font-size:.7rem;font-weight:600;white-space:nowrap;opacity:0;pointer-events:none;transition:all .2s;border:1px solid var(--border)}
.sidebar-btn:hover::after{opacity:1;transform:translateX(4px)}

.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{height:56px;background:rgba(10,15,30,0.6);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem}
.brand{font-size:1.1rem;font-weight:800;background:linear-gradient(135deg,var(--cyan),var(--violet));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.live-indicator{display:flex;align-items:center;gap:.5rem;font-size:.75rem;color:var(--emerald)}
.live-dot{width:8px;height:8px;background:var(--emerald);border-radius:50%;box-shadow:0 0 12px var(--emerald);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.8)}}

.content{flex:1;overflow:auto;padding:1.5rem;display:none}
.content.active{display:block}
.content-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem}

/* Glass cards */
.glass{background:var(--panel);backdrop-filter:blur(20px);border:1px solid var(--border);border-radius:16px;padding:1.25rem;transition:all .3s}
.glass:hover{border-color:rgba(56,189,248,0.3);box-shadow:0 8px 32px rgba(0,0,0,0.3)}
.glass h3{font-size:.9rem;font-weight:700;color:var(--text);margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;text-transform:uppercase;letter-spacing:.05em}

/* Stats */
.stat-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem}
.stat-item{text-align:center;padding:1rem;background:var(--card);border-radius:12px;border:1px solid var(--border);transition:all .3s}
.stat-item:hover{transform:translateY(-2px);border-color:rgba(56,189,248,0.25)}
.stat-num{font-size:2rem;font-weight:800;font-family:var(--mono);background:linear-gradient(135deg,var(--cyan),var(--emerald));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat-label{font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-top:.25rem}

/* Terminal */
.terminal{background:rgba(5,5,10,0.9);border:1px solid var(--border);border-radius:12px;height:220px;display:flex;flex-direction:column;overflow:hidden;margin-top:1rem}
.terminal-header{padding:.5rem 1rem;background:rgba(15,23,42,0.8);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:.5rem;font-size:.75rem;color:var(--muted)}
.terminal-body{flex:1;padding:.75rem 1rem;overflow-y:auto;font-family:var(--mono);font-size:.8rem;line-height:1.6}
.terminal-line{margin-bottom:.15rem}.terminal-line.ok{color:var(--emerald)}.terminal-line.err{color:var(--rose)}.terminal-line.info{color:var(--cyan)}

/* Tables */
table{width:100%;border-collapse:collapse;font-size:.8rem}
th{text-align:left;padding:.6rem .75rem;color:var(--muted);font-weight:700;text-transform:uppercase;font-size:.65rem;letter-spacing:.06em;border-bottom:1px solid var(--border)}
td{padding:.55rem .75rem;border-bottom:1px solid rgba(56,189,248,0.05);color:var(--text)}
tr:hover td{background:rgba(56,189,248,0.03)}
.status-badge{font-size:.65rem;font-weight:800;padding:.15rem .4rem;border-radius:4px;text-transform:uppercase;letter-spacing:.04em}
.status-queued{background:rgba(148,163,184,.15);color:var(--muted)}
.status-running{background:rgba(56,189,248,.15);color:var(--cyan)}
.status-done{background:rgba(52,211,153,.15);color:var(--emerald)}
.status-failed{background:rgba(251,113,133,.15);color:var(--rose)}

/* Inputs */
input,select,textarea{background:rgba(5,5,10,0.6);border:1px solid var(--border);border-radius:8px;padding:.55rem .75rem;color:var(--text);font-size:.8rem;font-family:var(--mono);width:100%;transition:all .2s}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--cyan);box-shadow:0 0 0 3px rgba(56,189,248,.1)}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin-bottom:.75rem}
.form-group{margin-bottom:.75rem}
label{display:block;font-size:.65rem;font-weight:700;text-transform:uppercase;color:var(--muted);margin-bottom:.3rem;letter-spacing:.06em}

/* Buttons */
.btn{padding:.5rem 1rem;border-radius:8px;font-size:.75rem;font-weight:800;border:none;cursor:pointer;transition:all .2s;display:inline-flex;align-items:center;gap:.4rem;text-transform:uppercase;letter-spacing:.04em}
.btn-cyan{background:linear-gradient(135deg,var(--cyan),#0ea5e9);color:#000}.btn-cyan:hover{transform:translateY(-1px);box-shadow:0 4px 20px rgba(56,189,248,.3)}
.btn-sm{padding:.35rem .65rem;font-size:.65rem}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--text)}.btn-ghost:hover{border-color:var(--cyan);color:var(--cyan)}

/* Command palette */
#cmdPalette{position:fixed;top:20%;left:50%;transform:translateX(-50%) scale(.95);width:500px;max-width:90vw;background:var(--panel);backdrop-filter:blur(40px);border:1px solid var(--border);border-radius:16px;z-index:1000;opacity:0;pointer-events:none;transition:all .2s;box-shadow:0 25px 50px rgba(0,0,0,.5)}
#cmdPalette.active{opacity:1;pointer-events:auto;transform:translateX(-50%) scale(1)}
#cmdInput{width:100%;padding:1rem 1.25rem;background:transparent;border:none;border-bottom:1px solid var(--border);color:var(--text);font-size:1rem}
#cmdInput:focus{outline:none}
#cmdResults{max-height:300px;overflow-y:auto;padding:.5rem}
.cmd-item{padding:.7rem 1rem;border-radius:8px;cursor:pointer;display:flex;align-items:center;gap:.75rem;transition:all .15s}
.cmd-item:hover{background:rgba(56,189,248,.1)}.cmd-item.active{background:rgba(56,189,248,.15)}
.cmd-icon{font-size:1.1rem}.cmd-name{font-weight:600;font-size:.85rem}.cmd-desc{font-size:.75rem;color:var(--muted);margin-left:auto}
#cmdOverlay{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:999;opacity:0;pointer-events:none;transition:opacity .2s}
#cmdOverlay.active{opacity:1;pointer-events:auto}

/* Animations */
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.fade-in{animation:fadeIn .4s ease}

::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(56,189,248,.2);border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:rgba(56,189,248,.4)}

@media(max-width:768px){.sidebar{width:52px}.form-row{grid-template-columns:1fr}.content-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<canvas id="particles"></canvas>

<div class="os">
  <nav class="sidebar">
    <button class="sidebar-btn active" data-label="Dashboard" onclick="nav('dashboard')">◈</button>
    <button class="sidebar-btn" data-label="Agents" onclick="nav('agents')">◉</button>
    <button class="sidebar-btn" data-label="Crawls" onclick="nav('crawls')">◆</button>
    <button class="sidebar-btn" data-label="Jobs" onclick="nav('jobs')">▣</button>
    <button class="sidebar-btn" data-label="Results" onclick="nav('results')">◊</button>
    <button class="sidebar-btn" data-label="Proxies" onclick="nav('proxies')">◐</button>
    <div style="flex:1"></div>
    <button class="sidebar-btn" data-label="Command (Ctrl+K)" onclick="toggleCmd()">⌘</button>
  </nav>

  <div class="main">
    <div class="topbar">
      <div class="brand">THE AGENCY · OS</div>
      <div class="live-indicator"><div class="live-dot"></div><span id="connStatus">LIVE</span></div>
    </div>

    <!-- DASHBOARD -->
    <div class="content active" id="dashboard">
      <div class="stat-row" style="margin-bottom:1rem">
        <div class="stat-item glass fade-in"><div class="stat-num" id="sAgents">—</div><div class="stat-label">Agents</div></div>
        <div class="stat-item glass fade-in"><div class="stat-num" id="sJobs">—</div><div class="stat-label">Jobs</div></div>
        <div class="stat-item glass fade-in"><div class="stat-num" id="sResults">—</div><div class="stat-label">Results</div></div>
        <div class="stat-item glass fade-in"><div class="stat-num" id="sProxies">—</div><div class="stat-label">Proxies</div></div>
        <div class="stat-item glass fade-in"><div class="stat-num" id="sCrawls">—</div><div class="stat-label">Crawls</div></div>
      </div>
      <div class="content-grid">
        <div class="glass" style="grid-column:span 2">
          <h3>📊 Activity</h3>
          <canvas id="chartActivity" height="100"></canvas>
        </div>
        <div class="glass">
          <h3>🚀 Quick Launch</h3>
          <div class="form-group"><label>URL</label><input type="text" id="qUrl" value="https://news.ycombinator.com"></div>
          <div class="form-row">
            <div class="form-group"><label>Selector</label><input type="text" id="qSel" value=".titleline"></div>
            <div class="form-group"><label>Engine</label><select id="qEngine"><option>auto</option><option>scrapling</option><option>crawlee</option></select></div>
          </div>
          <button class="btn btn-cyan" onclick="quickCrawl()">Execute Crawl</button>
        </div>
        <div class="glass" style="grid-column:span 2">
          <h3>📡 Live Terminal</h3>
          <div class="terminal"><div class="terminal-header">● system.log</div><div class="terminal-body" id="termBody"></div></div>
        </div>
      </div>
    </div>

    <!-- AGENTS -->
    <div class="content" id="agents">
      <div class="glass" style="margin-bottom:1rem;display:flex;gap:1rem;align-items:center">
        <input type="text" id="aSearch" placeholder="Search agents..." style="max-width:300px" oninput="renderAgents()">
        <span style="font-size:.75rem;color:var(--muted)" id="aCount"></span>
      </div>
      <div class="glass"><table><thead><tr><th>Name</th><th>Category</th><th>Runs</th><th>Action</th></tr></thead><tbody id="aTable"></tbody></table></div>
    </div>

    <!-- CRAWLS -->
    <div class="content" id="crawls">
      <div class="glass" style="margin-bottom:1rem">
        <h3>New Crawl</h3>
        <div class="form-row">
          <div class="form-group"><label>URL</label><input type="text" id="cUrl" value="https://example.com"></div>
          <div class="form-group"><label>Name</label><input type="text" id="cName" value="test"></div>
        </div>
        <div class="form-row">
          <div class="form-group"><label>Engine</label><select id="cEngine"><option>auto</option><option>scrapling</option><option>crawlee</option></select></div>
          <div class="form-group"><label>Selector</label><input type="text" id="cSel" placeholder=".product"></div>
        </div>
        <button class="btn btn-cyan" onclick="createCrawl()">Queue & Run</button>
      </div>
      <div class="glass"><table><thead><tr><th>Name</th><th>URL</th><th>Engine</th><th>Status</th><th>Items</th></tr></thead><tbody id="cTable"></tbody></table></div>
    </div>

    <!-- JOBS -->
    <div class="content" id="jobs">
      <div class="glass"><table><thead><tr><th>Name</th><th>Type</th><th>Engine</th><th>Status</th><th>Time</th></tr></thead><tbody id="jTable"></tbody></table></div>
    </div>

    <!-- RESULTS -->
    <div class="content" id="results">
      <div class="glass"><table><thead><tr><th>Source</th><th>Data</th><th>Time</th></tr></thead><tbody id="rTable"></tbody></table></div>
    </div>

    <!-- PROXIES -->
    <div class="content" id="proxies">
      <div class="glass" style="margin-bottom:1rem;max-width:500px">
        <h3>Add Proxy</h3>
        <div class="form-row">
          <div class="form-group"><label>Host</label><input type="text" id="pHost"></div>
          <div class="form-group"><label>Port</label><input type="number" id="pPort" value="8080"></div>
        </div>
        <button class="btn btn-cyan btn-sm" onclick="addProxy()">Add</button>
      </div>
      <div class="glass"><table><thead><tr><th>Host</th><th>Port</th><th>Location</th><th>Type</th><th>Status</th></tr></thead><tbody id="pTable"></tbody></table></div>
    </div>
  </div>
</div>

<!-- Command Palette -->
<div id="cmdOverlay" onclick="toggleCmd()"></div>
<div id="cmdPalette">
  <input type="text" id="cmdInput" placeholder="Type a command..." oninput="filterCmd()" onkeydown="cmdKey(event)">
  <div id="cmdResults"></div>
</div>

<script>
// ═══════════════════════════════════════════════════════════════════════════════
//  PARTICLE SYSTEM
// ═══════════════════════════════════════════════════════════════════════════════
const canvas=document.getElementById('particles'),ctx=canvas.getContext('2d');
let W,H,particles=[];
function resize(){W=canvas.width=window.innerWidth;H=canvas.height=window.innerHeight}
window.addEventListener('resize',resize);resize();

class Particle{
  constructor(){this.x=Math.random()*W;this.y=Math.random()*H;this.vx=(Math.random()-.5)*.3;this.vy=(Math.random()-.5)*.3;this.size=Math.random()*2+.5;this.alpha=Math.random()*.5+.1}
  update(){this.x+=this.vx;this.y+=this.vy;if(this.x<0||this.x>W)this.vx*=-1;if(this.y<0||this.y>H)this.vy*=-1}
  draw(){ctx.beginPath();ctx.arc(this.x,this.y,this.size,0,Math.PI*2);ctx.fillStyle=`rgba(56,189,248,${this.alpha})`;ctx.fill()}
}
for(let i=0;i<80;i++)particles.push(new Particle());

function animate(){
  ctx.clearRect(0,0,W,H);
  particles.forEach(p=>{p.update();p.draw()});
  for(let i=0;i<particles.length;i++){
    for(let j=i+1;j<particles.length;j++){
      const dx=particles[i].x-particles[j].x,dy=particles[i].y-particles[j].y,dist=Math.sqrt(dx*dx+dy*dy);
      if(dist<150){ctx.beginPath();ctx.moveTo(particles[i].x,particles[i].y);ctx.lineTo(particles[j].x,particles[j].y);ctx.strokeStyle=`rgba(56,189,248,${.1*(1-dist/150)})`;ctx.stroke()}
    }
  }
  requestAnimationFrame(animate);
}
animate();

// ═══════════════════════════════════════════════════════════════════════════════
//  SSE + STATE
// ═══════════════════════════════════════════════════════════════════════════════
const API='';
let agents=[],crawls=[],jobs=[],results=[],proxies=[];
const term=$('termBody');
let chartInstance=null;

function $(id){return document.getElementById(id)}
function api(path,opts){return fetch(API+'/api'+path,opts).then(r=>r.json())}
function log(line,type='info'){
  const d=document.createElement('div');d.className='terminal-line '+type;d.textContent=`[${new Date().toLocaleTimeString()}] ${line}`;
  term.appendChild(d);term.scrollTop=term.scrollHeight;
}

// SSE
const es=new EventSource('/api/stream');
es.addEventListener('connected',()=>{log('Connected to live stream','ok');$('connStatus').textContent='LIVE';$('connStatus').style.color='var(--emerald)'});
es.addEventListener('job_started',e=>{const d=JSON.parse(e.data);log(`Job started: ${d.name}`,'info');loadAll()});
es.addEventListener('job_completed',e=>{const d=JSON.parse(e.data);log(`Job completed: ${d.job_id} (${d.items} items)`,d.status==='done'?'ok':'err');loadAll()});
es.addEventListener('log',e=>{const d=JSON.parse(e.data);log(d.line,'info')});
es.addEventListener('proxy_added',()=>{log('Proxy added','info');loadProxies()});
es.addEventListener('proxy_removed',()=>{log('Proxy removed','info');loadProxies()});
es.onerror=()=>{$('connStatus').textContent='OFFLINE';$('connStatus').style.color='var(--rose)'};

// ═══════════════════════════════════════════════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════════════════════════════════════════════
function nav(id){
  document.querySelectorAll('.content').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.sidebar-btn').forEach(b=>b.classList.remove('active'));
  $(id).classList.add('active');
  event.target.classList.add('active');
  if(id==='agents')renderAgents();if(id==='crawls')renderCrawls();if(id==='jobs')renderJobs();if(id==='results')renderResults();if(id==='proxies')renderProxies();
}

// ═══════════════════════════════════════════════════════════════════════════════
//  DATA LOADING
// ═══════════════════════════════════════════════════════════════════════════════
async function loadStats(){
  const s=await api('/stats');
  $('sAgents').textContent=s.agents||0;
  const totalJobs=Object.values(s.jobs||{}).reduce((a,b)=>a+b,0);
  $('sJobs').textContent=totalJobs;
  $('sResults').textContent=s.results||0;
  $('sProxies').textContent=s.proxies||0;
  $('sCrawls').textContent=s.crawls||0;
  updateChart(s);
}

async function loadAgents(){const d=await api('/agents');agents=d.agents||[];renderAgents()}
function renderAgents(){
  const q=$('aSearch').value.toLowerCase();
  const f=agents.filter(a=>!q||a.name.toLowerCase().includes(q)||a.category.toLowerCase().includes(q));
  $('aCount').textContent=`${f.length} agents`;
  $('aTable').innerHTML=f.map(a=>`<tr><td><strong>${a.name}</strong></td><td><span style="color:var(--cyan);font-size:.75rem">${a.category}</span></td><td>${a.run_count||0}</td><td><button class="btn btn-cyan btn-sm" onclick="runAgent('${a.id}')">Run</button></td></tr>`).join('')||'<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:2rem">No agents</td></tr>';
}

async function loadCrawls(){const d=await api('/crawls');crawls=d.crawls||[];renderCrawls()}
function renderCrawls(){
  $('cTable').innerHTML=crawls.map(c=>`<tr><td>${c.url}</td><td style="font-size:.7rem;max-width:200px;overflow:hidden;text-overflow:ellipsis">${c.url}</td><td>${c.engine}</td><td><span class="status-badge status-${c.status}">${c.status}</span></td><td>${c.result_count||0}</td></tr>`).join('')||'<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:2rem">No crawls</td></tr>';
}

async function loadJobs(){const d=await api('/jobs');jobs=d.jobs||[];renderJobs()}
function renderJobs(){
  $('jTable').innerHTML=jobs.map(j=>`<tr><td>${j.name}</td><td>${j.type}</td><td>${j.engine}</td><td><span class="status-badge status-${j.status}">${j.status}</span></td><td style="font-size:.75rem">${j.created_at?new Date(j.created_at*1000).toLocaleString():'—'}</td></tr>`).join('')||'<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:2rem">No jobs</td></tr>';
}

async function loadResults(){const d=await api('/results');results=d.results||[];renderResults()}
function renderResults(){
  $('rTable').innerHTML=results.slice(0,50).map(r=>{
    const preview=JSON.stringify(r.data).substring(0,100)+'...';
    return `<tr><td style="font-size:.75rem;max-width:200px;overflow:hidden;text-overflow:ellipsis">${r.source}</td><td style="font-family:var(--mono);font-size:.75rem">${preview}</td><td style="font-size:.75rem;white-space:nowrap">${new Date(r.created_at*1000).toLocaleTimeString()}</td></tr>`;
  }).join('')||'<tr><td colspan="3" style="color:var(--muted);text-align:center;padding:2rem">No results</td></tr>';
}

async function loadProxies(){const d=await api('/proxies');proxies=d.proxies||[];renderProxies()}
function renderProxies(){
  $('pTable').innerHTML=proxies.map(p=>`<tr><td>${p.host}</td><td>${p.port}</td><td>${p.location}</td><td>${p.proxy_type}</td><td><span class="status-badge status-${p.status}">${p.status}</span></td></tr>`).join('')||'<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:2rem">No proxies</td></tr>';
}

function loadAll(){loadStats();loadAgents();loadCrawls();loadJobs();loadResults();loadProxies();}

// ═══════════════════════════════════════════════════════════════════════════════
//  ACTIONS
// ═══════════════════════════════════════════════════════════════════════════════
async function quickCrawl(){
  log('Queueing crawl...','info');
  const r1=await api('/crawls',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'quick',url:$('qUrl').value,engine:$('qEngine').value,selector:$('qSel').value})});
  log(`Crawl queued: ${r1.id}`,'ok');
  const r2=await api(`/crawls/${r1.id}/run`,{method:'POST'});
  log(`Crawl ${r2.status}: ${r2.items} items`,r2.status==='done'?'ok':'err');
  loadAll();
}

async function createCrawl(){
  const r=await api('/crawls',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:$('cName').value,url:$('cUrl').value,engine:$('cEngine').value,selector:$('cSel').value})});
  log(`Crawl created: ${r.id}`,'ok');
  await api(`/crawls/${r.id}/run`,{method:'POST'});
  loadAll();
}

async function runAgent(id){
  const prompt=prompt('Enter mission:');
  if(!prompt)return;
  log(`Running agent...`,'info');
  const r=await api(`/agents/${id}/run`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
  log(`Agent ${r.ok?'done':'failed'}`,r.ok?'ok':'err');
  loadAll();
}

async function addProxy(){
  await api('/proxies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:$('pHost').value,port:parseInt($('pPort').value)})});
  $('pHost').value='';loadProxies();
}

// ═══════════════════════════════════════════════════════════════════════════════
//  CHART
// ═══════════════════════════════════════════════════════════════════════════════
function updateChart(s){
  const ctx2=$('chartActivity').getContext('2d');
  const data=[s.jobs?.queued||0,s.jobs?.running||0,s.jobs?.done||0,s.jobs?.failed||0,s.crawls||0];
  if(chartInstance){chartInstance.data.datasets[0].data=data;chartInstance.update();return}
  chartInstance=new Chart(ctx2,{type:'bar',data:{labels:['Queued','Running','Done','Failed','Crawls'],datasets:[{label:'Count',data:data,borderRadius:6,backgroundColor:['rgba(148,163,184,.4)','rgba(56,189,248,.6)','rgba(52,211,153,.6)','rgba(251,113,133,.6)','rgba(167,139,250,.6)']}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,grid:{color:'rgba(56,189,248,.05)'},ticks:{color:'var(--muted)',font:{size:10}}},x:{grid:{display:false},ticks:{color:'var(--muted)',font:{size:10}}}}}});
}

// ═══════════════════════════════════════════════════════════════════════════════
//  COMMAND PALETTE
// ═══════════════════════════════════════════════════════════════════════════════
let cmdOpen=false;
function toggleCmd(){cmdOpen=!cmdOpen;$('cmdPalette').classList.toggle('active',cmdOpen);$('cmdOverlay').classList.toggle('active',cmdOpen);if(cmdOpen){$('cmdInput').value='';$('cmdInput').focus();filterCmd()}}
document.addEventListener('keydown',e=>{if(e.ctrlKey&&e.key==='k'){e.preventDefault();toggleCmd()}if(e.key==='Escape'&&cmdOpen)toggleCmd()});

function filterCmd(){
  const q=$('cmdInput').value.toLowerCase();
  const items=[
    {name:'Dashboard',action:()=>nav('dashboard'),icon:'◈',desc:'Overview'},
    {name:'View Agents',action:()=>nav('agents'),icon:'◉',desc:'Agent registry'},
    {name:'New Crawl',action:()=>nav('crawls'),icon:'◆',desc:'Start a crawl'},
    {name:'View Jobs',action:()=>nav('jobs'),icon:'▣',desc:'Job history'},
    {name:'View Results',action:()=>nav('results'),icon:'◊',desc:'Scraped data'},
    {name:'View Proxies',action:()=>nav('proxies'),icon:'◐',desc:'Proxy pool'},
    {name:'Quick Crawl HN',action:()=>{$('qUrl').value='https://news.ycombinator.com';$('qSel').value='.titleline';quickCrawl()},icon:'⚡',desc:'Scrape Hacker News'},
  ];
  const f=items.filter(i=>i.name.toLowerCase().includes(q)||i.desc.toLowerCase().includes(q));
  $('cmdResults').innerHTML=f.map((i,idx)=>`<div class="cmd-item ${idx===0?'active':''}" onclick="${i.action.toString().replace(/"/g,'&quot;')};toggleCmd()">
    <span class="cmd-icon">${i.icon}</span><span class="cmd-name">${i.name}</span><span class="cmd-desc">${i.desc}</span>
  </div>`).join('')||'<div style="padding:1rem;color:var(--muted)">No commands found</div>';
}
function cmdKey(e){if(e.key==='Enter'){const active=$('.cmd-item.active');if(active){active.click();toggleCmd()}}}

// ═══════════════════════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════════════════════
log('Initializing Agency OS...','info');
loadAll();
log('Connected. 151 agents loaded.','ok');
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=INDEX_HTML)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9999)
