"""FastAPI dashboard for JARVIS status and settings."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="JARVIS Dashboard")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "request": request,
            "title": "JARVIS Dashboard",
            "modules": ["ai_brain", "whisper_stt", "advanced_tts", "system_dashboard"],
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "local_only": True}
