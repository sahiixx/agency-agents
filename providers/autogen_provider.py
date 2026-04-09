"""
providers/autogen_provider.py — Microsoft AutoGen provider.

Wraps AutoGen ConversableAgent so Agency missions can be run through
AutoGen's multi-agent conversation framework with --provider autogen.

Environment variables:
  OPENAI_API_KEY   — required for AutoGen's default LLM config
  AUTOGEN_MODEL    — model to use (default: gpt-4o)
  ANTHROPIC_API_KEY — if AUTOGEN_MODEL is claude-* AutoGen will use Anthropic

Install: pip install pyautogen
"""

from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any

from providers.base import BaseProvider, ProviderResult

REPO_ROOT = Path(__file__).parent.parent.resolve()

DEFAULT_MODEL = os.getenv("AUTOGEN_MODEL", "gpt-4o")


class AutoGenProvider(BaseProvider):
    """Microsoft AutoGen multi-agent conversation framework."""

    name = "autogen"

    def get_llm(self, **kwargs) -> Any:
        """AutoGen manages its own LLM; returns None (LangChain not used here)."""
        return None

    def _build_llm_config(self, model: str) -> dict:
        """Build AutoGen-compatible llm_config dict."""
        if model.startswith("claude"):
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise EnvironmentError("ANTHROPIC_API_KEY not set for AutoGen+Claude.")
            return {
                "config_list": [{"model": model, "api_key": api_key, "api_type": "anthropic"}],
                "temperature": 0.3,
            }
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY not set for AutoGen.")
        return {
            "config_list": [{"model": model, "api_key": api_key}],
            "temperature": 0.3,
        }

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "autogen-agent",
        model:         str = DEFAULT_MODEL,
        max_turns:     int = 3,
        **kwargs,
    ) -> ProviderResult:
        try:
            import autogen  # type: ignore
        except ImportError:
            return ProviderResult(
                output="", provider=self.name, model=model,
                error="pyautogen not installed. Run: pip install pyautogen",
            )
        try:
            llm_config = self._build_llm_config(model)

            assistant = autogen.ConversableAgent(
                name=agent_name,
                system_message=system_prompt,
                llm_config=llm_config,
            )
            user_proxy = autogen.ConversableAgent(
                name="agency-user-proxy",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=max_turns,
                is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
                llm_config=False,
            )

            user_proxy.initiate_chat(
                assistant,
                message=query,
                max_turns=max_turns,
            )

            # Extract last assistant message
            history = user_proxy.chat_messages.get(assistant, [])
            output = ""
            for msg in reversed(history):
                if msg.get("role") == "assistant":
                    output = msg.get("content", "")
                    break

            return ProviderResult(
                output=output or "[No assistant reply]",
                provider=self.name,
                model=model,
            )
        except Exception as e:
            return ProviderResult(
                output="", provider=self.name, model=model,
                error=f"{type(e).__name__}: {e}",
            )
