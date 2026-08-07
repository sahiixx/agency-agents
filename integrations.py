#!/usr/bin/env python3
"""
integrations.py — Unified integration layer for The Agency.

Every stack-implied third-party service is registered here with the env vars
it needs. `integration_status()` reports which are configured and which keys
are missing, and `init_optional_integrations()` lazily initializes the
monitoring/observability SDKs (Sentry, Traceloop, LangSmith) only when their
keys are present — never crashing when they are not.

Services register with:
    name        — human-readable label
    category    — CMS | LLM | Monitoring | Automation | Voice | Tools
    env_vars    — list of env var names required to be configured
    purpose     — what the integration does
    setup_hint  — where to get the key

Read the status from any script:
    from integrations import integration_status
    for s in integration_status(): print(s["name"], s["configured"])
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

# ── Registry ──────────────────────────────────────────────────────────────────

INTEGRATIONS: list[dict[str, Any]] = [
    # LLM providers — CLOUD-ONLY. The runtime resolves the first configured cloud
    # key (Anthropic → OpenAI → Gemini) via providers.default_provider(). There is
    # no local model runtime.
    {
        "name": "Anthropic Claude",
        "category": "LLM",
        "env_vars": ["ANTHROPIC_API_KEY"],
        "purpose": "Default cloud LLM backbone for agent missions (claude-sonnet-5).",
        "setup_hint": "console.anthropic.com → API keys",
    },
    {
        "name": "OpenAI",
        "category": "LLM",
        "env_vars": ["OPENAI_API_KEY"],
        "purpose": "OpenAI provider + voice (gpt-5.1 / gpt-realtime-2.1).",
        "setup_hint": "platform.openai.com → API keys",
    },
    {
        "name": "Google Gemini",
        "category": "LLM",
        "env_vars": ["GEMINI_API_KEY"],
        "purpose": "Gemini provider / ADK agent orchestration.",
        "setup_hint": "aistudio.google.com → API key",
    },
    # CMS
    {
        "name": "Builder.io CMS",
        "category": "CMS",
        "env_vars": ["BUILDER_API_KEY"],
        "purpose": "Visual headless CMS — dashboard CMS panel fetches content models.",
        "setup_hint": "builder.io → Space Settings → API Keys (public key)",
    },
    # Monitoring & observability
    {
        "name": "Sentry",
        "category": "Monitoring",
        "env_vars": ["SENTRY_DSN"],
        "purpose": "Error tracking + performance for the dashboard and scripts.",
        "setup_hint": "sentry.io → Project → Client Keys (DSN)",
    },
    {
        "name": "Traceloop",
        "category": "Monitoring",
        "env_vars": ["TRACELOOP_API_KEY"],
        "purpose": "OpenTelemetry LLM/agent traces, evals, quality monitoring.",
        "setup_hint": "traceloop.com → API key",
    },
    {
        "name": "LangSmith",
        "category": "Monitoring",
        "env_vars": ["LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2"],
        "defaults": {"LANGCHAIN_TRACING_V2": "true"},
        "purpose": "LangChain tracing for deepagents runs.",
        "setup_hint": "smith.langchain.com → Settings → API key",
    },
    # Automation & data
    {
        "name": "n8n",
        "category": "Automation",
        "env_vars": ["N8N_BASE_URL", "N8N_API_KEY"],
        "purpose": "Trigger n8n workflows from agent tools.",
        "setup_hint": "n8n instance → Settings → API",
    },
    {
        "name": "Perplexica",
        "category": "Search",
        "env_vars": ["PERPLEXICA_URL"],
        "purpose": "AI-powered search replacing DuckDuckGo in agents.",
        "setup_hint": "Self-hosted Perplexica URL.",
    },
    {
        "name": "SQLBot",
        "category": "Data",
        "env_vars": ["SQLBOT_URL"],
        "purpose": "Natural-language SQL over mission data.",
        "setup_hint": "SQLBot service URL.",
    },
    # Voice
    {
        "name": "Twilio",
        "category": "Voice",
        "env_vars": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
        "purpose": "Phone-call voice mode for the agency.",
        "setup_hint": "twilio.com → Console → API credentials",
    },
    # MCP / tools
    {
        "name": "MCP Registry",
        "category": "Tools",
        "env_vars": ["MCP_REGISTRY_URL"],
        "purpose": "Dynamic MCP tool servers loaded at import time.",
        "setup_hint": "URL of your MCP registry endpoint.",
    },
    # First-party ecosystem
    {
        "name": "Moltbot Gateway",
        "category": "Automation",
        "env_vars": ["MOLTBOT_GATEWAY_URL"],
        "purpose": "Fire missions via the sahiixx moltworker gateway.",
        "setup_hint": "Your moltworker Cloudflare gateway URL.",
    },
    {
        "name": "NOWHERE.AI",
        "category": "Data",
        "env_vars": ["NOWHERE_AI_URL"],
        "purpose": "B2B lead scoring + UAE market intelligence.",
        "setup_hint": "Your NOWHERE.AI platform URL.",
    },
    {
        "name": "Trust Graph",
        "category": "Data",
        "env_vars": ["TRUST_GRAPH_URL"],
        "purpose": "Neo4j entity trust graph queries.",
        "setup_hint": "Neo4j HTTP endpoint.",
    },
]


def _check(entry: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one registry entry against the environment."""
    env_vars = entry["env_vars"]
    present = [v for v in env_vars if os.environ.get(v)]
    defaults = entry.get("defaults", {})
    missing = [v for v in env_vars if v not in defaults and v not in present]
    configured = not missing
    if entry.get("configured") is not None and callable(entry.get("configured")):
        configured = entry["configured"]() or configured
    return {
        "name": entry["name"],
        "category": entry["category"],
        "env_vars": env_vars,
        "missing": missing,
        "configured": configured,
        "purpose": entry.get("purpose", ""),
        "setup_hint": entry.get("setup_hint", ""),
    }


