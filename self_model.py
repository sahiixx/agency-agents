#!/usr/bin/env python3
"""
self_model.py — Agent Self-Model & Reflection Engine for the AGI Director

Maintains a running model of the system's own capabilities, limitations,
and learning trajectory. Inspired by metacognition in human cognition:
the system "knows what it knows" and "knows what it doesn't know."

Key functions:
  - reflect_on_mission  → generate insight from outcome
  - predict_success     → P(success | goal, subsystem) based on history
  - identify_gaps       → surface blind spots from repeated failures
  - trend_analysis      → am I getting better or worse at X?

Storage: memory/self_model.json (human-readable, git-friendly)

Usage:
  from self_model import SelfModel
  sm = SelfModel()
  sm.reflect_on_mission(mission_id="agi-123", goal="...", subsystem="omni_analysis", success=True, duration=12.5)
  prob = sm.predict_success("reverse engineer a binary", "omni_analysis")
  print(f"Predicted success probability: {prob:.2%}")
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.resolve()
SELF_MODEL_FILE = REPO_ROOT / "memory" / "self_model.json"
STRATEGY_DB = REPO_ROOT / "memory" / "strategy_memory.db"

# Hyperparameters
CONFIDENCE_WINDOW = 10     # missions to consider for recency weighting
REFLECTION_THRESHOLD = 0.3 # min failure rate to trigger a gap reflection
TREND_WINDOW = 20          # missions for trend calculation


class SelfModel:
    """
    Persistent self-model that learns from mission outcomes.
    """

    def __init__(self):
        self.data = self._load()
        self._ensure_structure()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if SELF_MODEL_FILE.exists():
            try:
                return json.loads(SELF_MODEL_FILE.read_text())
            except (json.JSONDecodeError, Exception):
                pass
        return {}

    def _save(self):
        SELF_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SELF_MODEL_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(SELF_MODEL_FILE)

    def _ensure_structure(self):
        defaults = {
            "version": 1,
            "created_at": self._now(),
            "updated_at": self._now(),
            "subsystem_confidence": {},   # {subsystem: {score, runs, successes, failures, streak}}
            "capability_confidence": {},  # {capability_keyword: {score, runs, successes}}
            "reflections": [],            # [{ts, mission_id, insight, type}]
            "known_limitations": [],      # [{ts, limitation, evidence_count}]
            "goal_patterns": {},          # {goal_keyword: {subsystems_tried, best_subsystem, avg_success}}
            "trends": {},                 # {subsystem: {slope, recent_avg, overall_avg}}
        }
        for k, v in defaults.items():
            if k not in self.data:
                self.data[k] = v

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # ── Core API ─────────────────────────────────────────────────────────────

    def reflect_on_mission(
        self,
        mission_id: str,
        goal: str,
        subsystem: str,
        success: bool,
        duration: float,
        error: Optional[str] = None,
    ):
        """
        Update the self-model after observing a mission outcome.
        Generates reflections, updates confidence, detects trends.
        """
        self._update_subsystem_confidence(subsystem, success, duration)
        self._update_capability_confidence(goal, subsystem, success)
        self._update_goal_patterns(goal, subsystem, success, duration)
        self._maybe_generate_reflection(mission_id, goal, subsystem, success, error)
        self._compute_trends(subsystem)
        self.data["updated_at"] = self._now()
        self._save()

    def predict_success(self, goal: str, subsystem: str) -> float:
        """
        Predict probability of success for a (goal, subsystem) pair.
        Combines:
          - Base subsystem confidence (40%)
          - Goal-pattern match (30%)
          - Similar-capability history (30%)
        """
        score = 0.0
        weights = []

        # 1. Subsystem base confidence
        sub = self.data["subsystem_confidence"].get(subsystem, {})
        if sub.get("runs", 0) > 0:
            base = sub["successes"] / sub["runs"]
            # Regress toward 0.5 for small sample sizes
            n = sub["runs"]
            regressed = (base * n + 0.5 * 5) / (n + 5)
            score += regressed * 0.40
            weights.append(0.40)

        # 2. Goal pattern match
        goal_lower = goal.lower()
        best_match = None
        best_score = 0.0
        for pattern, meta in self.data["goal_patterns"].items():
            if pattern in goal_lower:
                s = meta.get("avg_success", 0.5)
                # Weight by how specific the pattern is (longer = more specific)
                specificity = len(pattern) / 50.0
                if specificity * s > best_score:
                    best_score = specificity * s
                    best_match = meta
        if best_match and best_match.get("runs", 0) > 0:
            score += best_match["avg_success"] * 0.30
            weights.append(0.30)

        # 3. Similar capability history
        cap_score = self._capability_similarity_score(goal, subsystem)
        if cap_score > 0:
            score += cap_score * 0.30
            weights.append(0.30)

        if not weights:
            return 0.5  # No data — coin flip
        # Normalize by total weight used
        return min(1.0, max(0.0, score / sum(weights)))

    def identify_gaps(self) -> list[dict]:
        """Return capabilities with consistently low success rates."""
        gaps = []
        for sub, meta in self.data["subsystem_confidence"].items():
            if meta.get("runs", 0) >= 3:
                rate = meta["successes"] / meta["runs"]
                if rate < REFLECTION_THRESHOLD:
                    gaps.append({
                        "subsystem": sub,
                        "success_rate": rate,
                        "runs": meta["runs"],
                        "insight": f"{sub} has {rate:.0%} success over {meta['runs']} runs — likely a capability gap.",
                    })
        return gaps

    def summary(self) -> dict:
        """Human-readable snapshot of current self-model."""
        subs = self.data["subsystem_confidence"]
        caps = self.data["capability_confidence"]
        reflections = self.data["reflections"][-5:]
        gaps = self.identify_gaps()
        return {
            "total_reflections": len(self.data["reflections"]),
            "subsystems_tracked": len(subs),
            "capabilities_tracked": len(caps),
            "known_gaps": len(gaps),
            "top_subsystems": sorted(
                [(s, m["successes"]/max(m["runs"],1)) for s,m in subs.items()],
                key=lambda x: x[1], reverse=True
            )[:5],
            "recent_reflections": reflections,
            "gaps": gaps,
        }

    # ── Internal Updates ─────────────────────────────────────────────────────

    def _update_subsystem_confidence(self, subsystem: str, success: bool, duration: float):
        if subsystem not in self.data["subsystem_confidence"]:
            self.data["subsystem_confidence"][subsystem] = {
                "runs": 0, "successes": 0, "failures": 0,
                "streak": 0, "avg_duration": 0.0, "last_ts": None,
            }
        s = self.data["subsystem_confidence"][subsystem]
        s["runs"] += 1
        if success:
            s["successes"] += 1
            s["streak"] = max(1, s["streak"] + 1) if s["streak"] > 0 else 1
        else:
            s["failures"] += 1
            s["streak"] = min(-1, s["streak"] - 1) if s["streak"] < 0 else -1
        # EMA for duration
        alpha = 0.3
        s["avg_duration"] = alpha * duration + (1 - alpha) * s["avg_duration"]
        s["last_ts"] = self._now()

    def _update_capability_confidence(self, goal: str, subsystem: str, success: bool):
        """Update confidence for capability keywords extracted from the goal."""
        keywords = self._extract_keywords(goal)
        for kw in keywords:
            if kw not in self.data["capability_confidence"]:
                self.data["capability_confidence"][kw] = {"runs": 0, "successes": 0, "subsystems": {}}
            c = self.data["capability_confidence"][kw]
            c["runs"] += 1
            if success:
                c["successes"] += 1
            if subsystem not in c["subsystems"]:
                c["subsystems"][subsystem] = {"runs": 0, "successes": 0}
            c["subsystems"][subsystem]["runs"] += 1
            if success:
                c["subsystems"][subsystem]["successes"] += 1

    def _update_goal_patterns(self, goal: str, subsystem: str, success: bool, duration: float):
        """Track which subsystems work best for common goal patterns."""
        patterns = self._extract_keywords(goal, min_len=4)
        for p in patterns:
            if p not in self.data["goal_patterns"]:
                self.data["goal_patterns"][p] = {
                    "runs": 0, "successes": 0, "subsystems_tried": {},
                    "best_subsystem": None, "avg_success": 0.0, "avg_duration": 0.0,
                }
            g = self.data["goal_patterns"][p]
            g["runs"] += 1
            if success:
                g["successes"] += 1
            if subsystem not in g["subsystems_tried"]:
                g["subsystems_tried"][subsystem] = {"runs": 0, "successes": 0}
            g["subsystems_tried"][subsystem]["runs"] += 1
            if success:
                g["subsystems_tried"][subsystem]["successes"] += 1
            # Update best subsystem
            best = max(g["subsystems_tried"].items(), key=lambda x: x[1]["successes"]/max(x[1]["runs"],1))
            g["best_subsystem"] = best[0]
            g["avg_success"] = g["successes"] / g["runs"]
            g["avg_duration"] = 0.3 * duration + 0.7 * g["avg_duration"]

    def _maybe_generate_reflection(self, mission_id: str, goal: str, subsystem: str, success: bool, error: Optional[str]):
        """Generate a textual reflection if the outcome was surprising or meaningful."""
        reflections = self.data["reflections"]
        sub = self.data["subsystem_confidence"].get(subsystem, {})
        runs = sub.get("runs", 0)
        base_rate = sub.get("successes", 0) / max(runs, 1)

        insight = None
        rtype = "observation"

        if not success and runs >= 3 and base_rate < 0.5:
            insight = (
                f"{subsystem} continues to underperform ({base_rate:.0%} success). "
                f"Mission '{goal[:60]}' failed. Consider evolving this subsystem or delegating to alternative."
            )
            rtype = "limitation"
            self._record_limitation(f"{subsystem} reliability", evidence=1)

        elif success and runs >= 3 and sub.get("streak", 0) >= 3:
            insight = (
                f"{subsystem} is on a {sub['streak']}-mission success streak. "
                f"Increasing confidence in this subsystem for similar goals."
            )
            rtype = "strength"

        elif not success and error and "timeout" in error.lower():
            insight = (
                f"{subsystem} timed out on '{goal[:60]}'. "
                f"Consider increasing timeout or breaking task into smaller sub-missions."
            )
            rtype = "tuning"

        if insight and not any(r.get("insight") == insight for r in reflections[-10:]):
            reflections.append({
                "ts": self._now(),
                "mission_id": mission_id,
                "insight": insight,
                "type": rtype,
                "subsystem": subsystem,
            })
            # Keep reflections bounded
            if len(reflections) > 200:
                self.data["reflections"] = reflections[-100:]

    def _record_limitation(self, limitation: str, evidence: int = 1):
        for lim in self.data["known_limitations"]:
            if lim["limitation"] == limitation:
                lim["evidence_count"] += evidence
                lim["ts"] = self._now()
                return
        self.data["known_limitations"].append({
            "ts": self._now(),
            "limitation": limitation,
            "evidence_count": evidence,
        })

    def _compute_trends(self, subsystem: str):
        """Compute success trend for a subsystem using recent vs overall average."""
        # Pull raw runs from strategy_memory.db for accuracy
        if not STRATEGY_DB.exists():
            return
        try:
            conn = sqlite3.connect(STRATEGY_DB)
            rows = conn.execute(
                "SELECT successes, total_runs FROM subsystem_performance WHERE subsystem = ?",
                (subsystem,)
            ).fetchall()
            conn.close()
            if rows:
                total_runs = rows[0][1]
                successes = rows[0][0]
                overall = successes / max(total_runs, 1)
                sub = self.data["subsystem_confidence"].get(subsystem, {})
                recent = sub.get("successes", 0) / max(sub.get("runs", 1), 1)
                self.data["trends"][subsystem] = {
                    "slope": recent - overall,
                    "recent_avg": recent,
                    "overall_avg": overall,
                    "ts": self._now(),
                }
        except Exception:
            pass

    def _capability_similarity_score(self, goal: str, subsystem: str) -> float:
        """Score based on how well subsystem has performed on similar capability keywords."""
        keywords = self._extract_keywords(goal)
        if not keywords:
            return 0.0
        scores = []
        for kw in keywords:
            cap = self.data["capability_confidence"].get(kw)
            if cap and subsystem in cap.get("subsystems", {}):
                sub = cap["subsystems"][subsystem]
                rate = sub["successes"] / max(sub["runs"], 1)
                scores.append(rate)
        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _extract_keywords(text: str, min_len: int = 3) -> list[str]:
        """Simple keyword extraction."""
        import re
        text = text.lower()
        text = re.sub(r"[^a-z0-9_\s]", " ", text)
        stop = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "under", "and", "but", "or", "yet", "so", "if",
            "because", "although", "though", "while", "where", "when", "that",
            "which", "who", "whom", "whose", "what", "this", "these", "those",
            "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
            "us", "them", "my", "your", "his", "its", "our", "their",
        }
        tokens = [t for t in text.split() if len(t) >= min_len and t not in stop]
        # Deduplicate while preserving rough frequency order
        seen = set()
        result = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Self-Model & Reflection Engine")
    parser.add_argument("--summary", action="store_true", help="Show self-model summary")
    parser.add_argument("--predict", nargs=2, metavar=("GOAL", "SUBSYSTEM"), help="Predict success probability")
    parser.add_argument("--gaps", action="store_true", help="Show identified capability gaps")
    parser.add_argument("--reflect", nargs=4, metavar=("MISSION_ID", "GOAL", "SUBSYSTEM", "SUCCESS"),
                        help="Record a reflection (SUCCESS: true/false)")
    args = parser.parse_args()

    sm = SelfModel()

    if args.summary:
        s = sm.summary()
        print(f"\n  🪞  Self-Model Summary")
        print(f"  {'─'*60}")
        print(f"  Reflections: {s['total_reflections']}  |  Subsystems: {s['subsystems_tracked']}  |  Gaps: {s['known_gaps']}")
        print(f"\n  Top Subsystems:")
        for name, rate in s["top_subsystems"]:
            print(f"     {name:25s}  {rate:.0%} success")
        if s["recent_reflections"]:
            print(f"\n  Recent Reflections:")
            for r in s["recent_reflections"]:
                print(f"     [{r['type']:12s}] {r['insight'][:80]}")
        if s["gaps"]:
            print(f"\n  ⚠️  Known Gaps:")
            for g in s["gaps"]:
                print(f"     • {g['insight']}")
        print()
        return

    if args.predict:
        goal, subsystem = args.predict
        prob = sm.predict_success(goal, subsystem)
        print(f"\n  P(success | '{goal[:50]}', {subsystem}) = {prob:.2%}\n")
        return

    if args.gaps:
        gaps = sm.identify_gaps()
        print(f"\n  {'─'*60}")
        print(f"  Identified {len(gaps)} capability gaps\n")
        for g in gaps:
            print(f"  • {g['subsystem']:20s}  {g['success_rate']:.0%} over {g['runs']} runs")
            print(f"    {g['insight']}")
        print()
        return

    if args.reflect:
        mid, goal, subsystem, success_str = args.reflect
        success = success_str.lower() in ("true", "1", "yes", "success")
        sm.reflect_on_mission(mid, goal, subsystem, success, duration=0.0)
        print(f"  ✅  Reflection recorded for {subsystem}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
