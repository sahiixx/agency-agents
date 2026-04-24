#!/usr/bin/env python3
"""
Swarm Stress Test — Claude-powered. Runs PM→Frontend→QA and writes a real file.
Use this to verify the full pipeline works end-to-end with actual file output.
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

CLAUDE_MODEL = "claude-sonnet-4-6"

def get_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    return ChatAnthropic(model=CLAUDE_MODEL, api_key=api_key)

def load(path): return (REPO_ROOT / path).read_text() if (REPO_ROOT / path).exists() else ""

def run_agent(llm, prompt, query, name):
    agent = create_deep_agent(model=llm, tools=[], system_prompt=prompt, name=name)
    try:
        return agent.invoke({"messages": [HumanMessage(content=query)]})["messages"][-1].content
    except Exception as e:
        print(f"  ❌  Agent '{name}' failed: {type(e).__name__}: {e}")
        return f"[{name} failed: {e}]"

def extract_code(response: str) -> str:
    """Pull code block out of LLM response."""
    for fence in ["```tsx", "```typescript", "```jsx", "```"]:
        if fence in response:
            return response.split(fence)[1].split("```")[0].strip()
    return response.strip()

class StressTestSwarm:
    def __init__(self):
        self.llm = get_claude()
        self.agents = {
            "pm":       load("project-management/project-manager-senior.md"),
            "frontend": load("engineering/engineering-frontend-developer.md"),
            "qa":       load("testing/testing-reality-checker.md"),
            "core":     load("specialized/specialized-claude-reasoning-core.md"),
        }

    def run_mission(self, goal: str):
        print(f"\n{'═'*60}")
        print(f"  🔥  Stress Test: {goal}")
        print(f"  🧠  Engine: Claude {CLAUDE_MODEL}")
        print(f"{'═'*60}\n")

        print("  📋  [1/4] PM — Planning...")
        plan = run_agent(self.llm, self.agents["pm"],
            f"Create a detailed execution plan for: {goal}", "pm")
        print("  ✅  Plan ready\n")

        print("  💻  [2/4] Frontend Dev — Building Dashboard.tsx...")
        raw_code = run_agent(self.llm, self.agents["frontend"],
            f"Implement a 'Dashboard.tsx' React component based on this plan:\n{plan}", "frontend")
        code = extract_code(raw_code)

        out_dir = REPO_ROOT / "scaffold/nextjs-tailwind/components"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "Dashboard.tsx").write_text(code)
        print(f"  ✅  Written: scaffold/nextjs-tailwind/components/Dashboard.tsx ({len(code):,} chars)\n")

        print("  🧪  [3/4] QA — Auditing...")
        qa = run_agent(self.llm, self.agents["qa"],
            f"Audit this React component for correctness, accessibility, and best practices:\n{code}", "qa")
        print("  ✅  QA done\n")

        print("  🧠  [4/4] Claude Core — Final verdict...")
        verdict = run_agent(self.llm, self.agents["core"],
            f"Mission: {goal}\n\nReview plan + code + QA. GO/NO-GO?\n\nPlan:\n{plan[:600]}\n\nCode:\n{code[:600]}\n\nQA:\n{qa[:400]}",
            "claude-reasoning-core")

        print(f"\n{'═'*60}\n  🧠  VERDICT\n{'═'*60}")
        print(verdict)
        print(f"\n{'═'*60}\n  🏁  Stress test complete.\n{'═'*60}\n")
        return True

if __name__ == "__main__":
    StressTestSwarm().run_mission(
        "Build a responsive analytics dashboard component for the Next.js scaffold."
    )
