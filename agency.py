#!/usr/bin/env python3
"""
agency.py — The Agency's unified entry point.

A fully-wired orchestrator using the deepagents SDK properly:
  - MemoryMiddleware: shared agency memory loaded at startup
  - SubAgentMiddleware: agents can spawn specialist subagents
  - Claude Reasoning Core: final gate on every mission
  - Persistent state via checkpointer (optional)

Usage:
  python3 agency.py --mission "Build a REST API for user auth"
  python3 agency.py --mission "..." --agents pm,backend,qa,core
  python3 agency.py --list-agents
"""
import os, sys, argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent, SubAgent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

CLAUDE_MODEL = "claude-sonnet-4-6"
MEMORY_FILE  = "memory/AGENTS.md"

# All available specialist agents
AGENT_REGISTRY = {
    "pm":        ("project-management/project-manager-senior.md",       "Senior project manager — planning, task decomposition, timelines"),
    "frontend":  ("engineering/engineering-frontend-developer.md",       "Frontend developer — React, Next.js, UI implementation"),
    "backend":   ("engineering/engineering-backend-architect.md",        "Backend architect — APIs, databases, system design"),
    "ai":        ("engineering/engineering-ai-engineer.md",              "AI engineer — ML models, LLM integration, RAG"),
    "security":  ("engineering/engineering-security-engineer.md",        "Security engineer — threat modeling, vulnerability review"),
    "devops":    ("engineering/engineering-devops-automator.md",         "DevOps — CI/CD, infrastructure, deployment automation"),
    "qa":        ("testing/testing-reality-checker.md",                  "QA engineer — testing, auditing, quality gates"),
    "design":    ("design/design-ux-architect.md",                       "UX architect — user experience, information architecture"),
    "growth":    ("marketing/marketing-growth-hacker.md",                "Growth hacker — acquisition, conversion, metrics"),
    "copywriter":("marketing/marketing-content-creator.md",              "Content creator — copy, messaging, brand voice"),
    "sales":     ("sales/sales-deal-strategist.md",                      "Deal strategist — sales strategy, proposals, negotiation"),
    "core":      ("specialized/specialized-claude-reasoning-core.md",    "Claude Reasoning Core — judgment, ethics, final verdicts"),
}

DEFAULT_MISSION_AGENTS = ["pm", "backend", "frontend", "qa", "security", "core"]
DEFAULT_SAAS_AGENTS    = ["pm", "copywriter", "frontend", "qa", "core"]
DEFAULT_RESEARCH_AGENTS = ["pm", "ai", "qa", "core"]


def get_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY not set."); sys.exit(1)
    return ChatAnthropic(model=CLAUDE_MODEL, api_key=api_key)


def load(path: str) -> str:
    f = REPO_ROOT / path
    return f.read_text() if f.exists() else ""


def build_subagent(name: str, llm) -> SubAgent:
    """Build a SubAgent spec for a named agent."""
    path, description = AGENT_REGISTRY[name]
    return {
        "name": name,
        "description": description,
        "system_prompt": load(path),
        "tools": [],
        "model": llm,
    }


