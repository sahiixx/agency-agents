"""
providers/openai_provider.py — OpenAI provider (GPT-4o, o3, o1, etc.)

Uses langchain_openai.ChatOpenAI as the LLM backend so any deepagents
pipeline can swap to OpenAI models with --provider openai.

Environment variables required:
  OPENAI_API_KEY   — your OpenAI secret key

Optional:
  OPENAI_BASE_URL  — override base URL (e.g. Azure OpenAI endpoint)
  OPENAI_MODEL     — default model name (default: gpt-4o)
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

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


class OpenAIProvider(BaseProvider):
    """OpenAI GPT-4o / o3 / o1 via LangChain ChatOpenAI."""

    name = "openai"

    def get_llm(self, model: str = DEFAULT_MODEL, **kwargs):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai not installed. Run: pip install langchain-openai"
            )
        api_key  = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set.")
        extra = {"base_url": base_url} if base_url else {}
        return ChatOpenAI(model=model, api_key=api_key, **extra, **kwargs)

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "openai-agent",
        model:         str = DEFAULT_MODEL,
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
