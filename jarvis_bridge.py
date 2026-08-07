#!/usr/bin/env python3
"""
jarvis_bridge.py — JARVIS as the Agency-OS harness operator.

JARVIS (the desktop assistant stack in jarvis/) becomes the **brain, memory, and
main operator** of the Agency-OS harness:

  brain       → jarvis.modules.ai_brain.AIBrain        (Ollama LLM + keyword fallback)
  memory      → jarvis.modules.ai.persistent_memory    (SQLite at ~/.jarvis/memory.db)
  personality → jarvis.modules.ai.personality_engine   (professional / casual / ...)
  learning    → jarvis.modules.ai.learning_engine      (command usage analytics)
  routing     → jarvis.modules.ai.multi_agent          (research / coding / creative / system)

Every JARVIS component is imported lazily and wrapped in try/except so the
dashboard **never crashes** when a dependency is missing or Ollama is down —
each feature degrades to a graceful fallback instead.

Usage:
    from jarvis_bridge import get_operator
    op = get_operator()
    op.status()
    op.ask("Summarize the 2026 trends")
    op.remember("favorite_color", "blue", "preferences")
    op.recall("favorite_color")
    op.set_personality("sarcastic")

Env overrides:
    JARVIS_MODEL      — brain model name (default qwen3:8b)
    JARVIS_OLLAMA_URL — Ollama base URL  (default http://localhost:11434)
    JARVIS_MEMORY_DB  — SQLite path      (default ~/.jarvis/memory.db)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

# ── Config (env-overridable) ─────────────────────────────────────────────────
JARVIS_MODEL = os.environ.get("JARVIS_MODEL", "qwen3:8b")
JARVIS_OLLAMA_URL = os.environ.get("JARVIS_OLLAMA_URL", "http://localhost:11434")
JARVIS_MEMORY_DB = os.environ.get("JARVIS_MEMORY_DB", "~/.jarvis/memory.db")

PERSONALITY_MODES = ["professional", "casual", "sarcastic", "motivational", "teacher"]


class JarvisOperator:
    """Unified JARVIS operator for the Agency-OS harness."""

    def __init__(self) -> None:
        self.brain: Any = None
        self.memory: Any = None
        self.personality: Any = None
        self.learning: Any = None
        self.router: Any = None
        self.brain_error: Optional[str] = None
        self._load()

    # ── Lazy, crash-safe loading ──────────────────────────────────────────────
    def _load(self) -> None:
        try:
            from jarvis.modules.ai_brain import AIBrain
            self.brain = AIBrain(model=JARVIS_MODEL, base_url=JARVIS_OLLAMA_URL)
        except Exception as e:  # noqa: BLE001 — operator must never crash
            self.brain = None
            self.brain_error = f"{type(e).__name__}: {e}"

        try:
            from jarvis.modules.ai.persistent_memory import PersistentMemory
            self.memory = PersistentMemory(JARVIS_MEMORY_DB)
        except Exception as e:  # noqa: BLE001
            self.memory = None
            self.brain_error = self.brain_error or f"memory: {type(e).__name__}: {e}"

        try:
            from jarvis.modules.ai.personality_engine import PersonalityEngine
            self.personality = PersonalityEngine()
        except Exception:  # noqa: BLE001
            self.personality = None

        try:
            from jarvis.modules.ai.learning_engine import LearningEngine
            self.learning = LearningEngine()
        except Exception:  # noqa: BLE001
            self.learning = None

        try:
            from jarvis.modules.ai.multi_agent import MultiAgentRouter
            self.router = MultiAgentRouter()
        except Exception:  # noqa: BLE001
            self.router = None

    # ── Status ────────────────────────────────────────────────────────────────
    def status(self) -> dict[str, Any]:
        mem_count = 0
        mem_rows: list[dict[str, str]] = []
        if self.memory is not None:
            try:
                conn = self.memory.conn
                mem_count = conn.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
                mem_rows = [
                    {"key": k, "value": v[:80], "category": c}
                    for k, v, c in conn.execute(
                        "SELECT key, value, category FROM memory ORDER BY key LIMIT 50"
                    ).fetchall()
                ]
            except Exception:  # noqa: BLE001
                pass

        return {
            "operator": "JARVIS",
            "brain": {
                "model": JARVIS_MODEL,
                "base_url": JARVIS_OLLAMA_URL,
                "available": self.brain is not None,
                "error": self.brain_error,
            },
            "memory": {
                "db": str(Path(JARVIS_MEMORY_DB).expanduser()),
                "facts": mem_count,
                "rows": mem_rows,
            },
            "personality": {
                "mode": self.personality.mode if self.personality else "professional",
                "modes": PERSONALITY_MODES,
            },
            "learning": {
                "top_commands": self.learning.top_commands(5) if self.learning else [],
            },
        }

    # ── Brain ─────────────────────────────────────────────────────────────────
    def ask(self, prompt: str) -> dict[str, Any]:
        """Route → track → think → personality-format. Never raises."""
        route = self.router.route(prompt) if self.router else "system"
        if self.learning:
            try:
                self.learning.track(prompt)
            except Exception:  # noqa: BLE001
                pass

        if self.brain is not None:
            try:
                resp = self.brain.ask(prompt)
                text, source = resp.text, resp.source
            except Exception as e:  # noqa: BLE001
                text, source = f"Brain error: {type(e).__name__}: {e}", "error"
        else:
            text = "JARVIS brain unavailable (Ollama not reachable). " \
                   f"Start it with: ollama serve  →  {JARVIS_OLLAMA_URL}"
            source = "unavailable"

        if self.personality is not None:
            try:
                text = self.personality.format_response(text)
            except Exception:  # noqa: BLE001
                pass

        return {"reply": text, "source": source, "route": route,
                "personality": self.personality.mode if self.personality else "professional"}

    # ── Memory ───────────────────────────────────────────────────────────────
    def remember(self, key: str, value: str, category: str = "general") -> dict[str, Any]:
        if self.memory is None:
            return {"ok": False, "error": "Memory unavailable"}
        try:
            self.memory.remember(key, value, category)
            return {"ok": True, "action": "remember", "key": key}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def recall(self, key: str) -> dict[str, Any]:
        if self.memory is None:
            return {"ok": False, "error": "Memory unavailable"}
        try:
            value = self.memory.recall(key)
            return {"ok": True, "key": key, "value": value, "found": value is not None}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    def forget(self, key: str) -> dict[str, Any]:
        if self.memory is None:
            return {"ok": False, "error": "Memory unavailable"}
        try:
            self.memory.forget(key)
            return {"ok": True, "action": "forget", "key": key}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # ── Personality ───────────────────────────────────────────────────────────
    def set_personality(self, mode: str) -> dict[str, Any]:
        if self.personality is None:
            return {"ok": False, "error": "Personality engine unavailable"}
        try:
            self.personality.set_mode(mode)
            return {"ok": True, "mode": mode}
        except ValueError as e:
            return {"ok": False, "error": str(e), "modes": PERSONALITY_MODES}


# ── Singleton ─────────────────────────────────────────────────────────────────
_OPERATOR: Optional[JarvisOperator] = None


def get_operator() -> JarvisOperator:
    global _OPERATOR
    if _OPERATOR is None:
        _OPERATOR = JarvisOperator()
    return _OPERATOR


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    op = get_operator()
    print(json.dumps(op.status(), indent=2, default=str))
    print()
    print(json.dumps(op.ask("research the 2026 AI trends"), indent=2, default=str))
