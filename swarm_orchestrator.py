#!/usr/bin/env python3
"""
The Agency — Swarm Orchestrator
Claude (Anthropic) is the reasoning backbone of every agent in the swarm.
Pipeline: PM → Dev → QA → [Claude Reasoning Core Review] → Ship
"""

import os
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

CLAUDE_MODEL = "claude-sonnet-4-6"

SWARM_AGENTS = {
    "pm":       "project-management/project-manager-senior.md",
    "frontend": "engineering/engineering-frontend-developer.md",
    "backend":  "engineering/engineering-backend-architect.md",
    "qa":       "testing/testing-reality-checker.md",
    "security": "engineering/engineering-security-engineer.md",
    "core":     "specialized/specialized-claude-reasoning-core.md",
}


def get_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    return ChatAnthropic(model=CLAUDE_MODEL, api_key=api_key)


def load(path: str) -> str:
    full = REPO_ROOT / path
    return full.read_text() if full.exists() else ""


def run_agent(llm, system_prompt: str, query: str, name: str) -> str:
    agent = create_deep_agent(model=llm, tools=[], system_prompt=system_prompt, name=name)
    response = agent.invoke({"messages": [HumanMessage(content=query)]})
    return response["messages"][-1].content


class AgencySwarm:
    def __init__(self):
        self.llm = get_claude()
        self.prompts = {k: load(v) for k, v in SWARM_AGENTS.items()}

    def run_mission(self, mission_goal: str, mode: str = "full"):
        print(f"\n{'═'*65}")
        print(f"  🚀  MISSION: {mission_goal}")
        print(f"  🧠  Engine: Claude {CLAUDE_MODEL} (Anthropic)")
        print(f"  🔁  Mode: {mode}")
        print(f"{'═'*65}\n")

        # ── Phase 1: Project Manager ──────────────────────────────────
        print("  📋  [Phase 1/5] Project Manager — Planning...")
        plan = run_agent(
            self.llm, self.prompts["pm"],
            f"Create a detailed execution plan for: {mission_goal}",
            "pm-agent"
        )
        print(f"  ✅  Plan ready ({len(plan):,} chars)\n")

        # ── Phase 2: Frontend Developer ───────────────────────────────
        print("  💻  [Phase 2/5] Frontend Developer — Implementation...")
        code = run_agent(
            self.llm, self.prompts["frontend"],
            f"Implement the frontend based on this plan:\n\n{plan}",
            "frontend-agent"
        )
        print(f"  ✅  Implementation ready ({len(code):,} chars)\n")

        # ── Phase 3: QA Reality Check ─────────────────────────────────
        print("  🧪  [Phase 3/5] QA — Reality Check...")
        qa_report = run_agent(
            self.llm, self.prompts["qa"],
            f"Audit this implementation for quality, correctness, and best practices:\n\n{code}",
            "qa-agent"
        )
        print(f"  ✅  QA report ready ({len(qa_report):,} chars)\n")

        # ── Phase 4: Security Review (full mode only) ─────────────────
        security_report = ""
        if mode == "full":
            print("  🔒  [Phase 4/5] Security Engineer — Threat Review...")
            security_report = run_agent(
                self.llm, self.prompts["security"],
                f"Review this implementation for security vulnerabilities:\n\n{code}",
                "security-agent"
            )
            print(f"  ✅  Security report ready ({len(security_report):,} chars)\n")

        # ── Phase 5: Claude Reasoning Core — Final Gate ───────────────
        print("  🧠  [Phase 5/5] Claude Reasoning Core — Final Judgment...")
        synthesis_query = f"""
Mission: {mission_goal}

You have received outputs from four specialist agents. Perform a final constitutional review and synthesize into a go/no-go verdict with key findings.

--- PROJECT PLAN ---
{plan[:1500]}

--- IMPLEMENTATION (excerpt) ---
{code[:1500]}

--- QA REPORT ---
{qa_report[:1000]}

--- SECURITY REPORT ---
{security_report[:1000] if security_report else 'Not run (fast mode)'}

Your job:
1. Identify any critical issues that block shipping
2. Identify the top 3 things that are working well
3. Give a GO / NO-GO verdict with clear reasoning
4. If NO-GO: specify exactly what must be fixed
"""
        verdict = run_agent(self.llm, self.prompts["core"], synthesis_query, "claude-reasoning-core")

        print(f"\n{'═'*65}")
        print("  🧠  CLAUDE REASONING CORE — FINAL VERDICT")
        print(f"{'═'*65}")
        print(verdict)
        print(f"{'═'*65}\n")

        return {
            "plan": plan,
            "code": code,
            "qa": qa_report,
            "security": security_report,
            "verdict": verdict,
        }


def main():
    parser = argparse.ArgumentParser(description="🧠 Agency Swarm Orchestrator (Claude-Powered)")
    parser.add_argument("--mission", "-m", type=str, required=True, help="Mission goal")
    parser.add_argument("--mode", choices=["full", "fast"], default="full",
                        help="full=all agents, fast=PM+Dev+QA+Core only")
    args = parser.parse_args()

    swarm = AgencySwarm()
    swarm.run_mission(args.mission, mode=args.mode)


if __name__ == "__main__":
    main()
