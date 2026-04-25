#!/usr/bin/env python3
"""
The Agency — Mission Control CLI
Powered by Ollama (local) as the Reasoning Core.
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure deepagents SDK is on the path
REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

from deepagents import create_deep_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# ─── Constants ────────────────────────────────────────────────────────────────

OLLAMA_MODEL = "llama3.1"
OLLAMA_BASE_URL = "http://localhost:11434"
REASONING_CORE_PATH = "specialized/specialized-claude-reasoning-core.md"

AGENT_DIRS = [
    "engineering", "design", "marketing", "specialized", "sales",
    "product", "testing", "support", "strategy", "project-management",
    "paid-media", "game-development", "spatial-computing",
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_ollama():
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)


def parse_frontmatter(path: str) -> dict:
    meta = {"name": Path(path).stem, "description": "", "emoji": "🤖", "color": ""}
    try:
        with open(path) as f:
            content = f.read()
        if content.startswith("---"):
            fm = content.split("---")[1]
            for line in fm.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"')
    except Exception:
        pass
    return meta


def list_agents(filter_dir=None):
    agents = []
    for d in AGENT_DIRS:
        if filter_dir and filter_dir not in d:
            continue
        dir_path = REPO_ROOT / d
        if not dir_path.exists():
            continue
        for md_file in sorted(dir_path.rglob("*.md")):
            rel = str(md_file.relative_to(REPO_ROOT))
            meta = parse_frontmatter(str(md_file))
            meta["path"] = rel
            agents.append(meta)
    return agents


def load_agent_prompt(agent_path: str) -> str:
    full = REPO_ROOT / agent_path
    if not full.exists():
        print(f"❌  Agent file not found: {agent_path}")
        sys.exit(1)
    return full.read_text()


def load_reasoning_core_prompt() -> str:
    core_path = REPO_ROOT / REASONING_CORE_PATH
    return core_path.read_text() if core_path.exists() else ""


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_list(args):
    agents = list_agents(filter_dir=getattr(args, 'filter', None))
    print(f"\n{'─'*60}")
    print(f"  🧠  The Agency — {len(agents)} agents available")
    print(f"{'─'*60}")
    current_dir = None
    for a in agents:
        d = Path(a["path"]).parent
        if d != current_dir:
            current_dir = d
            print(f"\n  📁  {str(d).upper()}")
        emoji = a.get("emoji", "🤖")
        name = a.get("name", a["path"])
        desc = a.get("description", "")[:70]
        print(f"     {emoji}  {name}")
        if desc:
            print(f"         {desc}")
    print()


def cmd_launch(args):
    llm = get_ollama()
    agent_prompt = load_agent_prompt(args.agent)
    meta = parse_frontmatter(str(REPO_ROOT / args.agent))

    if args.agent != REASONING_CORE_PATH:
        core_prompt = load_reasoning_core_prompt()
        system = f"{agent_prompt}\n\n---\n\n## Reasoning Backbone\n{core_prompt}" if core_prompt else agent_prompt
    else:
        system = agent_prompt

    print(f"\n{'─'*60}")
    print(f"  {meta.get('emoji','🤖')}  Launching: {meta.get('name', args.agent)}")
    print(f"  🧠  Model: {OLLAMA_MODEL} (Ollama)")
    print(f"  📋  Query: {args.query}")
    print(f"{'─'*60}\n")

    agent = create_deep_agent(model=llm, tools=[], system_prompt=system, name=meta.get("name", "agency-agent"))
    response = agent.invoke({"messages": [HumanMessage(content=args.query)]})

    print("Response:\n")
    print(response["messages"][-1].content)
    print(f"\n{'─'*60}")


def cmd_reason(args):
    llm = get_ollama()
    core_prompt = load_reasoning_core_prompt()

    print(f"\n{'─'*60}")
    print("  🧠  Ollama Reasoning Core — Direct Mode")
    print(f"  📋  Query: {args.query}")
    print(f"{'─'*60}\n")

    agent = create_deep_agent(model=llm, tools=[], system_prompt=core_prompt, name="claude-reasoning-core")
    response = agent.invoke({"messages": [HumanMessage(content=args.query)]})

    print("Reasoning Output:\n")
    print(response["messages"][-1].content)
    print(f"\n{'─'*60}")


def cmd_info(args):
    meta = parse_frontmatter(str(REPO_ROOT / args.info))
    prompt = load_agent_prompt(args.info)
    print(f"\n{'─'*60}")
    print(f"  {meta.get('emoji','🤖')}  {meta.get('name', args.info)}")
    print(f"  📝  {meta.get('description','')}")
    print(f"  💬  Vibe: {meta.get('vibe','')}")
    print(f"  📄  Path: {args.info}")
    print(f"  📏  Prompt: {len(prompt):,} chars")
    print(f"{'─'*60}\n")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🧠 The Agency — Mission Control (Ollama-Powered)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 mission_control.py --list
  python3 mission_control.py --list --filter engineering
  python3 mission_control.py --launch engineering/engineering-frontend-developer.md --query "Build a login form"
  python3 mission_control.py --reason --query "Is this copy ethical?"
  python3 mission_control.py --info specialized/specialized-claude-reasoning-core.md
        """
    )

    parser.add_argument("--list", action="store_true")
    parser.add_argument("--filter", type=str)
    parser.add_argument("--launch", dest="agent", type=str)
    parser.add_argument("--reason", action="store_true")
    parser.add_argument("--info", type=str, metavar="AGENT")
    parser.add_argument("--query", "-q", type=str)

    args = parser.parse_args()

    if args.list:
        cmd_list(args)
    elif args.agent and args.query:
        cmd_launch(args)
    elif args.reason and args.query:
        cmd_reason(args)
    elif args.info:
        cmd_info(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