def run_mission(goal: str, agent_names: list[str], mode: str = "full"):
    llm = get_claude()

    print(f"\n{'═'*65}")
    print(f"  🚀  MISSION: {goal}")
    print(f"  🧠  Engine: Claude {CLAUDE_MODEL}")
    print(f"  🤖  Agents: {', '.join(agent_names)}")
    print(f"{'═'*65}\n")

    # Validate agent names
    invalid = [n for n in agent_names if n not in AGENT_REGISTRY]
    if invalid:
        print(f"❌  Unknown agents: {invalid}")
        print(f"   Available: {list(AGENT_REGISTRY.keys())}")
        sys.exit(1)

    # Build subagents (all except core, which is the orchestrating agent)
    specialist_names = [n for n in agent_names if n != "core"]
    subagents = [build_subagent(n, llm) for n in specialist_names]

    # Core (Claude Reasoning Core) is the orchestrating agent
    # It has all specialists available as subagents it can delegate to
    core_prompt = load(AGENT_REGISTRY["core"][0])

    # Build the orchestrating agent with:
    # - memory: shared agency context loaded at startup
    # - subagents: all specialist agents it can spawn
    orchestrator = create_deep_agent(
        model=llm,
        tools=[],
        system_prompt=core_prompt,
        subagents=subagents,
        memory=[MEMORY_FILE],
        name="claude-agency-orchestrator",
    )

    # The mission brief — Core orchestrates and delegates.
    # Note: SubAgentMiddleware appends "Available subagent types: - name: description"
    # to Core's system prompt automatically. The task tool routes by name.
    brief = f"""MISSION: {goal}

You have specialist subagents available (listed in your system prompt under "Available subagent types").
Use the `task` tool to delegate to them by name.

Orchestration plan:
1. Delegate planning to the `pm` subagent first — get a structured breakdown
2. Delegate implementation/design tasks to the relevant specialist subagents in parallel where possible
3. Delegate quality review to the `qa` subagent
4. Synthesize all outputs
5. Apply your constitutional review (accuracy, safety, completeness)
6. Return a final GO/NO-GO verdict with the complete deliverable

Delegate — do not do the specialists' work yourself.
You are the orchestrator and the final judgment layer."""

    print("  🎬  Orchestrator active — delegating to specialists...\n")

    response = orchestrator.invoke({
        "messages": [HumanMessage(content=brief)]
    })

    final = response["messages"][-1].content

    print(f"\n{'═'*65}")
    print("  🧠  MISSION COMPLETE — CLAUDE REASONING CORE VERDICT")
    print(f"{'═'*65}")
    print(final)
    print(f"{'═'*65}\n")

    return final


def list_agents():
    print(f"\n{'─'*65}")
    print(f"  🤖  Agency Agent Registry — {len(AGENT_REGISTRY)} agents")
    print(f"{'─'*65}")
    for name, (path, desc) in AGENT_REGISTRY.items():
        exists = "✅" if (REPO_ROOT / path).exists() else "❌"
        print(f"  {exists}  {name:<12} {desc}")
    print(f"\n  Presets:")
    print(f"    --preset full     → {', '.join(DEFAULT_MISSION_AGENTS)}")
    print(f"    --preset saas     → {', '.join(DEFAULT_SAAS_AGENTS)}")
    print(f"    --preset research → {', '.join(DEFAULT_RESEARCH_AGENTS)}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="🧠 The Agency — Unified Orchestrator (Claude + Memory + SubAgents)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 agency.py --list-agents
  python3 agency.py --mission "Build a REST API for user auth"
  python3 agency.py --mission "Design a SaaS landing page" --preset saas
  python3 agency.py --mission "Research AI trends" --preset research
  python3 agency.py --mission "Audit our security posture" --agents security,qa,core
        """
    )
    parser.add_argument("--mission", "-m", type=str, help="Mission goal")
    parser.add_argument("--agents", type=str, help="Comma-separated agent names")
    parser.add_argument("--preset", choices=["full", "saas", "research"],
                        default="full", help="Agent preset (default: full)")
    parser.add_argument("--list-agents", action="store_true", help="List all available agents")
    args = parser.parse_args()

    if args.list_agents:
        list_agents()
        return

    if not args.mission:
        parser.print_help(); return

    if args.agents:
        agent_names = [a.strip() for a in args.agents.split(",")]
    elif args.preset == "saas":
        agent_names = DEFAULT_SAAS_AGENTS
    elif args.preset == "research":
        agent_names = DEFAULT_RESEARCH_AGENTS
    else:
        agent_names = DEFAULT_MISSION_AGENTS

    # Always ensure core is last
    if "core" in agent_names:
        agent_names = [a for a in agent_names if a != "core"] + ["core"]

    run_mission(args.mission, agent_names)


if __name__ == "__main__":
    main()
