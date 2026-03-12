#!/usr/bin/env python3
"""
SaaS Dominance Swarm — Claude-powered 4-agent pipeline.
PM → Copywriter → Frontend Dev → QA → Claude Reasoning Core verdict
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

class SaasSwarm:
    def __init__(self):
        self.llm = get_claude()
        self.agents = {
            "pm":     load("project-management/project-manager-senior.md"),
            "copy":   load("marketing/marketing-growth-hacker.md"),
            "frontend": load("engineering/engineering-frontend-developer.md"),
            "qa":     load("testing/testing-reality-checker.md"),
            "core":   load("specialized/specialized-claude-reasoning-core.md"),
        }

    def run_mission(self, goal: str):
        print(f"\n{'═'*60}\n  🚀  SaaS Dominance Mission: {goal}\n  🧠  Engine: Claude {CLAUDE_MODEL}\n{'═'*60}\n")

        print("  📋  [1/5] PM — Strategic Planning...")
        plan = run_agent(self.llm, self.agents["pm"], f"Create a SaaS architecture plan for: {goal}", "pm")
        print(f"  ✅  Plan ready\n")

        print("  ✍️   [2/5] Growth Hacker — Marketing Copy...")
        copy = run_agent(self.llm, self.agents["copy"], f"Write high-conversion landing page copy for this SaaS:\n{plan}", "copy")
        print(f"  ✅  Copy ready\n")

        print("  💻  [3/5] Frontend Dev — UI Implementation...")
        code = run_agent(self.llm, self.agents["frontend"], f"Implement the landing page UI.\nPlan: {plan}\nCopy: {copy}", "frontend")

        out_dir = REPO_ROOT / "scaffold/nextjs-tailwind/pages"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "saas-landing.tsx").write_text(code)
        print(f"  ✅  Code saved to scaffold/nextjs-tailwind/pages/saas-landing.tsx\n")

        print("  🧪  [4/5] QA — Reality Check...")
        qa = run_agent(self.llm, self.agents["qa"], f"Audit for SEO, accessibility, and conversion:\n{code}", "qa")
        print(f"  ✅  QA done\n")

        print("  🧠  [5/5] Claude Reasoning Core — Final Verdict...")
        verdict = run_agent(self.llm, self.agents["core"],
            f"Mission: {goal}\n\nPlan:\n{plan[:800]}\n\nCopy:\n{copy[:800]}\n\nCode:\n{code[:800]}\n\nQA:\n{qa[:600]}\n\nGive GO/NO-GO verdict with key findings.", "core")

        print(f"\n{'═'*60}\n  🧠  FINAL VERDICT\n{'═'*60}")
        print(verdict)
        print(f"{'═'*60}\n  🏁  SaaS Dominance Mission Complete.\n{'═'*60}\n")

if __name__ == "__main__":
    SaasSwarm().run_mission("Build a high-conversion SaaS Landing Page for an AI Agent Agency.")
