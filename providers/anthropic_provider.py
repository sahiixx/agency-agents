"""
providers/anthropic_provider.py — Legacy Claude (Anthropic) provider wrapper.

Thin wrapper around ChatAnthropic + deepagents flow for backward compatibility.
Default model is overridable via the ANTHROPIC_MODEL env var (e.g. claude-sonnet-5).
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

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")


class AnthropicProvider(BaseProvider):
    """Claude via Anthropic API — the default cloud provider."""

    name = "anthropic"

    def get_llm(self, model: str = ANTHROPIC_MODEL, **kwargs):
        from langchain_anthropic import ChatAnthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Add it in the Freebuff Keys tab."
            )
        base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
        extra = {"base_url": base_url} if base_url else {}
        return ChatAnthropic(model=model, api_key=api_key, **extra, **kwargs)

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "claude-agent",
        model:         str = ANTHROPIC_MODEL,
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
