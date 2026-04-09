"""
providers/rasa_provider.py — Rasa Open Source provider.

Sends a message to a running Rasa server and returns the NLU + dialog response.
Can also invoke a Rasa Action Server for custom actions.

Environment variables:
  RASA_URL         — Rasa server base URL (default: http://localhost:5005)
  RASA_TOKEN       — Optional auth token for the Rasa server
  RASA_SENDER_ID   — Sender ID for the conversation (default: agency)

The system_prompt is ignored here (Rasa manages dialog via .yml files);
the query is sent as a user message to the REST channel.

Install: pip install rasa
"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.parse
from typing import Any

from providers.base import BaseProvider, ProviderResult

RASA_URL       = os.getenv("RASA_URL",       "http://localhost:5005")
RASA_TOKEN     = os.getenv("RASA_TOKEN",     "")
RASA_SENDER_ID = os.getenv("RASA_SENDER_ID", "agency")


class RasaProvider(BaseProvider):
    """Rasa Open Source dialog + NLU via REST channel."""

    name = "rasa"

    def get_llm(self, **kwargs) -> Any:
        """Rasa does not expose a LangChain-compatible LLM; returns None."""
        return None

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "rasa-agent",
        sender_id:     str = RASA_SENDER_ID,
        rasa_url:      str = RASA_URL,
        **kwargs,
    ) -> ProviderResult:
        """
        Send query to a running Rasa REST channel and return the response.
        Falls back to /model/parse (NLU-only) if the dialog endpoint fails.
        """
        endpoint = f"{rasa_url.rstrip('/')}/webhooks/rest/webhook"
        payload  = json.dumps({"sender": sender_id, "message": query}).encode()
        headers  = {
            "Content-Type": "application/json",
            "User-Agent":   "TheAgency/1.0",
        }
        if RASA_TOKEN:
            headers["Authorization"] = f"Bearer {RASA_TOKEN}"

        try:
            req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            # Rasa returns a list of response objects
            texts = [msg.get("text", "") for msg in data if msg.get("text")]
            output = "\n".join(texts) if texts else json.dumps(data)
            return ProviderResult(
                output=output or "[No response from Rasa]",
                provider=self.name,
                model="rasa",
                metadata={"endpoint": endpoint},
            )
        except Exception as e:
            # Try NLU-only parse endpoint as fallback
            try:
                parse_url = f"{rasa_url.rstrip('/')}/model/parse"
                nlu_req   = urllib.request.Request(
                    parse_url,
                    data=json.dumps({"text": query}).encode(),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(nlu_req, timeout=10) as r:
                    nlu_data = json.loads(r.read().decode())
                return ProviderResult(
                    output=json.dumps(nlu_data, indent=2),
                    provider=self.name,
                    model="rasa-nlu",
                    metadata={"fallback": "nlu-parse", "original_error": str(e)},
                )
            except Exception as inner:
                return ProviderResult(
                    output="", provider=self.name, model="rasa",
                    error=(
                        f"Rasa dialog error: {e}. "
                        f"NLU fallback also failed: {inner}. "
                        f"Is Rasa running at {rasa_url}? Run: rasa run --enable-api"
                    ),
                )
