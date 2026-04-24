#!/usr/bin/env python3
"""
Evolution Scheduler — Randomly selects an agent and runs Claude Reasoning Core
to critique and improve it, then commits the improved version to git.
"""
import os
import sys
import random
import subprocess
import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

CLAUDE_MODEL = "claude-sonnet-4-6"
EXCLUDED = {'.git', 'node_modules', 'deepagents', 'integrations', 'scaffold', 'tests', 'scripts'}
SKIP_FILES = {'README.md', 'CONTRIBUTING.md', 'LICENSE.md', 'AGENTS.md', 'README_DEEPAGENTS.md', 'README_CLAUDE.md'}

def get_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌  ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    return ChatAnthropic(model=CLAUDE_MODEL, api_key=api_key)

def get_all_agents():
    agents = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED]
        for f in files:
            if f.endswith('.md') and f not in SKIP_FILES:
                agents.append(Path(root) / f)
    return agents

def evolve_agent(llm, agent_path: Path) -> str:
    """Use Claude Reasoning Core to critique and rewrite an agent's personality."""
    core_prompt = (REPO_ROOT / "specialized/specialized-claude-reasoning-core.md").read_text()
    original = agent_path.read_text()

    query = f"""You are reviewing and improving an agent personality file.

ORIGINAL AGENT:
{original}

Your task:
1. Identify weaknesses: vague instructions, missing edge cases, unclear scope, or anything that would make this agent less effective
2. Rewrite the full agent file with improvements — same format, same frontmatter, but sharper, clearer, more capable
3. Return ONLY the improved agent file content, nothing else

Be surgical. Preserve what works. Improve what doesn't."""

    agent = create_deep_agent(model=llm, tools=[], system_prompt=core_prompt, name="evolution-core")
    response = agent.invoke({"messages": [HumanMessage(content=query)]})
    return response["messages"][-1].content

def run_tests():
    try:
        subprocess.run([sys.executable, "tests/agent_tests.py"], check=True, cwd=REPO_ROOT)
        return True
    except subprocess.CalledProcessError:
        return False

def commit(agent_path: Path):
    name = agent_path.name
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    cmds = [
        ["git", "add", str(agent_path.relative_to(REPO_ROOT))],
        ["git", "commit", "-m", f"🧠 Claude Evolution: {name} [{ts}]"],
    ]
    for cmd in cmds:
        subprocess.run(cmd, check=True, cwd=REPO_ROOT)
    print(f"  ✅  Committed: {name}")

def main():
    llm = get_claude()
    agents = get_all_agents()

    if not agents:
        print("No agents found.")
        return

    target = random.choice(agents)
    print(f"\n{'═'*60}")
    print(f"  🧬  Evolution Cycle — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  🎯  Target: {target.relative_to(REPO_ROOT)}")
    print(f"  🧠  Engine: Claude {CLAUDE_MODEL}")
    print(f"{'═'*60}\n")

    original = target.read_text()

    print("  🔬  Running Claude Reasoning Core critique & rewrite...")
    improved = evolve_agent(llm, target)

    if len(improved) < 200:
        print("  ⚠️   Output too short — skipping write. Likely a refusal or error.")
        return

    # Backup original
    backup = target.with_suffix(".md.bak")
    backup.write_text(original)

    # Write improvement
    target.write_text(improved)
    print(f"  ✅  Agent improved ({len(original):,} → {len(improved):,} chars)\n")

    print("  🧪  Running test suite...")
    if run_tests():
        print("  ✅  Tests passed")
        commit(target)
        backup.unlink(missing_ok=True)
        print(f"\n  🏁  Evolution complete: {target.name}")
    else:
        print("  ❌  Tests failed — reverting")
        target.write_text(original)
        backup.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
