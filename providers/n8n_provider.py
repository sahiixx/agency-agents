"""
providers/n8n_provider.py — n8n workflow automation provider.

Fires an n8n webhook trigger and returns the workflow response as the
"agent output".  This lets any Agency mission delegate sub-tasks to
n8n workflows (email, Slack, CRM, data pipelines, etc.).

Environment variables:
  N8N_BASE_URL     — n8n instance base URL (default: http://localhost:5678)
  N8N_API_KEY      — n8n API key for /api/v1 endpoints (optional)
  N8N_WEBHOOK_PATH — default webhook path suffix (default: /webhook/agency)

Usage:
  The system_prompt is used as a "workflow tag" to route to named workflows.
  The query becomes the webhook payload's "mission" field.

  With --provider n8n:
    agency.py --provider n8n --mission "Send weekly sales report"
    → POST http://localhost:5678/webhook/agency  {"mission": "...", "workflow_tag": "..."}

Install: n8n runs as a standalone Node service — no Python package needed.
  npm install -g n8n  OR  docker run -it --rm -p 5678:5678 n8nio/n8n
"""

from __future__ import annotations
import json
import os
import urllib.request
import urllib.parse
from typing import Any

from providers.base import BaseProvider, ProviderResult

N8N_BASE_URL     = os.getenv("N8N_BASE_URL",     "http://localhost:5678")
N8N_API_KEY      = os.getenv("N8N_API_KEY",      "")
N8N_WEBHOOK_PATH = os.getenv("N8N_WEBHOOK_PATH", "/webhook/agency")

# Maximum characters from system_prompt used as workflow_tag routing hint
MAX_WORKFLOW_TAG_LENGTH = 200


class N8NProvider(BaseProvider):
    """n8n workflow automation — fires webhooks, returns workflow output."""

    name = "n8n"

    def get_llm(self, **kwargs) -> Any:
        """n8n does not expose an LLM; returns None."""
        return None

    def run_agent(
        self,
        system_prompt: str,
        query:         str,
        agent_name:    str = "n8n-workflow",
        base_url:      str = N8N_BASE_URL,
        webhook_path:  str = N8N_WEBHOOK_PATH,
        **kwargs,
    ) -> ProviderResult:
        """
        POST a mission payload to the n8n webhook and return the workflow response.
        system_prompt is passed as workflow_tag for routing to named workflows.
        """
        url     = f"{base_url.rstrip('/')}{webhook_path}"
        payload = json.dumps({
            "mission":      query,
            "workflow_tag": system_prompt[:MAX_WORKFLOW_TAG_LENGTH] if system_prompt else agent_name,
            "agent_name":   agent_name,
        }).encode()

        headers: dict = {
            "Content-Type": "application/json",
            "User-Agent":   "TheAgency/1.0",
        }
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY

        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode()
            try:
                data   = json.loads(raw)
                output = (
                    data.get("output") or
                    data.get("result") or
                    data.get("message") or
                    json.dumps(data, indent=2)
                )
            except (json.JSONDecodeError, AttributeError):
                output = raw

            return ProviderResult(
                output=str(output),
                provider=self.name,
                model="n8n",
                metadata={"url": url},
            )
        except Exception as e:
            return ProviderResult(
                output="", provider=self.name, model="n8n",
                error=(
                    f"n8n webhook error: {e}. "
                    f"Is n8n running at {base_url}? "
                    f"Check N8N_BASE_URL and N8N_WEBHOOK_PATH env vars."
                ),
            )

    # ── n8n REST API helpers ──────────────────────────────────────────────────

    def list_workflows(self, base_url: str = N8N_BASE_URL) -> list[dict]:
        """Return all workflows from the n8n REST API (requires N8N_API_KEY)."""
        if not N8N_API_KEY:
            return [{"error": "N8N_API_KEY not set — cannot list workflows via REST API"}]
        url = f"{base_url.rstrip('/')}/api/v1/workflows"
        req = urllib.request.Request(url, headers={
            "X-N8N-API-KEY": N8N_API_KEY,
            "User-Agent":    "TheAgency/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode()).get("data", [])
        except Exception as e:
            return [{"error": str(e)}]

    def trigger_workflow_by_id(
        self,
        workflow_id: str,
        payload:     dict,
        base_url:    str = N8N_BASE_URL,
    ) -> dict:
        """Trigger a specific workflow by ID via n8n REST API."""
        if not N8N_API_KEY:
            return {"error": "N8N_API_KEY not set"}
        url = f"{base_url.rstrip('/')}/api/v1/workflows/{workflow_id}/execute"
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type":  "application/json",
                "X-N8N-API-KEY": N8N_API_KEY,
                "User-Agent":    "TheAgency/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            return {"error": str(e)}
