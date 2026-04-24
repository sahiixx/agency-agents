"""Local AI brain module using Ollama with keyword fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import requests  # type: ignore[import-untyped]


@dataclass
class AIResponse:
    text: str
    source: str


@dataclass
class AIBrain:
    model: str = "llama3"
    base_url: str = "http://localhost:11434"
    history: List[Dict[str, str]] = field(default_factory=list)

    KEYWORD_FALLBACKS = {
        "quantum": "Quantum computing uses qubits that can represent multiple states at once.",
        "summarize": "Please provide text to summarize.",
        "python": "I can draft Python scripts once local LLM is available.",
    }

    def ask(self, prompt: str) -> AIResponse:
        self.history.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": self.history, "stream": False}
        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {}).get("content", "")
            if message:
                self.history.append({"role": "assistant", "content": message})
                return AIResponse(text=message, source="ollama")
        except Exception:
            pass

        lowered = prompt.lower()
        for key, fallback in self.KEYWORD_FALLBACKS.items():
            if key in lowered:
                self.history.append({"role": "assistant", "content": fallback})
                return AIResponse(text=fallback, source="fallback")
        default = "Ollama is unavailable. Install and run it locally: https://ollama.com"
        self.history.append({"role": "assistant", "content": default})
        return AIResponse(text=default, source="fallback")
