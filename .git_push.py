#!/usr/bin/env python3
"""Push agency-agents changes to GitHub with token from env file."""
import subprocess, os
from pathlib import Path

repo = Path(os.path.expanduser("~/agency-agents"))
os.chdir(repo)

# Commit all changes
subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
subprocess.run(
    ["git", "commit", "-m", "AGI upgrades + Ollama migration

- 5 new AGI modules: tool_fabricator.py, meta_spawner.py, self_evolve_loop.py, explorer_loop.py, specialized-autonomous-explorer.md
- Swapped default provider from Anthropic/Claude to Ollama (llama3.1) across all 23+ source files
- Removed all ANTHROPIC_API_KEY env variable checks
- New CLI flags: --explore, --evolve-daemon, --fabricate, --ecosystem, --score-all
- New presets: --preset explore, --preset agi
- A2A imports now lazy (no starlette dependency for non-mission ops)
- All 19 tests pass"],
    check=True, capture_output=True,
)
print("Committed.")

# Push using embedded PAT (already in remote URL)
result = subprocess.run(["git", "push"], capture_output=True, text=True)
print(result.stdout[-200:] if len(result.stdout) > 200 else result.stdout)
print(result.stderr[-200:] if len(result.stderr) > 200 else result.stderr)
if result.returncode == 0:
    print("Pushed successfully!")
else:
    print(f"Push failed (rc={result.returncode})")
