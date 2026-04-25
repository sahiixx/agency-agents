"""
providers/ — Unified multi-framework LLM/agent provider layer for The Agency.

Every provider exposes two things:
  get_llm(...)   → a LangChain-compatible chat model object
  run_agent(...) → a blocking call that returns a ProviderResult object

Supported providers:
  ollama     — Local Ollama models (default)
  openai     — OpenAI Agents SDK (GPT-4o, o3, etc.)
  adk        — Google Agent Development Kit
  autogen    — Microsoft AutoGen
  rasa       — Rasa Open Source (dialog + NLU)
  n8n        — n8n workflow webhook trigger
"""

from providers.base import BaseProvider, ProviderResult

__all__ = ["BaseProvider", "ProviderResult", "get_provider"]


def get_provider(name: str) -> "BaseProvider":
    """Return a provider instance by name."""
    name = name.lower()
    if name in ("anthropic", "claude"):
        from providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "ollama":
        from providers.ollama_provider import OllamaProvider
        return OllamaProvider()
    if name == "openai":
        from providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "adk":
        from providers.adk_provider import ADKProvider
        return ADKProvider()
    if name == "autogen":
        from providers.autogen_provider import AutoGenProvider
        return AutoGenProvider()
    if name == "rasa":
        from providers.rasa_provider import RasaProvider
        return RasaProvider()
    if name == "n8n":
        from providers.n8n_provider import N8NProvider
        return N8NProvider()
    raise ValueError(f"Unknown provider '{name}'. Choices: anthropic, ollama, openai, adk, autogen, rasa, n8n")
