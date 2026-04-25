#!/usr/bin/env python3
"""
Sovereign Ecosystem — Ollama-powered self-evolution cycle.
Observer audits an agent → Refiner rewrites it → Ollama Core approves → DevOps verifies.
"""
import os
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

OLLAMA_MODEL = "llama3.1"

def get_ollama_client():
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    if not base_url:
        print("❌  OLLAMA_BASE_URL not set.")
        sys.exit(1)
    return ChatOllama(model=OLLAMA_MODEL, base_url=base_url)

def load(path): return (REPO_ROOT / path).read_text() if (REPO_ROOT / path).exists() else ""

def run_agent(llm, prompt, query, name):
    agent = create_deep_agent(model=llm, tools=[], system_prompt=prompt, name=name)
    try:
        return agent.invoke({"messages": [HumanMessage(content=query)]})["messages"][-1].content
    except Exception as e:
        print(f"  ❌  Agent '{name}' failed: {type(e).__name__}: {e}")
        return f"[{name} failed: {e}]"

class SovereignEcosystem:
    def __init__(self):
        self.llm = get_ollama_client()
        self.agents = {
            "observer": load("testing/testing-reality-checker.md"),
            "refiner":  load("specialized/specialized-perfect-agent-orchestrator.md"),
            "core":     load("specialized/specialized-claude-reasoning-core.md"),
            "devops":   load("engineering/engineering-ai-engineer.md"),
        }

    def run_evolution_cycle(self, target_agent_path: str):
        target = REPO_ROOT / target_agent_path
        if not target.exists():
            print(f"❌  Agent not found: {target_agent_path}")
            return False

        current = target.read_text()
        print(f"\n{'═'*60}")
        print("  🌌  Sovereign Ecosystem — Evolution Cycle")
        print(f"  🎯  Target: {target_agent_path}")
        print(f"  🧠  Engine: Ollama {OLLAMA_MODEL}")
        print(f"{'═'*60}\n")

        # Phase 1: Observer audits
        print("  🔍  [1/4] Observer — Auditing personality...")
        audit = run_agent(self.llm, self.agents["observer"],
            f"Audit this agent personality for weaknesses, gaps, and outdated practices:\n\n{current}",
            "observer")
        print("  ✅  Audit complete\n")

        # Phase 2: Refiner rewrites
        print("  ✏️   [2/4] Refiner — Optimizing personality...")
        optimized = run_agent(self.llm, self.agents["refiner"],
            f"Rewrite this agent personality to address all audit findings. Return ONLY the improved file.\n\nOriginal:\n{current}\n\nAudit:\n{audit}",
            "refiner")

        if len(optimized) < 300:
            print("  ⚠️   Refiner output too short — aborting")
            return False

        # Phase 3: Ollama Reasoning Core approves
        print("  🧠  [3/4] Ollama Reasoning Core — Constitutional review...")
        verdict = run_agent(self.llm, self.agents["core"],
            f"Review this rewritten agent personality. Is it safe to deploy? GO/NO-GO.\n\nOriginal:\n{current[:800]}\n\nOptimized:\n{optimized[:800]}",
            "ollama-reasoning-core")

        if "no-go" in verdict.lower() or "no go" in verdict.lower():
            print(f"  ❌  Core says NO-GO — aborting\n  Reason: {verdict[:300]}")
            return False
        print("  ✅  Core approved\n")

        # Phase 4: Write + DevOps verify
        backup = target.with_suffix(".md.bak")
        backup.write_text(current)
        target.write_text(optimized)
        print(f"  💾  [4/4] Written to {target_agent_path}")

        run_agent(self.llm, self.agents["devops"],
            f"Verify this updated agent is production-ready:\n{optimized[:1000]}",
            "devops")
        print("  ✅  DevOps verified\n")
        backup.unlink(missing_ok=True)

        print(f"{'═'*60}\n  🏁  Evolution complete: {target.name}\n{'═'*60}\n")
        return True

def main():
    parser = argparse.ArgumentParser(description="🌌 Sovereign Ecosystem — Agent Evolution")
    parser.add_argument("--agent", required=True, help="Path to agent .md file to evolve")
    args = parser.parse_args()
    SovereignEcosystem().run_evolution_cycle(args.agent)

if __name__ == "__main__":
    main()
