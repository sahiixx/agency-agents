"""
providers/ollama_provider.py — Local Ollama provider for offline/private models.

Uses langchain_ollama.ChatOllama as the LLM backend.
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

from providers.base import BaseProvider, ProviderResult

REPO_ROOT = Path(__file__).parent.parent.resolve()
SDK_PATH  = REPO_ROOT / "deepagents" / "libs" / "deepagents"
for p in (str(SDK_PATH), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


class OllamaProvider(BaseProvider):
    """Local Ollama models (llama3.1, mistral, qwen2, etc.)."""

    name = "ollama"

    def get_llm(self, model: str = "llama3.1", base_url: str = "http://localhost:11434", **kwargs):
        try:
            from langchain_ollama import ChatOllama
        except ImportError:
            raise ImportError("langchain-ollama not installed. Run: pip install langchain-ollama")
        # The ollama Python client (used internally by ChatOllama) respects
        # OLLAMA_HOST env var. Ensure it is set so the client does not try
        # IPv6 localhost first and hang indefinitely.
        os.environ.setdefault("OLLAMA_HOST", base_url)
        return ChatOllama(model=model, base_url=base_url, **kwargs)

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "ollama-agent",
        model:         str = "llama3.1",
        base_url:      str = "http://localhost:11434",
        **kwargs,
    ) -> ProviderResult:
        try:
            from deepagents import create_deep_agent
            from langchain_core.messages import HumanMessage
            llm   = self.get_llm(model=model, base_url=base_url)
            agent = create_deep_agent(
                model=llm, tools=[], system_prompt=system_prompt, name=agent_name
            )
            resp = agent.invoke(
                {"messages": [HumanMessage(content=query)]},
                config={"recursion_limit": 50},
            )
            output = resp["messages"][-1].content
            return ProviderResult(output=output, provider=self.name, model=model)
        except Exception as e:
            return ProviderResult(
                output="", provider=self.name, model=model,
                error=f"{type(e).__name__}: {e}",
            )
