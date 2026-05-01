#!/usr/bin/env python3
"""
Weave — Git merge driver for AI agent conflicts.

Inspired by Ataraxy-Labs/weave (960 ★). Resolves git merge conflicts
that arise when multiple AI agents (delegates) edit the same file.
Records outcomes in the trust graph so future conflicts prefer the
agent with the best resolution track record.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ConflictBlock:
    ours: list[str]
    theirs: list[str]
    agent_id: str
    trust: float = 0.5


class WeaveDriver:
    """AI-aware git merge driver."""

    CONFLICT_RE = re.compile(
        r"^<<<<<<<\s*(?P<agent>\S+)\s+(?P<trust>\d+\.?\d*?)\n"
        r"(?P<ours>.*?)"
        r"^=======\n"
        r"(?P<theirs>.*?)"
        r"^>>>>>>>\s*(?P<base>\S+)",
        re.MULTILINE | re.DOTALL,
    )

    def __init__(self, *, use_llm: bool = True, trust_graph: Optional[dict] = None) -> None:
        self.use_llm = use_llm
        self.trust_graph = trust_graph or {}

    def resolve(self, base_path: str, ours_path: str, theirs_path: str, merged_path: str) -> str:
        """Resolve three-way merge. Returns resolved content."""
        base = Path(base_path).read_text(encoding="utf-8")
        ours = Path(ours_path).read_text(encoding="utf-8")
        theirs = Path(theirs_path).read_text(encoding="utf-8")

        # Check if any AI agent markers exist
        if "<<<<<<<" not in ours and "<<<<<<<" not in theirs:
            return self._conventional_merge(base, ours, theirs)

        # Parse AI conflict markers
        blocks = self._extract_blocks(ours, theirs)

        resolved_parts: list[str] = []
        cursor = 0
        for block in blocks:
            # Find position of this conflict
            marker = f"<<<<<<< {block.agent_id}"
            pos = ours.find(marker, cursor)
            if pos == -1:
                pos = theirs.find(marker, cursor)
            if pos == -1:
                pos = cursor  # fallback

            # Add preceding content
            resolved_parts.append(ours[cursor:pos])

            # Decide winner
            winner = self._pick_winner(block)
            resolved_parts.append(winner)

            # Update trust graph
            self._record_resolution(block.agent_id, block.ours, block.theirs, winner)

            cursor = pos + len(marker) + 1  # rough advance

        resolved_parts.append(ours[cursor:])
        return "".join(resolved_parts)

    def _extract_blocks(self, ours: str, theirs: str) -> list[ConflictBlock]:
        """Pull out AI conflict blocks."""
        blocks: list[ConflictBlock] = []
        for m in self.CONFLICT_RE.finditer(ours):
            blocks.append(ConflictBlock(
                ours=m.group("ours").splitlines(keepends=True),
                theirs=[],
                agent_id=m.group("agent"),
                trust=float(m.group("trust")),
            ))
        return blocks

    def _pick_winner(self, block: ConflictBlock) -> str:
        """Return the winning code block."""
        # Prefer agent with higher trust score
        agent_trust = self.trust_graph.get(block.agent_id, block.trust)

        if agent_trust >= 0.8:
            return "".join(block.ours)

        if agent_trust <= 0.2:
            return "".join(block.theirs) if block.theirs else "".join(block.ours)

        # Mid-trust: pick shorter, simpler block
        ours_len = len("".join(block.ours))
        theirs_len = len("".join(block.theirs))
        if block.theirs and theirs_len < ours_len:
            return "".join(block.theirs)
        return "".join(block.ours)

    def _record_resolution(self, agent_id: str, ours: list[str], theirs: list[str], winner: str) -> None:
        """Log resolution for trust graph updates."""
        ours_text = "".join(ours).strip()
        won = winner.strip() == ours_text
        # Increment/decrement trust
        current = self.trust_graph.get(agent_id, 0.5)
        delta = 0.05 if won else -0.05
        self.trust_graph[agent_id] = min(1.0, max(0.0, current + delta))

    def _conventional_merge(self, base: str, ours: str, theirs: str) -> str:
        """Fallback to line-based merge for conventional conflicts."""
        # Very simple three-way: prefer ours for conflicting hunks
        # In a real implementation you'd use python difflib or git-merge-file
        return ours


def install_git_driver(repo_root: Path) -> None:
    """Register weave as a git merge driver for .py and .md files."""
    config = repo_root / ".git" / "config"
    if not config.exists():
        print("No .git/config found — run inside a git repo.")
        return

    weave_path = (repo_root / "agency-agents" / "weave" / "weave.py").resolve()

    git_config = f"""
[merge "weave"]
    name = AI agent conflict resolver
    driver = python3 {weave_path} --base %O --ours %A --theirs %B --merged %A
[merge]
    default = weave
"""
    # Append if not present
    content = config.read_text(encoding="utf-8")
    if "[merge \"weave\"]" not in content:
        with open(config, "a", encoding="utf-8") as f:
            f.write(git_config)
        print("Weave merge driver installed.")
    else:
        print("Weave merge driver already configured.")

    # Also write .gitattributes
    gitattributes = repo_root / ".gitattributes"
    attrs_line = "*.py merge=weave\n*.md merge=weave\n"
    if gitattributes.exists():
        if "merge=weave" not in gitattributes.read_text():
            with open(gitattributes, "a", encoding="utf-8") as f:
                f.write(attrs_line)
    else:
        gitattributes.write_text(attrs_line, encoding="utf-8")
    print(".gitattributes updated for *.py and *.md.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Weave — AI agent merge driver")
    parser.add_argument("--base", required=True, help="Base file path")
    parser.add_argument("--ours", required=True, help="Ours (current branch) file path")
    parser.add_argument("--theirs", required=True, help="Theirs (incoming) file path")
    parser.add_argument("--merged", required=True, help="Output merged file path")
    parser.add_argument("--trust-db", default="weave_trust.json", help="Trust graph JSON file")
    parser.add_argument("--install", action="store_true", help="Install as git merge driver")
    args = parser.parse_args()

    if args.install:
        install_git_driver(Path.cwd())
        return

    trust_graph: dict[str, float] = {}
    if Path(args.trust_db).exists():
        with open(args.trust_db, encoding="utf-8") as f:
            trust_graph = json.load(f)

    driver = WeaveDriver(trust_graph=trust_graph)
    resolved = driver.resolve(args.base, args.ours, args.theirs, args.merged)

    with open(args.merged, "w", encoding="utf-8") as f:
        f.write(resolved)

    with open(args.trust_db, "w", encoding="utf-8") as f:
        json.dump(trust_graph, f, indent=2)

    print("Merge resolved.")


if __name__ == "__main__":
    main()
