#!/usr/bin/env python3
"""
self_evolve_loop.py — Autonomous Agent Evolution for The Agency.

AGI capability: a cron-able daemon that continuously improves the agency's agents.
Instead of manually evolving one agent at a time, this runs in the background,
selecting the weakest/most-outdated agents for improvement each cycle.

Key idea: autonomous self-improvement is a core AGI requirement —
the system should get better at its tasks over time without human intervention.

How it works per cycle:
  1. Score all agents (prompt quality metrics)
  2. Select the N lowest-scoring agents for evolution
  3. For each selected agent:
     a. Ollama critiques the current prompt
     b. Ollama generates an improved version
     c. Original is backed up
     d. New prompt replaces the old one
  4. Run test suite
  5. If tests pass: commit improvements
  6. If tests fail: revert

Usage:
  # Single cycle
  python3 self_evolve_loop.py

  # Daemon mode (runs every N minutes)
  python3 self_evolve_loop.py --daemon --interval 60

  # Dry run (show what would happen, no writes)
  python3 self_evolve_loop.py --dry-run --max-agents 5
"""

import json
import os
import subprocess
import sys
import time
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.resolve()

# Scoring weights
WEIGHT_CHARS = 0.15        # Prefer 500-5000 char prompts
WEIGHT_SECTIONS = 0.25     # Must have Core Mission, Quality Standards
WEIGHT_FRONTMATTER = 0.15  # Must have valid frontmatter
WEIGHT_TOOLS = 0.10        # Should mention available tools
WEIGHT_VIBE = 0.10         # Should have a vibe line
WEIGHT_AGE = 0.25          # Older prompts score lower (favor evolution)

REQUIRED_SECTIONS = [
    "Core Mission",
    "Quality Standards",
    "Identity",
]

DESIRED_SECTIONS = [
    "Collaboration",
    "Boundaries",
    "Tools",
]

EXCLUDED_FILES = {
    "README.md", "CONTRIBUTING.md", "LICENSE.md", "AGENTS.md",
    "SECURITY.md", "README_DEEPAGENTS.md", "README_CLAUDE.md",
    "ARCHITECTURE.md", "REAL_ESTATE_SWARM.md", "SECURITY_AUDIT_SWARM.md",
    "SECURITY_AUDIT_QUICK_REFERENCE.md",
}

EXCLUDED_DIRS = {'.git', 'node_modules', '__pycache__', 'deepagents',
                 'integrations', 'scaffold', 'tests', 'scripts',
                 'synthesized_tools', 'data', 'memory', 'dashboard'}


def get_agent_files() -> list[Path]:
    """Get all agent .md files from the repo."""
    agents = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in files:
            if f.endswith(".md") and f not in EXCLUDED_FILES:
                agents.append(Path(root) / f)
    return agents


