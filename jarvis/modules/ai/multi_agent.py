"""Task router for JARVIS specialized sub-agents."""

from __future__ import annotations


class MultiAgentRouter:
    """Route a request to a specialist label."""

    def route(self, prompt: str) -> str:
        normalized = prompt.lower()
        if any(k in normalized for k in ["research", "analyze", "search"]):
            return "research"
        if any(k in normalized for k in ["code", "debug", "fix"]):
            return "coding"
        if any(k in normalized for k in ["image", "music", "creative"]):
            return "creative"
        return "system"
