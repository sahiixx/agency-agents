"""FastAPI dashboard for JARVIS status and settings."""

from __future__ import annotations

import http.client
import json
import subprocess
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
MODULES_FILE = Path("/tmp/jarvis_modules.json")
HISTORY_FILE = Path("/tmp/jarvis_history.jsonl")
LOG_FILE = Path("/tmp/jarvis.log")

app = FastAPI(title="JARVIS Dashboard")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

MODULE_NAMES = ["ai_brain", "whisper_stt", "advanced_tts", "system_dashboard"]

# Ensure state files exist
def _init_state():
    if not MODULES_FILE.exists():
        MODULES_FILE.write_text(json.dumps({m: True for m in MODULE_NAMES}))
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("")
    if not LOG_FILE.exists():
        LOG_FILE.write_text("")

_init_state()


def _read_modules() -> dict:
    try:
        return json.loads(MODULES_FILE.read_text())
    except Exception:
        return {m: True for m in MODULE_NAMES}


def _write_modules(data: dict):
    MODULES_FILE.write_text(json.dumps(data))


def _fetch_health(url: str, timeout: float = 2.0) -> dict:
    """Simple HTTP GET using stdlib with timeout."""
    start = time.time()
    try:
        parsed = url.replace("http://", "").replace("https://", "")
        if "/" in parsed:
            host_port, path = parsed.split("/", 1)
            path = "/" + path
        else:
            host_port = parsed
            path = "/"
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 80
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="ignore")
        conn.close()
        elapsed = round((time.time() - start) * 1000, 1)
        return {
            "status": "up" if resp.status < 400 else "down",
            "code": resp.status,
            "response_time_ms": elapsed,
            "body": body[:200],
        }
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 1)
        return {"status": "down", "code": None, "response_time_ms": elapsed, "error": str(e)}


def _docker_container_status(name: str) -> dict:
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}", name],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return {"status": "down", "error": result.stderr.strip() or "not found"}
        parts = result.stdout.strip().split("|")
        state = parts[0]
        health = parts[1] if len(parts) > 1 else "none"
        return {"status": state, "health": health}
    except FileNotFoundError:
        return {"status": "unknown", "error": "docker not found"}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        name="index.html",
        context={
            "title": "JARVIS Dashboard",
            "port": 7000,
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "local_only": True}


@app.get("/api/health")
def api_health():
    endpoints = {
        "Orchestrator": "http://localhost:9000/health",
        "SAHIIX-AGI": "http://localhost:7777/health",
        "sahiixx-bus": "http://localhost:8200/",
        "goose-aios": "http://localhost:8001/",
        "codex-self": "http://localhost:9001/",
        "Open WebUI": "http://localhost:8080/",
    }
    results = {}
    for name, url in endpoints.items():
        results[name] = _fetch_health(url)
    return results


@app.get("/api/docker")
def api_docker():
    containers = ["agency-agents", "fixfizx-frontend", "fixfizx-backend", "sovereign-swarm", "ollama"]
    results = {}
    for name in containers:
        results[name] = _docker_container_status(name)
    return results


@app.get("/api/modules")
def api_modules():
    return _read_modules()


@app.post("/toggle/{module}")
def toggle_module(module: str):
    modules = _read_modules()
    if module not in modules:
        return JSONResponse(status_code=404, content={"error": f"module {module} not found"})
    modules[module] = not modules[module]
    _write_modules(modules)
    return {"module": module, "state": modules[module]}


@app.get("/api/history")
def api_history(limit: int = 50):
    lines = []
    if HISTORY_FILE.exists():
        text = HISTORY_FILE.read_text()
        for line in text.strip().split("\n"):
            if line.strip():
                try:
                    lines.append(json.loads(line))
                except Exception:
                    pass
    return lines[-limit:]


@app.get("/api/logs")
def api_logs(lines: int = 20):
    if not LOG_FILE.exists():
        return []
    text = LOG_FILE.read_text()
    all_lines = text.split("\n")
    return [ln for ln in all_lines[-lines:] if ln.strip() != ""]


@app.post("/command")
def command(payload: dict):
    cmd = payload.get("command", "").strip().lower()
    if not cmd:
        return JSONResponse(status_code=400, content={"error": "empty command"})

    tokens = cmd.split()
    action = tokens[0]
    arg = tokens[1] if len(tokens) > 1 else None

    response = {"command": cmd, "output": "", "timestamp": time.time()}

    if action == "status":
        health_data = api_health()
        docker_data = api_docker()
        up = sum(1 for v in health_data.values() if v.get("status") == "up")
        running = sum(1 for v in docker_data.values() if v.get("status") == "running")
        response["output"] = (
            f"Services up: {up}/{len(health_data)}. "
            f"Containers running: {running}/{len(docker_data)}."
        )

    elif action == "restart" and arg:
        result = subprocess.run(
            ["docker", "restart", arg],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            response["output"] = f"Restarted container: {arg}"
        else:
            # Try systemctl fallback
            result2 = subprocess.run(
                ["systemctl", "restart", arg],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result2.returncode == 0:
                response["output"] = f"Restarted service: {arg}"
            else:
                response["output"] = f"Failed to restart {arg}. docker: {result.stderr.strip() or 'n/a'}, systemctl: {result2.stderr.strip() or 'n/a'}"

    elif action == "logs" and arg:
        result = subprocess.run(
            ["docker", "logs", "--tail", "20", arg],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            response["output"] = result.stdout.strip()
        else:
            response["output"] = f"Failed to fetch logs for {arg}: {result.stderr.strip() or 'n/a'}"

    elif action == "agents":
        response["output"] = "Active agents: JARVIS, Orchestrator, SAHIIX-AGI, goose-aios, codex-self, OpenClaw, FRIDAY"

    elif action == "ping":
        response["output"] = "pong"

    else:
        response["output"] = f"Unknown command: {cmd}. Available: status, restart <svc>, logs <svc>, agents, ping"

    # Append to history
    with HISTORY_FILE.open("a") as f:
        f.write(json.dumps(response) + "\n")

    return response