def score_agent(prompt_path: Path, now: datetime) -> dict:
    """
    Score an agent prompt on multiple quality dimensions.

    Returns dict with score (0-100) and per-dimension breakdown.
    """
    content = prompt_path.read_text()
    lines = content.split("\n")
    char_count = len(content)
    line_count = len(lines)

    score = 0.0
    details = {}

    # 1. Char count score
    if 500 <= char_count <= 5000:
        chars_score = 1.0
    elif char_count < 200:
        chars_score = 0.0
    elif char_count < 500:
        chars_score = char_count / 500
    elif char_count > 10000:
        chars_score = max(0, 1 - (char_count - 5000) / 10000)
    else:
        chars_score = 1.0
    score += chars_score * WEIGHT_CHARS
    details["char_count"] = {"score": round(chars_score, 3), "value": char_count}

    # 2. Required sections score
    found_sections = 0
    for section in REQUIRED_SECTIONS:
        if section.lower() in content.lower():
            found_sections += 1
    sections_score = found_sections / len(REQUIRED_SECTIONS)
    score += sections_score * WEIGHT_SECTIONS
    details["sections"] = {"score": round(sections_score, 3),
                           "found": found_sections, "required": len(REQUIRED_SECTIONS)}

    # 3. Desired sections
    desired_found = sum(1 for s in DESIRED_SECTIONS if s.lower() in content.lower())
    desired_score = desired_found / len(DESIRED_SECTIONS)
    score += desired_score * 0.10  # bonus for extra sections
    details["desired_sections"] = {"score": round(desired_score, 3),
                                    "found": desired_found}

    # 4. Frontmatter validity
    has_frontmatter = content.startswith("---")
    has_name = "name:" in content[:500]
    has_desc = "description:" in content[:500]
    fm_score = 0.0
    if has_frontmatter:
        fm_score += 0.5
    if has_name:
        fm_score += 0.25
    if has_desc:
        fm_score += 0.25
    score += fm_score * WEIGHT_FRONTMATTER
    details["frontmatter"] = {"score": round(fm_score, 3),
                               "has_frontmatter": has_frontmatter,
                               "has_name": has_name, "has_desc": has_desc}

    # 5. Tools mention
    has_tools = any(t in content.lower() for t in ["web_search", "write_output",
                                                    "memory_recall", "read_file"])
    tools_score = 1.0 if has_tools else 0.0
    score += tools_score * WEIGHT_TOOLS
    details["tools"] = {"score": tools_score, "has_tools": has_tools}

    # 6. Vibe line
    has_vibe = "vibe:" in content[:500]
    vibe_score = 1.0 if has_vibe else 0.0
    score += vibe_score * WEIGHT_VIBE
    details["vibe"] = {"score": vibe_score, "has_vibe": has_vibe}

    # 7. Age score (files older than 30 days score lower)
    try:
        mtime = os.path.getmtime(prompt_path)
        age_days = (now.timestamp() - mtime) / 86400
        age_score = max(0, 1 - age_days / 90)  # 90 days to decay to 0
    except OSError:
        age_score = 0.5
    score += age_score * WEIGHT_AGE
    details["age"] = {"score": round(age_score, 3), "age_days": round(age_days, 1) if 'age_days' in dir() else 0}

    # Normalize to 0-100
    final_score = round(score * 100, 1)
    details["total"] = final_score

    return {
        "path": str(prompt_path),
        "name": prompt_path.stem,
        "score": final_score,
        "char_count": char_count,
        "line_count": line_count,
        "details": details,
    }


def evolve_agent(agent_path: Path, agent_name: str, dry_run: bool = False) -> Optional[str]:
    """
    Use Ollama to critique and improve a single agent prompt.
    Returns the improved text, or None on failure.

    In dry_run mode, returns expected improvement without calling LLM.
    """
    original = agent_path.read_text()

    if dry_run:
        return f"[DRY RUN] Would evolve: {agent_name} ({len(original)} chars)"

    try:
        sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))
        from deepagents import create_deep_agent
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage

        core_prompt = (REPO_ROOT / "specialized/specialized-claude-reasoning-core.md").read_text()
        llm = ChatOllama(model="llama3.1", base_url="http://localhost:11434")

        query = textwrap.dedent(f"""\
        You are reviewing and improving an agent personality file.

        ORIGINAL AGENT: {agent_name}
        ```markdown
        {original}
        ```

        Your task:
        1. Identify weaknesses: vague instructions, missing edge cases, unclear scope,
           missing sections, poor structure, anything that would make this agent less effective
        2. Rewrite the full agent file with improvements — same format (frontmatter + markdown),
           same name and description, but sharper, clearer, more capable
        3. Ensure: Core Mission, Identity, Quality Standards, Collaboration, Boundaries
        4. Keep the personality and vibe — improve clarity and capability, don't change identity
        5. Return ONLY the improved agent file content in a markdown code block, nothing else

        Be surgical. Preserve what works. Improve what doesn't.
        """)

        agent = create_deep_agent(model=llm, tools=[],
                                  system_prompt=core_prompt,
                                  name="evolution-core")
        response = agent.invoke({"messages": [HumanMessage(content=query)]})
        improved = response["messages"][-1].content

        # Extract code block if present
        if "```" in improved:
            parts = improved.split("```")
            # Take middle part (between fences)
            for i, p in enumerate(parts):
                if p.strip() and not p.strip().startswith("markdown") and not p.strip().startswith("md"):
                    if i > 0 and (parts[i-1].strip().startswith("markdown") or parts[i-1].strip().startswith("md")):
                        improved = p.strip()
                        break
                    elif p.strip() != improved.strip():
                        # Try the longest code block
                        if len(p) > len(improved) // 2:
                            improved = p.strip()
                            break

        # Strip leading markdown/md fence labels
        improved = improved.strip()
        for prefix in ["markdown\n", "md\n"]:
            if improved.startswith(prefix):
                improved = improved[len(prefix):]

        if len(improved) < 200:
            print(f"  ⚠️   Output too short ({len(improved)} chars) — skipping")
            return None

        return improved

    except Exception as e:
        print(f"  ❌  Evolution error for '{agent_name}': {e}")
        return None


