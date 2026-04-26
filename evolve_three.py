#!/usr/bin/env python3
"""
Evolve the 3 lowest-scoring agents using Ollama (llama3.1) + Reasoning Core.
Uses curl subprocess to call Ollama API.
"""
import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.resolve()
OLLAMA_MODEL = "llama3.1"

def ollama_chat(messages: list[dict], temperature: float = 0.7) -> str:
    """Call Ollama API via curl subprocess."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False,
    })
    
    result = subprocess.run(
        ["curl", "-s", "--max-time", "600", 
         "-X", "POST", "http://localhost:11434/api/chat",
         "-d", payload],
        capture_output=True, text=True, timeout=620,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"curl failed (exit {result.returncode}): {result.stderr[:500]}")

    data = json.loads(result.stdout)
    return data["message"]["content"]


def evolve_agent(agent_path: Path, agent_name: str) -> str | None:
    """Use Reasoning Core to critique and rewrite an agent's personality."""
    core_prompt = (REPO_ROOT / "specialized/specialized-claude-reasoning-core.md").read_text()
    original = agent_path.read_text()

    messages = [
        {"role": "system", "content": core_prompt},
        {"role": "user", "content": f"""You are reviewing and improving an agent personality file.

ORIGINAL AGENT: {agent_name}
```markdown
{original}
```

Your task:
1. Identify weaknesses: vague instructions, missing edge cases, unclear scope,
   missing sections, poor structure, anything that would make this agent less effective
2. Rewrite the full agent file with improvements — same format (frontmatter + markdown),
   same name and description, but sharper, clearer, more capable
3. The improved file MUST have:
   - YAML frontmatter (between --- markers) with: name, description, vibe
   - A Core Mission section
   - An Identity section  
   - A Quality Standards section
   - A Collaboration section
   - A Boundaries section
4. Keep the personality and vibe — improve clarity and capability, don't change identity
5. Return ONLY the improved agent file content, starting with '---', nothing else outside
6. Do NOT wrap the output in code fences, do NOT add explanations

Be surgical. Preserve what works. Improve what doesn't."""},
    ]

    improved = ollama_chat(messages, temperature=0.7).strip()

    # Remove code fences if present
    if improved.startswith("```"):
        first_end = improved.find("```", 3)
        if first_end > 0:
            improved = improved[first_end + 3:]
        else:
            improved = improved[3:]
        improved = improved.strip()
    
    if improved.endswith("```"):
        improved = improved[:-3].strip()
    
    for prefix in ["markdown\n", "md\n"]:
        if improved.startswith(prefix):
            improved = improved[len(prefix):]
    improved = improved.strip()

    if len(improved) < 200:
        print(f"  ⚠️   Output too short ({len(improved)} chars) — skipping")
        print(f"      First 200 chars: {improved[:200]}")
        return None

    if not improved.startswith("---"):
        first_fence = improved.find("---")
        if first_fence > 0 and first_fence < 200:
            improved = improved[first_fence:]
            print(f"      ⚡  Fixed: extracted frontmatter from position {first_fence}")
        else:
            print(f"      ⚠️   Output doesn't start with frontmatter (---)")
            print(f"      First 100 chars: {improved[:100]}")

    return improved


def run_tests() -> bool:
    """Run the test suite."""
    try:
        env = os.environ.copy()
        env.pop("OLLAMA_HOST", None)
        result = subprocess.run(
            [sys.executable, "tests/agent_tests.py"],
            capture_output=True, text=True, timeout=120,
            cwd=REPO_ROOT, env=env,
        )
        if result.returncode != 0:
            print(f"  ❌  Tests failed:")
            lines = result.stdout.split('\n')
            for line in lines:
                if 'FAIL' in line or 'ERROR' in line or 'fail' in line.lower():
                    print(f"      {line.strip()}")
            if not any('FAIL' in l or 'ERROR' in l for l in lines):
                print(f"      Last output: {result.stdout[-300:]}")
            if result.stderr:
                print(f"      stderr: {result.stderr[-300:]}")
            return False
        print(f"  ✅  Tests passed")
        return True
    except subprocess.TimeoutExpired:
        print(f"  ⚠️   Tests timed out")
        return False
    except Exception as e:
        print(f"  ❌  Test error: {e}")
        return False


def commit_improvement(agent_path: Path, agent_name: str) -> bool:
    """Commit the improved agent to git (file already written)."""
    try:
        rel_path = agent_path.relative_to(REPO_ROOT)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        subprocess.run(["git", "add", str(rel_path)], check=True, cwd=REPO_ROOT,
                       capture_output=True, timeout=30)
        subprocess.run(["git", "commit", "-m", f"🧬 Auto-evolution: {agent_name} [{ts}]"],
                       check=True, cwd=REPO_ROOT, capture_output=True, timeout=30)

        print(f"  ✅  Committed: {agent_name}")
        return True

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else str(e)
        print(f"  ⚠️   Git error: {stderr[:300]}")
        return False
    except Exception as e:
        print(f"  ❌  Commit error: {e}")
        return False


def main():
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M")
    
    targets = [
        ("phase-4-hardening", Path(REPO_ROOT) / "strategy/playbooks/phase-4-hardening.md"),
        ("default_agent_prompt", Path(REPO_ROOT) / "deepagents_repo/libs/cli/deepagents_cli/default_agent_prompt.md"),
        ("agent-activation-prompts", Path(REPO_ROOT) / "strategy/coordination/agent-activation-prompts.md"),
    ]

    print(f"\n{'═'*65}")
    print(f"  🧬  Agency Evolution Cycle — {ts}")
    print(f"  🧠  Engine: Ollama ({OLLAMA_MODEL})")
    print(f"  🎯  Targets: 3 lowest-scoring agents")
    print(f"{'═'*65}\n")

    results = []

    for name, path in targets:
        if not path.exists():
            print(f"  ❌  Agent file not found: {path}")
            results.append((name, "not_found"))
            continue

        original = path.read_text()
        print(f"  🔬  Evolving: {name} ({len(original):,} chars)")
        print(f"      Path: {path.relative_to(REPO_ROOT)}")

        improved = evolve_agent(path, name)
        if not improved:
            print(f"      Skipping '{name}' — no improvement generated\n")
            results.append((name, "skipped"))
            continue

        print(f"      Generated: {len(original):,} → {len(improved):,} chars ({len(improved) - len(original):+d})")
        
        backup = path.with_suffix(".md.bak")
        backup.write_text(original)
        path.write_text(improved)
        print()

        print(f"      🧪  Running tests...")
        if run_tests():
            print(f"      💾  Committing...")
            if commit_improvement(path, name):
                results.append((name, "committed"))
            else:
                path.write_text(original)
                results.append((name, "commit_failed"))
                print(f"      ⚠️   Reverted '{name}' — commit failed")
        else:
            path.write_text(original)
            results.append((name, "tests_failed"))
            print(f"      ⚠️   Reverted '{name}' — tests failed")

        backup.unlink(missing_ok=True)
        print()

    print(f"{'═'*65}")
    print(f"  🏁  Cycle Complete — {ts}")
    for name, status in results:
        emojis = {"committed": "✅", "skipped": "⏭️", "tests_failed": "❌", "commit_failed": "⚠️", "not_found": "❓"}
        print(f"      {emojis.get(status, '❓')} {name}: {status}")
    print(f"{'═'*65}")

    return results


if __name__ == "__main__":
    main()
