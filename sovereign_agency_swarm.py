#!/usr/bin/env python3
"""
Sovereign Agency Swarm — Claude-powered 6-agent full-stack pipeline.
PM → Backend → AI Engineer → Frontend → QA → Claude Reasoning Core
"""
import os, sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

CLAUDE_MODEL = "claude-sonnet-4-6"

def get_claude() -> object:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY not set."); sys.exit(1)
    return ChatAnthropic(model=CLAUDE_MODEL, api_key=api_key)

def load(path: str) -> str: return (REPO_ROOT / path).read_text() if (REPO_ROOT / path).exists() else ""

def run_agent(llm, prompt: str, query: str, name: str) -> str:
    agent = create_deep_agent(model=llm, tools=[], system_prompt=prompt, name=name)
    try:
        return agent.invoke({"messages": [HumanMessage(content=query)]})["messages"][-1].content
    except Exception as e:
        print(f"  ❌  Agent '{name}' failed: {type(e).__name__}: {e}")
        return f"[{name} failed: {e}]"

class SovereignSwarm:
    def __init__(self):
        self.llm = get_claude()
        self.agents = {
            "pm":       load("project-management/project-manager-senior.md"),
            "backend":  load("engineering/engineering-backend-architect.md"),
            "ai":       load("engineering/engineering-ai-engineer.md"),
            "frontend": load("engineering/engineering-frontend-developer.md"),
            "qa":       load("testing/testing-reality-checker.md"),
            "core":     load("specialized/specialized-claude-reasoning-core.md"),
        }

    def run_mission(self, goal: str):
        print(f"\n{'═'*60}\n  👑  Sovereign Mission: {goal}\n  🧠  Engine: Claude {CLAUDE_MODEL}\n{'═'*60}\n")

        print("  📋  [1/6] PM — Full-Stack Architecture...")
        plan = run_agent(self.llm, self.agents["pm"],
            f"Create a production-ready full-stack architecture for: {goal}. Include DB schema and API route definitions.", "pm")
        print("  ✅  Plan ready\n")

        print("  🏗️   [2/6] Backend Architect — API & DB Design...")
        backend = run_agent(self.llm, self.agents["backend"],
            f"Design the Prisma schema and API routes for:\n{plan}", "backend")
        print("  ✅  Backend ready\n")

        print("  🤖  [3/6] AI Engineer — Agent Logic...")
        ai_logic = run_agent(self.llm, self.agents["ai"],
            f"Implement the core AI agent orchestration logic for:\n{plan}", "ai")
        print("  ✅  AI logic ready\n")

        print("  💻  [4/6] Frontend Dev — Dashboard UI...")
        frontend = run_agent(self.llm, self.agents["frontend"],
            f"Implement the Next.js dashboard UI.\nPlan: {plan}\nBackend: {backend}", "frontend")

        scaffold = REPO_ROOT / "scaffold/sovereign-platform"
        for d in ["api", "components", "ai"]:
            (scaffold / d).mkdir(parents=True, exist_ok=True)
        (scaffold / "schema.prisma").write_text(backend)
        (scaffold / "ai/orchestrator.ts").write_text(ai_logic)
        (scaffold / "components/Dashboard.tsx").write_text(frontend)
        print("  ✅  All components saved to scaffold/sovereign-platform/\n")

        print("  🧪  [5/6] QA — Audit...")
        qa = run_agent(self.llm, self.agents["qa"],
            f"Audit this full-stack platform for security, performance, reliability.\nFrontend: {frontend[:1000]}\nBackend: {backend[:1000]}", "qa")
        print("  ✅  QA done\n")

        print("  🧠  [6/6] Claude Reasoning Core — Final Verdict...")
        verdict = run_agent(self.llm, self.agents["core"],
            f"Mission: {goal}\n\nReview all agent outputs and give GO/NO-GO with key findings.\n\nPlan:\n{plan[:600]}\nBackend:\n{backend[:600]}\nAI Logic:\n{ai_logic[:600]}\nFrontend:\n{frontend[:600]}\nQA:\n{qa[:600]}", "core")

        print(f"\n{'═'*60}\n  🧠  FINAL VERDICT\n{'═'*60}")
        print(verdict)
        print(f"\n{'═'*60}\n  🏁  Sovereign Mission Complete.\n{'═'*60}\n")

if __name__ == "__main__":
    SovereignSwarm().run_mission(
        "Build a production-ready AI Agent Management Platform with multi-agent swarming, live monitoring, and automated deployment."
    )