def run_tests() -> bool:
    """Run the test suite. Returns True on success."""
    try:
        result = subprocess.run(
            [sys.executable, "tests/agent_tests.py"],
            capture_output=True, text=True, timeout=120,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            print(f"  ❌  Tests failed:\n{result.stdout[-500:]}\n{result.stderr[-500:]}")
            return False
        print(f"  ✅  Tests passed")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ⚠️   Tests timed out")
        return False
    except Exception as e:
        print(f"  ❌  Test error: {e}")
        return False


def commit_improvement(agent_path: Path, original: str, improved: str, agent_name: str) -> bool:
    """Commit the improved agent to git."""
    try:
        rel_path = agent_path.relative_to(REPO_ROOT)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Backup original
        backup = agent_path.with_suffix(".md.bak")
        backup.write_text(original)

        # Write improved
        agent_path.write_text(improved)

        # Git add & commit
        cmds = [
            ["git", "add", str(rel_path)],
            ["git", "commit", "-m", f"🧬 Auto-evolution: {agent_name} [{ts}]"],
        ]
        for cmd in cmds:
            subprocess.run(cmd, check=True, cwd=REPO_ROOT,
                           capture_output=True, timeout=30)

        # Remove backup
        backup.unlink(missing_ok=True)

        print(f"  ✅  Committed: {agent_name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"  ⚠️   Git error: {e.stderr.decode() if e.stderr else e}")
        # Revert
        if backup.exists():
            agent_path.write_text(original)
            backup.unlink()
        return False
    except Exception as e:
        print(f"  ❌  Commit error: {e}")
        return False


def run_evolution_cycle(
    max_agents: int = 3,
    min_score: float = 50.0,
    dry_run: bool = False,
    test_after: bool = True,
) -> dict:
    """
    Run one evolution cycle:

    1. Score all agents
    2. Select N lowest-scoring agents
    3. Evolve each one
    4. Test and commit

    Returns stats dict.
    """
    now = datetime.now()
    agents = get_agent_files()
    print(f"\n{'═'*65}")
    print(f"  🧬  Evolution Cycle — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"  📊  Agents evaluated: {len(agents)}")
    print(f"{'═'*65}")

    # Score all agents
    scored = []
    for path in agents:
        result = score_agent(path, now)
        scored.append(result)

    # Sort by score (ascending — lowest first)
    scored.sort(key=lambda s: s["score"])

    # Print score distribution
    scores = [s["score"] for s in scored]
    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"\n  Score distribution:")
    print(f"    Average: {avg_score:.1f}")
    print(f"    Min:     {min(scores):.1f}")
    print(f"    Max:     {max(scores):.1f}")

    # Select candidates below threshold
    candidates = [s for s in scored if s["score"] < min_score][:max_agents]

    if not candidates:
        print(f"\n  ✅  No agents below threshold ({min_score}). All agents are healthy.")
        return {
            "cycle": now.isoformat(),
            "total_agents": len(agents),
            "avg_score": round(avg_score, 1),
            "evolved": 0,
            "status": "no_candidates",
        }

    print(f"\n  🎯  Candidates for evolution ({len(candidates)}):")
    for c in candidates:
        print(f"      {c['name']:<25} score={c['score']:>5.1f}  ({c['char_count']:,} chars)")

    # Evolve each candidate
    evolved_count = 0
    for candidate in candidates:
        path = Path(candidate["path"])
        name = candidate["name"]

        print(f"\n  🔬  Evolving: {name} (score={candidate['score']})")

        original = path.read_text()
        improved = evolve_agent(path, name, dry_run=dry_run)

        if not improved:
            print(f"      Skipping '{name}' — no improvement generated")
            continue

        if dry_run:
            print(f"      {improved[:100]}...")
            continue

        # Save and test
        backup = path.with_suffix(".md.bak")
        backup.write_text(original)
        path.write_text(improved)

        if test_after:
            print(f"      Running tests...")
            if run_tests():
                # Commit
                if commit_improvement(path, original, improved, name):
                    evolved_count += 1
                else:
                    # Revert
                    path.write_text(original)
                    print(f"      ⚠️   Reverted '{name}' — commit failed")
            else:
                # Revert
                path.write_text(original)
                print(f"      ⚠️   Reverted '{name}' — tests failed")
        else:
            # Skip tests, just save
            evolved_count += 1
            print(f"      ✅  Saved improvement (testing skipped)")

        # Clean up backup
        backup.unlink(missing_ok=True)

    print(f"\n{'═'*65}")
    print(f"  🏁  Cycle complete: {evolved_count}/{len(candidates)} agents evolved")
    print(f"{'═'*65}")

    return {
        "cycle": now.isoformat(),
        "total_agents": len(agents),
        "avg_score": round(avg_score, 1),
        "candidates": len(candidates),
        "evolved": evolved_count,
        "status": "complete",
    }


# ── Daemon Mode ───────────────────────────────────────────────────────────────

def daemon_loop(interval_minutes: int = 60, max_agents: int = 3, dry_run: bool = False):
    """Run evolution cycles in an infinite loop with given interval."""
    print(f"\n  ⏰  Evolution Daemon starting (every {interval_minutes} min)")
    print(f"      Max agents per cycle: {max_agents}")
    if dry_run:
        print(f"      DRY RUN — no files will be modified")

    cycle_num = 0
    while True:
        cycle_num += 1
        print(f"\n{'='*65}")
        print(f"  Daemon Cycle #{cycle_num}")
        print(f"{'='*65}")

        try:
            run_evolution_cycle(
                max_agents=max_agents,
                dry_run=dry_run,
                test_after=not dry_run,
            )
        except KeyboardInterrupt:
            print(f"\n  Daemon interrupted. Exiting cleanly.")
            break
        except Exception as e:
            print(f"\n  ❌  Cycle error: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n  Sleeping for {interval_minutes} minutes...")
        print(f"  Next cycle at: {datetime.now().strftime('%H:%M')} +{interval_minutes}min")

        try:
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print(f"\n  Daemon interrupted. Exiting cleanly.")
            break

    print(f"\n  Daemon stopped after {cycle_num} cycles.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Self-Evolve Loop — Autonomous Agent Improvement")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--interval", type=int, default=60, help="Minutes between cycles (default: 60)")
    parser.add_argument("--max-agents", type=int, default=3, help="Max agents to evolve per cycle (default: 3)")
    parser.add_argument("--min-score", type=float, default=50.0, help="Minimum score threshold (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    parser.add_argument("--score", type=str, help="Score a specific agent file")
    parser.add_argument("--score-all", action="store_true", help="Score and rank all agents")

    args = parser.parse_args()

    if args.daemon:
        daemon_loop(
            interval_minutes=args.interval,
            max_agents=args.max_agents,
            dry_run=args.dry_run,
        )

    elif args.score:
        path = Path(args.score)
        if path.exists():
            result = score_agent(path, datetime.now())
            print(f"\n  Agent: {result['name']}")
            print(f"  Score: {result['score']}/100")
            print(f"  Chars: {result['char_count']:,}")
            for dim, detail in result['details'].items():
                if dim != 'total':
                    print(f"    {dim}: {detail}")
        else:
            print(f"  ❌  File not found: {args.score}")
            sys.exit(1)

    elif args.score_all:
        agents = get_agent_files()
        now = datetime.now()
        scored = [score_agent(path, now) for path in agents]
        scored.sort(key=lambda s: s["score"])

        print(f"\n  Agent Score Ranking ({len(scored)} agents):")
        print(f"  {'Rank':<6} {'Score':<8} {'Name':<30} {'Chars':<8} {'Issues'}")
        print(f"  {'─'*65}")
        for i, s in enumerate(scored, 1):
            issues = []
            if s["char_count"] < 500:
                issues.append("short")
            if s["char_count"] > 10000:
                issues.append("long")
            if not s["details"].get("frontmatter", {}).get("has_frontmatter"):
                issues.append("no-frontmatter")
            if not s["details"].get("tools", {}).get("has_tools"):
                issues.append("no-tools")
            if s["details"].get("sections", {}).get("found", 0) < 2:
                issues.append("missing-sections")
            issue_str = ", ".join(issues) if issues else "OK"
            print(f"  {i:<6} {s['score']:<8.1f} {s['name']:<30} {s['char_count']:<8,} {issue_str}")

        avg = sum(s["score"] for s in scored) / len(scored)
        print(f"\n  Average score: {avg:.1f}/100")
        print(f"  Below 50:     {sum(1 for s in scored if s['score'] < 50)} agents")
        print(f"  Below 30:     {sum(1 for s in scored if s['score'] < 30)} agents")

    else:
        run_evolution_cycle(
            max_agents=args.max_agents,
            min_score=args.min_score,
            dry_run=args.dry_run,
            test_after=not args.dry_run,
        )
