#!/usr/bin/env python3
"""
run-skill.py — Run any Agency skill as a standalone agent.

Reads a SKILL.md file, extracts the system prompt, and runs it against
the Anthropic API with streaming output. Works with skills installed
via skills.sh or directly from this repo.

Usage:
  python3 scripts/run-skill.py --skill engineering-backend-architect --task "Design a REST API for a todo app"
  python3 scripts/run-skill.py --skill marketing-growth-hacker --task "Growth strategy for a B2B SaaS"
  python3 scripts/run-skill.py --list
  echo "Review this code" | python3 scripts/run-skill.py --skill engineering-code-reviewer --stdin

Requires:
  export ANTHROPIC_API_KEY="sk-ant-..."
  pip install anthropic
"""

import os
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

model = os.environ.get("AGENCY_MODEL", "claude-sonnet-4-6")


def parse_skill_md(path: Path) -> tuple[str, str, str]:
    """Extract name, description, and body from a SKILL.md file."""
    text = path.read_text()
    if not text.startswith("---"):
        return "", "", text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", "", text

    frontmatter = parts[1]
    body = parts[2].strip()

    name = ""
    description = ""
    for line in frontmatter.strip().splitlines():
        if line.startswith("name:"):
            name = line[5:].strip()
        elif line.startswith("description:"):
            description = line[12:].strip()

    return name, description, body


def find_skill(skill_name: str) -> Path | None:
    """Find a SKILL.md by skill name."""
    direct = SKILLS_DIR / skill_name / "SKILL.md"
    if direct.exists():
        return direct

    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                name, _, _ = parse_skill_md(skill_file)
                if name == skill_name:
                    return skill_file

    return None


def list_skills() -> list[tuple[str, str]]:
    """List all available skills."""
    skills = []
    if not SKILLS_DIR.exists():
        return skills

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            name, description, _ = parse_skill_md(skill_file)
            if name:
                skills.append((name, description))
    return skills


def run_agent(system_prompt: str, task: str, stream: bool = True):
    """Run the agent via the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package not installed.", file=sys.stderr)
        print("  pip install anthropic", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        print("  export ANTHROPIC_API_KEY='sk-ant-...'", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    if stream:
        with client.messages.stream(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": task}],
        ) as response:
            for text in response.text_stream:
                print(text, end="", flush=True)
        print()
    else:
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": task}],
        )
        print(response.content[0].text)


def main():
    global model

    parser = argparse.ArgumentParser(
        description="Run any Agency skill as a standalone agent.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  %(prog)s --skill engineering-backend-architect --task 'Design a REST API'\n"
               "  %(prog)s --list\n"
               "  echo 'Review this' | %(prog)s --skill engineering-code-reviewer --stdin",
    )
    parser.add_argument("--skill", "-s", help="Skill name (e.g. engineering-backend-architect)")
    parser.add_argument("--task", "-t", help="Task/prompt to send to the agent")
    parser.add_argument("--stdin", action="store_true", help="Read task from stdin")
    parser.add_argument("--list", "-l", action="store_true", help="List all available skills")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming output")
    parser.add_argument("--model", "-m", help=f"Model to use (default: {model})")
    parser.add_argument("--skill-file", help="Path to a SKILL.md file directly")

    args = parser.parse_args()

    if args.model:
        model = args.model

    if args.list:
        skills = list_skills()
        if not skills:
            print("No skills found. Run: ./scripts/convert.sh --tool skillssh")
            sys.exit(1)
        print(f"Available skills ({len(skills)}):\n")
        current_domain = ""
        for name, desc in skills:
            domain = name.split("-")[0] if "-" in name else "other"
            if domain != current_domain:
                current_domain = domain
                print(f"\n  [{domain}]")
            short_desc = desc[:80] + "..." if len(desc) > 80 else desc
            print(f"    {name:<50} {short_desc}")
        print()
        return

    if not args.skill and not args.skill_file:
        parser.error("--skill or --skill-file is required (or use --list)")

    if args.skill_file:
        skill_path = Path(args.skill_file)
        if not skill_path.exists():
            print(f"Error: file not found: {args.skill_file}", file=sys.stderr)
            sys.exit(1)
    else:
        skill_path = find_skill(args.skill)
        if not skill_path:
            print(f"Error: skill '{args.skill}' not found.", file=sys.stderr)
            print(f"  Run: python3 {sys.argv[0]} --list", file=sys.stderr)
            sys.exit(1)

    name, description, body = parse_skill_md(skill_path)

    if args.stdin:
        task = sys.stdin.read().strip()
    elif args.task:
        task = args.task
    else:
        parser.error("--task or --stdin is required")

    if not task:
        print("Error: empty task.", file=sys.stderr)
        sys.exit(1)

    print(f"Agent: {name}", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)
    print(f"---", file=sys.stderr)

    run_agent(body, task, stream=not args.no_stream)


if __name__ == "__main__":
    main()
