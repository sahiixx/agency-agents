#!/usr/bin/env python3
"""
auto-skill.py — Automatically select and run the best skill for a given goal.

Two-stage selection:
  1. Domain classifier (keywords → engineering/marketing/design/etc.)
  2. LLM picks best skill from that domain

Usage:
  python3 scripts/auto-skill.py "Build a REST API"
  python3 scripts/auto-skill.py --top 3 "Write marketing copy"
  python3 scripts/auto-skill.py --chat "Help me debug this code"
  echo "Design a logo" | python3 scripts/auto-skill.py --stdin
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SKILLS_DIR = REPO_ROOT / "skills"

MODEL = os.environ.get("AGENCY_MODEL", "deepseek-v4-flash:cloud")
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/api/chat"

DOMAIN_KEYWORDS = {
    "engineering": ["code", "build", "develop", "api", "backend", "frontend", "database", "devops", "security", "test", "bug", "debug", "deploy", "server", "app", "software", "system", "architecture", "python", "javascript", "react", "node", "cloud", "infra", "ci/cd", "git", "review", "refactor", "optimize", "performance", "scalable", "microservice", "container", "docker", "kubernetes", "program", "function", "class", "library", "framework", "compile", "runtime", "error", "exception", "traceback", "script", "crashes", "memory leak"],
    "marketing": ["market", "advertise", "campaign", "seo", "social", "content", "copy", "brand", "growth", "lead", "traffic", "promote", "landing page", "email", "ads", "viral", "conversion", "funnel", "copywriting", "messaging", "positioning", "awareness", "engagement", "retention"],
    "design": ["design", "ui", "ux", "visual", "brand", "logo", "mockup", "prototype", "figma", "interface", "user experience", "graphic", "illustration", "wireframe", "design system", "component", "color", "typography", "layout", "icon"],
    "sales": ["sales", "deal", "prospect", "pipeline", "negotiate", "close", "crm", "lead", "quota", "revenue", "pitch", "proposal", "cold call", "outbound", "account", "renewal", "churn", "upsell"],
    "business": ["business", "strategy", "operations", "analytics", "kpi", "forecast", "process", "workflow", "hr", "invoice", "compliance", "b2b", "pricing", "revenue", "consulting", "transformation", "audit", "risk"],
    "real-estate": ["real estate", "property", "listing", "buyer", "seller", "rent", "mortgage", "rera", "dubai", "apartment", "villa", "lease", "valuation", "investment", "agent", "broker"],
    "testing": ["test", "qa", "quality", "audit", "benchmark", "performance", "accessibility", "validate", "verify", "regression", "unit test", "integration test", "e2e", "load test", "stress test", "penetration test"],
    "product": ["product", "feature", "roadmap", "sprint", "backlog", "prioritize", "user story", "mvp", "prd", "requirements", "release", "launch", "feedback", "survey", "interview"],
    "project-management": ["project", "timeline", "milestone", "deliverable", "stakeholder", "scrum", "agile", "plan", "schedule", "jira", "kanban", "resource", "budget", "risk", "dependency", "gantt"],
    "support": ["support", "ticket", "customer service", "help desk", "troubleshoot", "incident", "sla", "escalation", "on-call", "faq", "knowledge base", "chatbot"],
    "game-development": ["game", "unity", "unreal", "godot", "level", "narrative", "gameplay", "multiplayer", "shader", "roblox", "mechanic", "quest", "npc", "asset", "sprite", "texture", "physics", "ai behavior"],
    "paid-media": ["ppc", "ad spend", "programmatic", "media buy", "ctr", "cpc", "roas", "facebook ads", "google ads", "display", "retargeting", "bid", "impression", "click", "conversion tracking"],
    "specialized": ["claude", "prompt", "mcp", "compliance", "linux", "sysadmin", "audit", "reverse engineer", "docs", "learning", "curator", "trust", "graph", "ontology", "embedding", "rag", "vector", "neo4j"],
}


def detect_domain(goal: str) -> str | None:
    """Detect the most likely domain from the goal."""
    goal_lower = goal.lower()
    best_domain = None
    best_score = 0
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in goal_lower)
        if score > best_score:
            best_score = score
            best_domain = domain
    return best_domain if best_score >= 1 else None


def list_skills():
    """Return list of (skill_name, description, domain) tuples."""
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        text = skill_md.read_text()
        desc = ""
        m = re.search(r"^description:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m:
            desc = m.group(1).strip().strip('"').strip("'")
        # Infer domain from name prefix
        domain = "other"
        for d in DOMAIN_KEYWORDS:
            if skill_dir.name.startswith(d):
                domain = d
                break
        skills.append((skill_dir.name, desc, domain))
    return skills


def llm_select_skill(goal: str, candidates: list[tuple[str, str]]) -> str | None:
    """Ask the LLM to pick the best skill from candidates."""
    skill_list = "\n".join([f"- {name}: {desc[:140]}" for name, desc in candidates])
    prompt = (
        f"Goal: {goal}\n\n"
        f"Candidate skills:\n{skill_list}\n\n"
        f"Which single skill is the BEST match for this goal? "
        f"Respond with ONLY the exact skill name (before the colon). No explanation."
    )
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            obj = json.loads(resp.read())
        reply = obj.get("message", {}).get("content", "").strip()
        for name, _ in candidates:
            if name in reply or reply == name:
                return name
        return None
    except Exception as e:
        print(f"LLM selection failed: {e}", file=sys.stderr)
        return None


def run_skill(skill_name: str, task: str, *, chat: bool = False, tools: bool = False):
    """Invoke run-skill.py for the given skill."""
    cmd = [sys.executable, str(SCRIPTS_DIR / "run-skill.py"), "--skill", skill_name]
    if chat:
        cmd.append("--chat")
    elif task:
        cmd.extend(["--task", task])
    if tools:
        cmd.append("--tools")
    env = os.environ.copy()
    env["AGENCY_MODEL"] = MODEL
    subprocess.run(cmd, env=env)


def main():
    parser = argparse.ArgumentParser(
        description="Auto-select and run the best skill for your goal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s 'Build a REST API'\n"
               "  %(prog)s --top 3 'Write landing page copy'\n"
               "  %(prog)s --chat 'Help me design a database schema'\n"
               "  echo 'Debug this Python function' | %(prog)s --stdin",
    )
    parser.add_argument("goal", nargs="?", help="What you need (natural language)")
    parser.add_argument("--top", "-n", type=int, default=1, help="Run top N matching skills (default: 1)")
    parser.add_argument("--chat", "-c", action="store_true", help="Enter interactive chat with the best skill")
    parser.add_argument("--tools", "-t", action="store_true", help="Enable tool use (web search, file read)")
    parser.add_argument("--stdin", "-s", action="store_true", help="Read goal from stdin")
    parser.add_argument("--list-matches", "-l", action="store_true", help="Only show candidates, don't run")
    parser.add_argument("--keyword", "-k", action="store_true", help="Use keyword-only matching (no LLM)")

    args = parser.parse_args()

    if args.stdin:
        goal = sys.stdin.read().strip()
    elif args.goal:
        goal = args.goal
    else:
        parser.error("Provide a goal or use --stdin")

    if not goal:
        print("Error: empty goal.", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing goal: {goal}\n")
    skills = list_skills()
    domain = detect_domain(goal)

    if domain:
        candidates = [(name, desc) for name, desc, d in skills if d == domain]
        print(f"Detected domain: {domain} ({len(candidates)} skills)\n")
    else:
        # Fallback: include all skills
        candidates = [(name, desc) for name, desc, _ in skills]
        print(f"No specific domain detected. Checking all {len(candidates)} skills.\n")

    if not candidates:
        print("No matching skills found.", file=sys.stderr)
        sys.exit(1)

    if args.list_matches:
        print(f"Candidate skills:\n")
        for i, (name, desc) in enumerate(candidates[:20], 1):
            short = desc[:90] + "..." if len(desc) > 90 else desc
            print(f"  {i}. {name}\n     {short}")
        if len(candidates) > 20:
            print(f"  ... and {len(candidates) - 20} more")
        return

    if args.keyword:
        # Simple keyword scoring within domain
        goal_lower = goal.lower()
        goal_words = set(re.findall(r"[a-z0-9]+", goal_lower))
        scored = []
        for name, desc in candidates:
            score = 0.0
            name_words = set(re.findall(r"[a-z0-9]+", name.lower()))
            for w in goal_words:
                if w in name_words:
                    score += 3.0
            if desc:
                desc_words = set(re.findall(r"[a-z0-9]+", desc.lower()))
                for w in goal_words:
                    if w in desc_words:
                        score += 0.5
            scored.append((score, name, desc))
        scored.sort(reverse=True)
        selected = scored[:args.top]
    else:
        if args.top == 1:
            # Send domain candidates to LLM for best match
            selected_name = llm_select_skill(goal, candidates)
            if selected_name:
                desc = dict(candidates).get(selected_name, "")
                selected = [(0, selected_name, desc)]
                print(f"LLM selected: {selected_name}\n")
            else:
                print("LLM selection failed, using keyword fallback.\n", file=sys.stderr)
                goal_lower = goal.lower()
                goal_words = set(re.findall(r"[a-z0-9]+", goal_lower))
                scored = []
                for name, desc in candidates:
                    score = sum(1 for w in goal_words if w in name.lower()) * 3.0
                    scored.append((score, name, desc))
                scored.sort(reverse=True)
                selected = scored[:1]
        else:
            # Multi-skill: keyword scoring within domain
            goal_lower = goal.lower()
            goal_words = set(re.findall(r"[a-z0-9]+", goal_lower))
            scored = []
            for name, desc in candidates:
                score = sum(1 for w in goal_words if w in name.lower()) * 3.0
                scored.append((score, name, desc))
            scored.sort(reverse=True)
            selected = scored[:args.top]

    if not selected:
        print("No matching skills found.", file=sys.stderr)
        sys.exit(1)

    if len(selected) == 1:
        score, name, desc = selected[0]
        print(f"Auto-selected skill: {name}\n")
        run_skill(name, goal, chat=args.chat, tools=args.tools)
    else:
        for i, (score, name, desc) in enumerate(selected, 1):
            print(f"\n{'='*60}")
            print(f"[{i}/{len(selected)}] Running skill: {name}")
            print(f"{'='*60}\n")
            run_skill(name, goal, chat=False, tools=args.tools)


if __name__ == "__main__":
    main()
