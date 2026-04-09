"""
providers/adk_provider.py — Google Agent Development Kit (ADK) provider.

Wraps Google ADK Python so any Agency pipeline can delegate to Gemini-powered
ADK agents with --provider adk.

Environment variables required:
  GOOGLE_API_KEY   — your Google AI Studio / Vertex API key
  OR
  GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION

Optional:
  ADK_MODEL        — model name (default: gemini-2.0-flash)

ADK install: pip install google-adk
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

DEFAULT_ADK_MODEL = os.getenv("ADK_MODEL", "gemini-2.0-flash")


class ADKProvider(BaseProvider):
    """Google ADK — Gemini-powered agent runtime."""

    name = "adk"

    def get_llm(self, model: str = DEFAULT_ADK_MODEL, **kwargs):
        """Return a LangChain-compatible Gemini chat model via langchain-google-genai."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain-google-genai not installed. Run: pip install langchain-google-genai"
            )
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key and not os.environ.get("GOOGLE_GENAI_USE_VERTEXAI"):
            raise EnvironmentError(
                "GOOGLE_API_KEY not set. "
                "Get one at https://aistudio.google.com/apikey "
                "or set GOOGLE_GENAI_USE_VERTEXAI=true for Vertex AI."
            )
        extra = {"google_api_key": api_key} if api_key else {}
        return ChatGoogleGenerativeAI(model=model, **extra, **kwargs)

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "adk-agent",
        model:         str = DEFAULT_ADK_MODEL,
        **kwargs,
    ) -> ProviderResult:
        """
        Run an ADK-style agent turn.

        First tries the native Google ADK SDK (google.adk.agents.LlmAgent).
        Falls back to a plain LangChain ChatGoogleGenerativeAI call if ADK
        is not installed, so the provider remains useful without ADK.
        """
        try:
            import google.adk.agents as adk_agents  # type: ignore
            import google.adk.runners as adk_runners  # type: ignore
            import asyncio

            root_agent = adk_agents.LlmAgent(
                name=agent_name,
                model=model,
                description=agent_name,
                instruction=system_prompt,
            )
            runner = adk_runners.Runner(
                agent=root_agent,
                app_name="agency",
                session_service=adk_runners.sessions.InMemorySessionService(),
            )
            session_id = "agency-session"

            async def _run():
                from google.genai import types as genai_types
                content = genai_types.Content(
                    role="user",
                    parts=[genai_types.Part(text=query)],
                )
                final = ""
                async for event in runner.run_async(
                    user_id="agency", session_id=session_id, new_message=content
                ):
                    if event.is_final_response() and event.content and event.content.parts:
                        final = event.content.parts[0].text or ""
                return final

            output = asyncio.run(_run())
            return ProviderResult(output=output, provider=self.name, model=model)

        except ImportError:
            # ADK not installed — fall back to plain LangChain Gemini call
            try:
                from langchain_core.messages import SystemMessage, HumanMessage
                llm      = self.get_llm(model=model)
                messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]
                resp     = llm.invoke(messages)
                output   = resp.content if hasattr(resp, "content") else str(resp)
                return ProviderResult(
                    output=output, provider=self.name, model=model,
                    metadata={"fallback": "langchain-google-genai (ADK SDK not installed)"},
                )
            except Exception as inner:
                return ProviderResult(
                    output="", provider=self.name, model=model,
                    error=f"{type(inner).__name__}: {inner}",
                )
        except Exception as e:
            return ProviderResult(
                output="", provider=self.name, model=model,
                error=f"{type(e).__name__}: {e}",
            )
