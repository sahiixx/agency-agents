"""General-purpose helper utilities for JARVIS."""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any) -> Any:
    """Load JSON from path and return default on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def save_json(path: Path, payload: Any) -> None:
    """Write JSON payload to path safely."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def greeting_for_hour(hour: int | None = None) -> str:
    """Return a contextual greeting."""
    hour = datetime.now().hour if hour is None else hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def choose(items: list[str], fallback: str) -> str:
    """Choose a random item or fallback."""
    return random.choice(items) if items else fallback
