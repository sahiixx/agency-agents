#!/usr/bin/env python3
"""
agency.py — The Agency unified entry point.

Fully-wired orchestrator using the deepagents SDK:
  - MemoryMiddleware + FilesystemBackend: shared AGENTS.md loaded at startup
  - SubAgentMiddleware: Claude Core spawns specialists via the `task` tool
  - TitansMemory: surprise-weighted memory persists lessons across runs
  - Claude Reasoning Core: final gate — GO / CONDITIONAL GO / NO-GO

Usage:
  python3 agency.py --list-agents
  python3 agency.py --mission "Build a REST API for user auth"
  python3 agency.py --mission "Design a SaaS landing page" --preset saas
  python3 agency.py --mission "Research AI trends" --preset research
  python3 agency.py --mission "Audit our security" --agents security,qa,core
"""

import os
import sys
import warnings
import argparse
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.resolve()
SDK_PATH  = REPO_ROOT / "deepagents" / "libs" / "deepagents"

for p in (str(SDK_PATH), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    from deepagents import create_deep_agent, SubAgent
    from deepagents.backends import FilesystemBackend
except ImportError as e:
    print(f"❌  deepagents SDK not found: {e}")
    print("    Run: pip install -e deepagents/libs/deepagents")
    sys.exit(1)

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
except ImportError as e:
    print(f"❌  langchain-anthropic not found: {e}")
    print("    Run: pip install langchain-anthropic")
    sys.exit(1)

from memory.titans_memory import TitansMemory

# ── Config ────────────────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-6"
MEMORY_FILE  = "memory/AGENTS.md"  # relative to REPO_ROOT

# ── Agent registry ────────────────────────────────────────────────────────────
AGENT_REGISTRY = {
    "pm":        ("project-management/project-manager-senior.md",    "Senior project manager — planning, task decomposition, timelines"),
    "frontend":  ("engineering/engineering-frontend-developer.md",    "Frontend developer — React, Next.js, UI implementation"),
    "backend":   ("engineering/engineering-backend-architect.md",     "Backend architect — APIs, databases, system design"),
    "ai":        ("engineering/engineering-ai-engineer.md",           "AI engineer — ML models, LLM integration, RAG"),
    "security":  ("engineering/engineering-security-engineer.md",     "Security engineer — threat modeling, vulnerability review"),
    "devops":    ("engineering/engineering-devops-automator.md",      "DevOps — CI/CD, infrastructure, deployment automation"),
    "qa":        ("testing/testing-reality-checker.md",               "QA engineer — testing, auditing, quality gates"),
    "design":    ("design/design-ux-architect.md",                    "UX architect — user experience, information architecture"),
    "growth":    ("marketing/marketing-growth-hacker.md",             "Growth hacker — acquisition, conversion, metrics"),
    "copywriter":("marketing/marketing-content-creator.md",           "Content creator — copy, messaging, brand voice"),
    "sales":     ("sales/sales-deal-strategist.md",                   "Deal strategist — sales strategy, proposals, negotiation"),
    "core":      ("specialized/specialized-claude-reasoning-core.md", "Claude Reasoning Core — judgment, ethics, final verdicts"),
}

PRESETS = {
    "full":     ["pm", "backend", "frontend", "qa", "security", "core"],
    "saas":     ["pm", "copywriter", "frontend", "qa", "core"],
    "research": ["pm", "ai", "qa", "core"],
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_llm() -> ChatAnthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY not set.")
        print("    Export it: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)
    return ChatAnthropic(model=CLAUDE_MODEL, api_key=api_key)


def load_agent(path: str) -> str:
    f = REPO_ROOT / path
    if not f.exists():
        print(f"  ⚠️   Agent file missing: {path}")
        return ""
    return f.read_text()


def build_subagent(name: str, llm: ChatAnthropic) -> SubAgent:
    path, description = AGENT_REGISTRY[name]
    return {
        "name":          name,
        "description":   description,
        "system_prompt": load_agent(path),
        "tools":         [],
        "model":         llm,
    }


# ── Core mission runner ───────────────────────────────────────────────────────

def run_mission(goal: str, agent_names: list) -> str:
    invalid = [n for n in agent_names if n not in AGENT_REGISTRY]
    if invalid:
        print(f"❌  Unknown agents: {invalid}")
        print(f"   Available: {list(AGENT_REGISTRY.keys())}")
        sys.exit(1)

    llm = get_llm()

    print(f"\n{'='*65}")
    print(f"  MISSION: {goal}")
    print(f"  Engine:  {CLAUDE_MODEL}")
    print(f"  Agents:  {', '.join(agent_names)}")
    print(f"{'='*65}\n")

    # Build subagents (all except core)
    specialist_names = [n for n in agent_names if n != "core"]
    subagents = [build_subagent(n, llm) for n in specialist_names]
    for sa in subagents:
        status = "OK" if sa["system_prompt"] else "MISSING"
        print(f"  [{status}]  {sa['name']} ({len(sa['system_prompt']):,} chars)")

    # FilesystemBackend so MemoryMiddleware reads from local disk
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fs_backend = FilesystemBackend(root_dir=str(REPO_ROOT), virtual_mode=False)

    # Build orchestrator graph
    print(f"\n  Building orchestrator...")
    try:
        orchestrator = create_deep_agent(
            model=llm,
            tools=[],
            system_prompt=load_agent(AGENT_REGISTRY["core"][0]),
            subagents=subagents,
            memory=[MEMORY_FILE],
            backend=fs_backend,
            name="claude-agency-orchestrator",
        )
        print(f"  Graph ready ({len(orchestrator.nodes)} nodes)\n")
    except Exception as e:
        print(f"  ERROR building graph: {type(e).__name__}: {e}")
        return None

    brief = f"""MISSION: {goal}

You have specialist subagents available — listed in your system prompt under "Available subagent types".
Use the `task` tool to delegate to them by name.

Steps:
1. Delegate planning to `pm` first — structured breakdown
2. Delegate implementation to relevant specialists in parallel
3. Delegate quality review to `qa`
4. Synthesize all outputs
5. Constitutional review — accuracy, safety, completeness
6. Return final GO / CONDITIONAL GO / NO-GO verdict with complete deliverable

Delegate everything. You are the orchestrator and final judge."""

    print(f"  Orchestrating...\n")

    try:
        response = orchestrator.invoke(
            {"messages": [HumanMessage(content=brief)]},
            config={"recursion_limit": 50},
        )
        final = response["messages"][-1].content
    except KeyboardInterrupt:
        print("\n  Mission interrupted.")
        return None
    except Exception as e:
        print(f"\n  Mission failed: {type(e).__name__}: {e}")
        return None

    print(f"\n{'='*65}")
    print(f"  VERDICT — CLAUDE REASONING CORE")
    print(f"{'='*65}")
    print(final)
    print(f"{'='*65}\n")

    # Record in Titans memory
    verdict = (
        "NO-GO"          if "no-go"       in final.lower() and "conditional" not in final.lower() else
        "CONDITIONAL GO" if "conditional" in final.lower() else
        "GO"
    )
    try:
        mem = TitansMemory()
        outcome = mem.record_outcome(goal, verdict)
        mem.inject_into_agents_md()
        print(f"  Memory: {verdict} (surprise={outcome.surprise:.2f}) — {mem.summary()}")
    except Exception as e:
        print(f"  Memory update failed (non-fatal): {e}")

    return final


# ── CLI ───────────────────────────────────────────────────────────────────────

def list_agents():
    print(f"\n{'-'*65}")
    print(f"  Agency Agent Registry — {len(AGENT_REGISTRY)} agents")
    print(f"{'-'*65}")
    for name, (path, desc) in AGENT_REGISTRY.items():
        exists = "OK  " if (REPO_ROOT / path).exists() else "MISS"
        print(f"  [{exists}]  {name:<12} {desc}")
    print(f"\n  Presets:")
    for preset, agents in PRESETS.items():
        print(f"    --preset {preset:<10} -> {', '.join(agents)}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="The Agency — Claude-powered multi-agent orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 agency.py --list-agents
  python3 agency.py --mission "Write a technical spec for user auth"
  python3 agency.py --mission "Design a SaaS landing page" --preset saas
  python3 agency.py --mission "Research AI memory techniques" --preset research
  python3 agency.py --mission "Audit security posture" --agents security,qa,core
        """,
    )
    parser.add_argument("--mission", "-m", type=str, help="Mission goal")
    parser.add_argument("--agents",        type=str, help="Comma-separated agent keys")
    parser.add_argument("--preset",        choices=list(PRESETS), default="full",
                        help="Agent preset (default: full)")
    parser.add_argument("--list-agents",   action="store_true", help="List available agents")
    args = parser.parse_args()

    if args.list_agents:
        list_agents()
        return

    if not args.mission:
        parser.print_help()
        return

    agent_names = (
        [a.strip() for a in args.agents.split(",")]
        if args.agents
        else list(PRESETS[args.preset])
    )

    # Always put core last
    if "core" in agent_names:
        agent_names = [a for a in agent_names if a != "core"] + ["core"]

    run_mission(args.mission, agent_names)


if __name__ == "__main__":
    main()
