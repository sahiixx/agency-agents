"""
providers/ — Unified multi-framework LLM/agent provider layer for The Agency.

Every provider exposes two things:
  get_llm(...)   → a LangChain-compatible chat model object
  run_agent(...) → a blocking call that returns a ProviderResult object

CLOUD-ONLY: The Agency runs on cloud models exclusively — there is no local
model runtime. The LLM resolves to the first configured cloud provider
(Anthropic → OpenAI → Google Gemini).

Supported providers:
  anthropic  — Claude via Anthropic API (cloud, default)
  openai     — OpenAI GPT models (cloud)
  adk        — Google Agent Development Kit / Gemini (cloud)
  autogen    — Microsoft AutoGen (cloud)
  rasa       — Rasa Open Source (dialog + NLU)
  n8n        — n8n workflow webhook trigger
"""

import os
from typing import Any

from providers.base import BaseProvider, ProviderResult

__all__ = ["BaseProvider", "ProviderResult", "get_provider", "cloud_provider", "default_provider", "get_cloud_llm"]

# ── Cloud-only resolution ─────────────────────────────────────────────────────
# Ordered preference for the cloud LLM backbone. `AGENCY_PROVIDER` can override
# (e.g. AGENCY_PROVIDER=openai). No local model is ever selected implicitly.

CLOUD_PROVIDERS: tuple[tuple[str, str], ...] = (
    ("anthropic", "ANTHROPIC_API_KEY"),
    ("openai",    "OPENAI_API_KEY"),
    ("adk",       "GEMINI_API_KEY"),
)


def cloud_provider() -> str:
    """Return the first configured cloud provider name, or '' if none."""
    for name, key in CLOUD_PROVIDERS:
        if os.environ.get(key):
            return name
    return ""


def default_provider() -> str:
    """AGENCY_PROVIDER env override, else the first configured cloud provider."""
    env = os.environ.get("AGENCY_PROVIDER", "").strip().lower()
    if env:
        return "claude" if env == "anthropic" else env
    return cloud_provider()


def get_cloud_llm(provider: str = "", model: str = "", **kwargs) -> Any:
    """Cloud-only LangChain chat model factory (no local models).

    provider: 'anthropic' | 'claude' | 'openai' | 'adk' | 'autogen' — or '' for
    auto-resolution from configured API keys (Anthropic → OpenAI → Gemini).

    Raises EnvironmentError with setup guidance when no cloud key is configured.
    """
    provider = (provider or default_provider()).lower()
    if provider in ("", "auto"):
        provider = cloud_provider()
    if not provider:
        raise EnvironmentError(
            "No cloud LLM key configured. Add one of ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY in the Freebuff Keys tab, or set "
            "AGENCY_PROVIDER to pick a specific provider."
        )
    if provider in ("anthropic", "claude"):
        provider = "anthropic"
    p = get_provider(provider)
    if model:
        return p.get_llm(model=model, **kwargs)
    return p.get_llm(**kwargs)


def get_provider(name: str) -> "BaseProvider":
    """Return a provider instance by name."""
    name = name.lower()
    if name in ("anthropic", "claude"):
        from providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "openai":
        from providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "adk":
        from providers.adk_provider import ADKProvider
        return ADKProvider()
    if name == "autogen":
        from providers.autogen_provider import AutoGenProvider
        return AutoGenProvider()
    if name == "kimi":
        from providers.kimi_provider import KimiProvider
        return KimiProvider()
    if name == "rasa":
        from providers.rasa_provider import RasaProvider
        return RasaProvider()
    if name == "n8n":
        from providers.n8n_provider import N8NProvider
        return N8NProvider()
    raise ValueError(f"Unknown provider '{name}'. Choices: anthropic, claude, openai, adk, autogen, rasa, n8n, kimi")