"""
titans_memory.py — Titans-inspired memory management for The Agency.

Based on: "Titans: Learning to Memorize at Test Time" (Google, NeurIPS 2025)
Paper: https://arxiv.org/abs/2501.00663

Key idea from the paper:
  - Attention = short-term memory (precise, limited to context window)
  - Neural memory = long-term memory (persistent, learned)
  - Surprise metric: memorable events = those that violate expectations
    (measured by gradient magnitude of loss w.r.t. input)
  - Forgetting: weight decay proportional to how unsurprising something is

This module applies those principles to the agency's AGENTS.md memory:
  - "Surprising" mission outcomes (unexpected verdicts, new patterns) are
    written back to memory with higher weight
  - Routine outcomes decay and eventually get pruned
  - Memory stays compact and signal-rich rather than growing unbounded

Usage:
  from memory.titans_memory import TitansMemory
  mem = TitansMemory()
  mem.record_outcome(mission, verdict, surprise_score)
  mem.save()
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MEMORY_FILE = REPO_ROOT / "memory" / "AGENTS.md"
LEDGER_FILE = REPO_ROOT / "memory" / "mission_ledger.json"

# Titans hyperparams (adapted for discrete mission outcomes)
SURPRISE_DECAY = 0.9      # η — how fast past surprise fades (Titans Eq. 3)
FORGET_THRESHOLD = 0.1    # prune entries below this weight
MAX_LEDGER_ENTRIES = 50   # keep memory compact


class MissionOutcome:
    """A single mission result with a Titans-style surprise weight."""

    def __init__(self, mission: str, verdict: str, surprise: float, ts: str = None):
        self.mission = mission
        self.verdict = verdict          # GO / NO-GO / CONDITIONAL GO
        self.surprise = surprise        # 0.0 (routine) → 1.0 (completely unexpected)
        self.weight = surprise          # decays over time like Titans' forgetting gate
        self.ts = ts or datetime.now(timezone.utc).isoformat()

    def decay(self, eta: float = SURPRISE_DECAY):
        """Apply Titans-style forgetting: weight *= decay (less surprising → forgotten faster)."""
        self.weight *= eta * (1 - self.surprise * 0.3)  # surprising things decay slower

    def to_dict(self):
        return {"mission": self.mission, "verdict": self.verdict,
                "surprise": self.surprise, "weight": self.weight, "ts": self.ts}

    @classmethod
    def from_dict(cls, d):
        o = cls(d["mission"], d["verdict"], d["surprise"], d.get("ts"))
        o.weight = d.get("weight", d["surprise"])
        return o


class TitansMemory:
    """
    Agency long-term memory with Titans-style surprise-based retention.

    Memorable missions (unexpected verdicts, new patterns) persist longer.
    Routine missions decay and are pruned, keeping AGENTS.md signal-rich.
    """

    def __init__(self):
        self.ledger: list[MissionOutcome] = []
        self._load_ledger()

    def _load_ledger(self):
        if LEDGER_FILE.exists():
            try:
                data = json.loads(LEDGER_FILE.read_text())
                self.ledger = [MissionOutcome.from_dict(d) for d in data]
            except (json.JSONDecodeError, KeyError, TypeError):
                # Corrupt ledger — start fresh, keep backup
                backup = LEDGER_FILE.with_suffix(".json.bak")
                LEDGER_FILE.rename(backup)
                self.ledger = []

    def _save_ledger(self):
        """Atomic write — write to tmp then rename to avoid corruption."""
        tmp = LEDGER_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps([o.to_dict() for o in self.ledger], indent=2))
        tmp.replace(LEDGER_FILE)

    def compute_surprise(self, verdict: str, recent_verdicts: list[str]) -> float:
        """
        Estimate surprise score for a verdict given recent history.

        Inspired by Titans' gradient-based surprise metric — we approximate
        surprise as how much this verdict deviates from recent patterns.

        Returns 0.0 (completely expected) to 1.0 (totally unexpected).
        """
        if not recent_verdicts:
            return 0.5  # no history → moderate surprise

        # Count verdict frequency in recent history
        total = len(recent_verdicts)
        same = sum(1 for v in recent_verdicts if v.lower() == verdict.lower())
        frequency = same / total

        # High frequency → low surprise (expected); low frequency → high surprise
        surprise = 1.0 - frequency

        # NO-GO verdicts are inherently more surprising (rarer) — boost their weight
        if "no-go" in verdict.lower() and "conditional" not in verdict.lower():
            surprise = min(1.0, surprise + 0.3)

        return round(surprise, 3)

    def record_outcome(self, mission: str, verdict: str, surprise_score: float = None):
        """
        Record a mission outcome with Titans-style surprise weighting.

        If surprise_score is None, it's computed from recent verdict history.
        """
        # Decay all existing entries (Titans forgetting gate)
        for entry in self.ledger:
            entry.decay()

        # Prune low-weight entries (forgotten)
        self.ledger = [e for e in self.ledger if e.weight >= FORGET_THRESHOLD]

        # Compute surprise if not provided
        if surprise_score is None:
            recent = [e.verdict for e in self.ledger[-10:]]
            surprise_score = self.compute_surprise(verdict, recent)

        # Clamp to valid range
        surprise_score = max(0.0, min(1.0, surprise_score))

        # Add new outcome
        outcome = MissionOutcome(mission, verdict, surprise_score)
        self.ledger.append(outcome)

        # Keep ledger compact (Titans: bounded memory size)
        if len(self.ledger) > MAX_LEDGER_ENTRIES:
            # Keep highest-weight entries when pruning
            self.ledger.sort(key=lambda e: e.weight, reverse=True)
            self.ledger = self.ledger[:MAX_LEDGER_ENTRIES]

        self._save_ledger()
        return outcome

    def get_memorable_outcomes(self, top_n: int = 5) -> list[MissionOutcome]:
        """Return the most memorable (highest-weight) mission outcomes."""
        return sorted(self.ledger, key=lambda e: e.weight, reverse=True)[:top_n]

    def inject_into_agents_md(self):
        """
        Append a Lessons Learned section to AGENTS.md with the most memorable outcomes.
        This is the Titans equivalent of writing to long-term memory weights.
        """
        if not self.ledger:
            return

        memorable = self.get_memorable_outcomes(top_n=5)

        lessons = "\n## Mission Memory (Titans-weighted, most memorable first)\n"
        for o in memorable:
            lessons += f"- [{o.ts[:10]}] {o.verdict.upper()} — {o.mission[:80]}"
            lessons += f" (surprise={o.surprise:.2f}, weight={o.weight:.2f})\n"

        current = MEMORY_FILE.read_text()

        # Backup before rewriting
        MEMORY_FILE.with_suffix(".md.bak").write_text(current)

        # Remove old Mission Memory section if present
        if "## Mission Memory" in current:
            current = current[:current.index("## Mission Memory")]

        # Atomic write
        tmp = MEMORY_FILE.with_suffix(".md.tmp")
        tmp.write_text(current.rstrip() + "\n" + lessons)
        tmp.replace(MEMORY_FILE)

    def summary(self) -> str:
        """Human-readable memory summary."""
        if not self.ledger:
            return "No mission history yet."

        total = len(self.ledger)
        go = sum(1 for e in self.ledger if "go" in e.verdict.lower() and "no" not in e.verdict.lower())
        no_go = sum(1 for e in self.ledger if "no-go" in e.verdict.lower() and "conditional" not in e.verdict.lower())
        conditional = total - go - no_go
        avg_surprise = sum(e.surprise for e in self.ledger) / total

        return (f"Memory: {total} missions | GO: {go} | CONDITIONAL: {conditional} | "
                f"NO-GO: {no_go} | avg surprise: {avg_surprise:.2f}")


if __name__ == "__main__":
    # Demo
    mem = TitansMemory()

    print("Titans Memory Module — Demo")
    print("─" * 50)

    test_missions = [
        ("Write a technical spec for user auth API",    "GO"),
        ("Build a SaaS landing page",                   "CONDITIONAL GO"),
        ("Design a database schema for multi-tenancy",  "GO"),
        ("Generate marketing copy",                     "GO"),
        ("Architect a real-time trading system",        "NO-GO"),  # surprising!
    ]

    for mission, verdict in test_missions:
        outcome = mem.record_outcome(mission, verdict)
        print(f"  Recorded: {verdict:<16} surprise={outcome.surprise:.2f}  weight={outcome.weight:.2f}")
        print(f"           {mission}")

    print("\n" + mem.summary())
    print("\nMost memorable missions:")
    for o in mem.get_memorable_outcomes():
        print(f"  weight={o.weight:.2f}  {o.verdict:<16}  {o.mission[:60]}")

    mem.inject_into_agents_md()
    print("\n✅ Lessons written to memory/AGENTS.md")
