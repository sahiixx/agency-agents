"""
providers/base.py — Abstract base class for all provider backends.

Every provider must implement:
  get_llm(**kwargs)              → a LangChain-compatible chat model, or None
  run_agent(system, query, name) → ProviderResult with .output string and metadata
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ProviderResult:
    """Standardised result returned by every provider's run_agent()."""
    output:   str
    provider: str
    model:    str              = ""
    metadata: dict             = field(default_factory=dict)
    error:    Optional[str]    = None

    @property
    def ok(self) -> bool:
        return self.error is None


class BaseProvider(ABC):
    """Base class for all LLM / agent framework providers."""

    name: str = "base"

    # ── Required interface ────────────────────────────────────────────────────

    def get_llm(self, **kwargs) -> Any:
        """Return a LangChain-compatible chat model, or None if not applicable."""
        return None

    @abstractmethod
    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "agent",
        **kwargs,
    ) -> ProviderResult:
        """Execute a single agent turn and return a ProviderResult."""

    # ── Convenience ───────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"<Provider:{self.name}>"
