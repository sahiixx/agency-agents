#!/usr/bin/env python3
"""
mcp_tools.py — MCP tool layer for The Agency.

Wraps external capabilities as LangChain-compatible tools so any agent
can call them via the standard tool interface. No MCP server required —
these are local MCP-style tool definitions that follow the protocol schema.

Tools available:
  web_search                — fetch live search results (via DuckDuckGo, no key needed)
  read_file                 — read any file in the repo
  write_output              — write structured output to /tmp/agency_outputs/
  code_lint                 — run ruff lint on a code snippet
  memory_recall             — query Titans memory for past mission insights
  get_datetime              — return current UTC datetime
  query_ai_tools_knowledge  — natural language Q&A against the AI tools knowledge base
  get_tool_system_prompt    — retrieve raw system prompt for a specific AI tool
"""

import json
import os
import subprocess
import tempfile
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

OUTPUTS_DIR = Path("/tmp/agency_outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)

REPO_ROOT = Path(__file__).parent.resolve()

# Path to the sibling knowledge-base repo (override via SYSTEM_PROMPTS_REPO env var)
KNOWLEDGE_REPO        = Path(os.environ.get(
    "SYSTEM_PROMPTS_REPO",
    str(REPO_ROOT.parent / "system-prompts-and-models-of-ai-tools"),
))
KNOWLEDGE_BRIDGE_PATH = KNOWLEDGE_REPO / "integrations" / "agency_bridge.py"


# ── Tool 1: Web Search (DuckDuckGo instant answer, no API key) ─────────────
@tool
def web_search(query: str) -> str:
    """Search the web for current information. Returns top results as text."""
    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "TheAgency/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())

        results = []
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
        for t in data.get("RelatedTopics", [])[:4]:
            if isinstance(t, dict) and t.get("Text"):
                results.append(f"• {t['Text']}")

        return "\n".join(results) if results else f"No instant answer found for: {query}"
    except Exception as e:
        return f"Search error: {e}"


# ── Tool 2: Read File ───────────────────────────────────────────────────────────
@tool
def read_file(path: str) -> str:
    """Read any file in the agency repo. Path is relative to repo root."""
    try:
        full = REPO_ROOT / path
        if not full.exists():
            return f"File not found: {path}"
        content = full.read_text(encoding="utf-8", errors="replace")
        if len(content) > 4000:
            content = content[:4000] + f"\n\n... (truncated, {len(content)} total chars)"
        return content
    except Exception as e:
        return f"Read error: {e}"


# ── Tool 3: Write Output ──────────────────────────────────────────────────────
@tool
def write_output(filename: str, content: str) -> str:
    """Write structured output to /tmp/agency_outputs/. Returns confirmation."""
    try:
        safe = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe:
            safe = f"output_{datetime.now().strftime('%H%M%S')}.txt"
        path = OUTPUTS_DIR / safe
        path.write_text(content, encoding="utf-8")
        return f"Written: {path} ({len(content)} chars)"
    except Exception as e:
        return f"Write error: {e}"


# ── Tool 4: Code Lint ───────────────────────────────────────────────────────────
@tool
def code_lint(code: str, language: str = "python") -> str:
    """Lint a code snippet. Returns issues found or 'No issues'."""
    if language != "python":
        return f"Lint support: python only (got {language})"
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            fname = f.name
        result = subprocess.run(
            ["ruff", "check", "--select=E,F,W", fname],
            capture_output=True, text=True, timeout=10
        )
        out = result.stdout.strip() or result.stderr.strip()
        return out if out else "No issues found."
    except FileNotFoundError:
        return "ruff not installed — pip install ruff"
    except Exception as e:
        return f"Lint error: {e}"


# ── Tool 5: Memory Recall ───────────────────────────────────────────────────────
@tool
def memory_recall(topic: str) -> str:
    """Query Titans memory for past mission outcomes related to a topic."""
    try:
        import sys
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from memory.titans_memory import TitansMemory
        mem = TitansMemory()
        if not mem.ledger:
            return "No missions recorded in memory yet."
        topic_lower = topic.lower()
        matches = [
            e for e in mem.ledger
            if topic_lower in getattr(e, 'mission', str(e)).lower()
        ]
        entries = matches[:5] if matches else mem.ledger[-5:]
        lines = [f"Past missions (Titans memory — {len(mem.ledger)} total):"]
        for e in entries:
            mission = getattr(e, 'mission', '?')
            verdict = getattr(e, 'verdict', '?')
            surprise = getattr(e, 'surprise', 0)
            weight   = getattr(e, 'weight', 0)
            lines.append(f"  [{verdict}] {str(mission)[:60]} (surprise={surprise:.2f}, weight={weight:.2f})")
        return "\n".join(lines)
    except Exception as e:
        return f"Memory recall error: {e}"


# ── Tool 6: Get Current DateTime ─────────────────────────────────────────────────
@tool
def get_datetime(timezone: str = "UTC") -> str:
    """Return the current date and time. Timezone label only, always returns UTC."""
    return f"Current datetime: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"


# ── Integration: AI Tools Knowledge Base ────────────────────────────────────────

def _load_knowledge_bridge():
    """Lazily import agency_bridge from the sibling system-prompts repo."""
    import importlib.util
    if not KNOWLEDGE_BRIDGE_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location("agency_bridge", str(KNOWLEDGE_BRIDGE_PATH))
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Tool 7: Query AI Tools Knowledge Base ───────────────────────────────────
@tool
def query_ai_tools_knowledge(question: str) -> str:
    """
    Query the AI tools knowledge base with a natural language question.
    Returns Claude's analysis based on 37 tools' system prompts and metadata.
    Examples: 'Which tools support agent mode?', 'Compare Cursor and Windsurf',
    'What does the Claude Code system prompt say about tool use?'
    """
    try:
        kb_url = os.environ.get("KNOWLEDGE_SERVER_URL", "http://localhost:8200")
        try:
            payload = json.dumps({"question": question}).encode()
            req = urllib.request.Request(
                f"{kb_url}/query",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
                return data.get("answer", "No answer returned")
        except Exception:
            pass

        bridge = _load_knowledge_bridge()
        if bridge is None:
            return (
                "Knowledge base not reachable. "
                f"Start it: cd {KNOWLEDGE_REPO} && python3 integrations/claude_query_server.py\n"
                "Or set SYSTEM_PROMPTS_REPO env var to the repo path."
            )
        return bridge.query_knowledge_base(question)
    except Exception as e:
        return f"Knowledge base query error: {e}"


# ── Tool 8: Get System Prompt for a Specific AI Tool ───────────────────────
@tool
def get_tool_system_prompt(tool_slug: str) -> str:
    """
    Retrieve the full system prompt text for a specific AI tool by slug.
    Use this to understand how a tool instructs its AI, its constraints, and design patterns.
    Common slugs: claude-code, cursor-prompts, windsurf, devin-ai, replit,
    manus-agent-tools-prompt, github-copilot, lovable.
    Use query_ai_tools_knowledge('list all tools') to discover all available slugs.
    """
    try:
        kb_url = os.environ.get("KNOWLEDGE_SERVER_URL", "http://localhost:8200")
        try:
            req = urllib.request.Request(
                f"{kb_url}/tools/{tool_slug}/prompt", method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.read().decode()
        except Exception:
            pass

        bridge = _load_knowledge_bridge()
        if bridge is None:
            return f"Knowledge base not available for tool: {tool_slug}"
        return bridge.get_system_prompt_text(tool_slug)
    except Exception as e:
        return f"System prompt retrieval error for '{tool_slug}': {e}"


# ── Registry ────────────────────────────────────────────────────────────────────
MCP_TOOLS = [
    web_search,
    read_file,
    write_output,
    code_lint,
    memory_recall,
    get_datetime,
    query_ai_tools_knowledge,
    get_tool_system_prompt,
]

MCP_TOOL_NAMES = [t.name for t in MCP_TOOLS]


if __name__ == "__main__":
    print("MCP Tools available:")
    for t in MCP_TOOLS:
        print(f"  {t.name:30} — {t.description.split('.')[0]}")
    print(f"\nTesting memory_recall...")
    print(memory_recall.invoke({"topic": "auth"}))
    print(f"\nTesting get_datetime...")
    print(get_datetime.invoke({}))
