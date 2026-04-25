"""
providers/anthropic_provider.py — Legacy Claude (Anthropic) provider wrapper.

Thin wrapper around ChatAnthropic + deepagents flow for backward compatibility.
Default model now uses Ollama-style settings via OLLAMA_BASE_URL.
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

OLLAMA_MODEL = "llama3.1"


class AnthropicProvider(BaseProvider):
    """Claude via Anthropic API — legacy provider."""

    name = "anthropic"

    def get_llm(self, model: str = OLLAMA_MODEL, **kwargs):
        from langchain_anthropic import ChatAnthropic
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        if not base_url:
            raise EnvironmentError("OLLAMA_BASE_URL not set.")
        return ChatAnthropic(model=model, base_url=base_url, **kwargs)

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "claude-agent",
        model:         str = OLLAMA_MODEL,
        **kwargs,
    ) -> ProviderResult:
        try:
            from deepagents import create_deep_agent
            from langchain_core.messages import HumanMessage
            llm   = self.get_llm(model=model)
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