def integration_status() -> list[dict[str, Any]]:
    """Return configured/unconfigured status for every registered integration."""
    return [_check(e) for e in INTEGRATIONS]


def integration_summary() -> dict[str, Any]:
    """Compact summary: counts + list of missing keys."""
    statuses = integration_status()
    configured = [s for s in statuses if s["configured"]]
    missing_keys = sorted({k for s in statuses for k in s["missing"]})
    return {
        "total": len(statuses),
        "configured": len(configured),
        "unconfigured": len(statuses) - len(configured),
        "missing_keys": missing_keys,
        "services": statuses,
    }


# ── Optional initializers (never raise) ───────────────────────────────────────

def _safe_init(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except Exception as e:  # noqa: BLE001 — init must never crash the app
        print(f"  [integrations] {name} init skipped: {type(e).__name__}: {e}")


def init_sentry() -> None:
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return
    def _init() -> None:
        import sentry_sdk  # type: ignore
        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.environ.get("APP_ENV", "development"),
        )
        print("  [integrations] Sentry initialized.")
    _safe_init("Sentry", _init)


def init_traceloop() -> None:
    key = os.environ.get("TRACELOOP_API_KEY")
    if not key:
        return
    def _init() -> None:
        from traceloop_sdk import Traceloop  # type: ignore
        Traceloop.init(
            api_key=key,
            disable_batch=True,
            exporter=os.environ.get("TRACELOOP_EXPORTER", "traceloop"),
        )
        print("  [integrations] Traceloop initialized.")
    _safe_init("Traceloop", _init)


def init_langsmith() -> None:
    key = os.environ.get("LANGCHAIN_API_KEY")
    if not key:
        return
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "agency-agents")
    def _init() -> None:
        import langsmith  # type: ignore
        langsmith.Client(api_key=key)  # validates the key; tracing is env-driven
        print("  [integrations] LangSmith tracing enabled.")
    _safe_init("LangSmith", _init)


def init_optional_integrations() -> None:
    """Initialize every optional SDK that has its key configured."""
    init_sentry()
    init_traceloop()
    init_langsmith()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    summary = integration_summary()
    print(f"Integrations: {summary['configured']}/{summary['total']} configured")
    for s in summary["services"]:
        mark = "✅" if s["configured"] else "⬜"
        print(f"  {mark} {s['name']} [{s['category']}]")
        if s["missing"]:
            print(f"        missing keys: {', '.join(s['missing'])}")
    if summary["missing_keys"]:
        print(f"\nMissing keys: {', '.join(summary['missing_keys'])}")
