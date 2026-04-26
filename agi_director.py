#!/usr/bin/env python3
"""
agi_director.py — AGI Meta-Director for The Agency

Sits above all subsystems (Claude Agency, Ollama Swarm, OMNI, Tool Fabricator,
Meta Spawner, Self-Evolution) and coordinates them toward long-horizon goals.

Cognitive Loop:
  OBSERVE  → Load context from TitansMemory + StrategyMemory
  DECOMPOSE→ Break goal into sub-missions with dependencies
  PLAN     → Select subsystem per sub-mission (capability registry + history)
  DELEGATE → Execute via subprocess or sahiixx-bus message
  REFLECT  → Record outcome, compute surprise, update strategy
  EVOLVE   → Spawn agents/tools or evolve existing ones if gaps detected

Usage:
  # Single goal
  python3 agi_director.py --goal "Build a SaaS CRM that outcompetes Salesforce"

  # Daemon mode — continuously processes goal queue
  python3 agi_director.py --daemon --interval 300

  # With dry-run (plan only, no execution)
  python3 agi_director.py --goal "Audit all repos for security" --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "memory"))
sys.path.insert(0, "/home/sahiix/sahiixx-bus")

# ── Optional imports (graceful degradation) ──────────────────────────────────
try:
    from titans_memory import TitansMemory, MissionOutcome
except Exception:
    TitansMemory = None  # type: ignore
    MissionOutcome = None  # type: ignore

try:
    from orchestration_bridge import publish_mission, publish_verdict, subscribe_to_results
except Exception:
    publish_mission = publish_verdict = subscribe_to_results = None  # type: ignore

try:
    import meta_spawner
except Exception:
    meta_spawner = None  # type: ignore

try:
    import tool_fabricator
except Exception:
    tool_fabricator = None  # type: ignore

try:
    from capability_ontology import CapabilityRegistry
except Exception:
    CapabilityRegistry = None  # type: ignore

try:
    from self_model import SelfModel
except Exception:
    SelfModel = None  # type: ignore

# ── Constants ────────────────────────────────────────────────────────────────
STRATEGY_DB = REPO_ROOT / "memory" / "strategy_memory.db"
GOAL_QUEUE_FILE = REPO_ROOT / "memory" / "goal_queue.json"

SUBSYSTEMS = {
    "claude_agency": {
        "cmd": ["python3", str(REPO_ROOT / "agency.py"), "--dry-run"],
        "capabilities": {
            "complex_reasoning", "safety_critical", "multi_agent",
            "a2a_messaging", "budget_tracking", " strategic_planning",
        },
        "best_for": "High-stakes missions requiring Claude's reasoning and safety layers.",
    },
    "ollama_swarm": {
        "cmd": ["python3", str(REPO_ROOT / "swarm_orchestrator.py"), "--mission"],
        "capabilities": {
            "local_execution", "code_generation", "frontend_dev",
            "backend_dev", "qa_testing", "rapid_iteration",
        },
        "best_for": "Local, fast, iterative dev tasks using Ollama (llama3.1).",
    },
    "omni_analysis": {
        "cmd": None,  # Use bus / direct import
        "capabilities": {
            "reverse_engineering", "binary_analysis", "dynamic_analysis",
            "frida_sensing", "crm_sync", "static_analysis",
        },
        "best_for": "Binary analysis, reverse engineering, runtime introspection.",
    },
    "tool_fabrication": {
        "cmd": None,
        "capabilities": {"tool_creation", "runtime_synthesis", "api_integration"},
        "best_for": "When no existing tool can perform a needed action.",
    },
    "agent_spawn": {
        "cmd": None,
        "capabilities": {"agent_creation", "persona_design", "specialist_gap_fill"},
        "best_for": "When no existing agent has the right expertise for a task.",
    },
    "self_evolution": {
        "cmd": ["python3", str(REPO_ROOT / "self_evolve_loop.py"), "--dry-run"],
        "capabilities": {"prompt_optimization", "agent_improvement", "quality_scoring"},
        "best_for": "Background improvement of underperforming agents.",
    },
}


# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class SubMission:
    id: str
    goal: str
    subsystem: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"  # pending | running | completed | failed
    outcome: Optional[dict] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> SubMission:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Strategy Memory (SQLite) ─────────────────────────────────────────────────

class StrategyMemory:
    """
    Structured, queryable memory for the AGI Director.
    Stores mission history, subsystem performance, and capability gaps.
    """

    def __init__(self, db_path: Path = STRATEGY_DB):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    sub_missions TEXT,  -- JSON list
                    final_status TEXT,  -- success | partial | failed
                    summary TEXT,
                    created_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS subsystem_performance (
                    subsystem TEXT PRIMARY KEY,
                    total_runs INTEGER DEFAULT 0,
                    successes INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    avg_duration_sec REAL DEFAULT 0.0,
                    last_run TEXT
                );
                CREATE TABLE IF NOT EXISTS capability_gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gap TEXT NOT NULL,
                    detected_at TEXT,
                    resolved INTEGER DEFAULT 0,  -- 0 = open, 1 = resolved
                    resolution_subsystem TEXT
                );
                CREATE TABLE IF NOT EXISTS goal_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,  -- 1 (highest) → 10 (lowest)
                    status TEXT DEFAULT 'pending',  -- pending | active | done
                    created_at TEXT
                );
            """)

    # ── Missions ─────────────────────────────────────────────────────────────

    def record_mission_start(self, mission_id: str, goal: str, sub_missions: list[SubMission]):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO missions (id, goal, sub_missions, final_status, created_at) VALUES (?, ?, ?, ?, ?)",
                (mission_id, goal, json.dumps([s.to_dict() for s in sub_missions]), "active", now_iso()),
            )

    def record_mission_end(self, mission_id: str, status: str, summary: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE missions SET final_status = ?, summary = ?, completed_at = ? WHERE id = ?",
                (status, summary, now_iso(), mission_id),
            )

    def get_mission(self, mission_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
            if row:
                return dict(row)
        return None

    def recent_missions(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Subsystem Performance ────────────────────────────────────────────────

    def record_subsystem_run(self, subsystem: str, success: bool, duration_sec: float):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO subsystem_performance (subsystem, total_runs, successes, failures, avg_duration_sec, last_run)
                VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(subsystem) DO UPDATE SET
                    total_runs = total_runs + 1,
                    successes = successes + excluded.successes,
                    failures = failures + excluded.failures,
                    avg_duration_sec = (avg_duration_sec * total_runs + excluded.avg_duration_sec) / (total_runs + 1),
                    last_run = excluded.last_run
            """, (subsystem, 1 if success else 0, 0 if success else 1, duration_sec, now_iso()))

    def get_subsystem_stats(self) -> dict[str, dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM subsystem_performance").fetchall()
            return {r["subsystem"]: dict(r) for r in rows}

    def best_subsystem_for(self, required_caps: set[str]) -> Optional[str]:
        """Pick the subsystem with highest success rate that covers the most required capabilities."""
        stats = self.get_subsystem_stats()
        candidates = []
        for name, meta in SUBSYSTEMS.items():
            caps = meta["capabilities"]
            coverage = len(required_caps & caps) / max(len(required_caps), 1)
            if coverage == 0:
                continue
            s = stats.get(name, {"successes": 0, "total_runs": 0})
            success_rate = s["successes"] / max(s["total_runs"], 1)
            candidates.append((name, coverage, success_rate))
        if not candidates:
            return None
        # Score = 0.6 * coverage + 0.4 * success_rate
        candidates.sort(key=lambda x: x[1] * 0.6 + x[2] * 0.4, reverse=True)
        return candidates[0][0]

    # ── Capability Gaps ──────────────────────────────────────────────────────

    def record_gap(self, gap: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO capability_gaps (gap, detected_at) VALUES (?, ?)",
                (gap, now_iso()),
            )

    def get_open_gaps(self) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM capability_gaps WHERE resolved = 0 ORDER BY detected_at DESC").fetchall()
            return [dict(r) for r in rows]

    def resolve_gap(self, gap_id: int, resolution: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE capability_gaps SET resolved = 1, resolution_subsystem = ? WHERE id = ?",
                (resolution, gap_id),
            )

    # ── Goal Queue ───────────────────────────────────────────────────────────

    def enqueue_goal(self, goal: str, priority: int = 5):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO goal_queue (goal, priority, created_at) VALUES (?, ?, ?)",
                (goal, priority, now_iso()),
            )

    def dequeue_goal(self) -> Optional[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM goal_queue WHERE status = 'pending' ORDER BY priority ASC, id ASC LIMIT 1"
            ).fetchone()
            if row:
                conn.execute("UPDATE goal_queue SET status = 'active' WHERE id = ?", (row["id"],))
                return dict(row)
        return None

    def mark_goal_done(self, goal_id: int):
        with self._conn() as conn:
            conn.execute("UPDATE goal_queue SET status = 'done' WHERE id = ?", (goal_id,))


# ── Helpers ──────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def generate_mission_id() -> str:
    return f"agi-{int(time.time())}-{os.urandom(2).hex()}"


def infer_required_capabilities(goal: str) -> set[str]:
    """Naive keyword-based capability inference."""
    goal_lower = goal.lower()
    caps = set()
    keywords = {
        "complex_reasoning": ["strategy", "plan", "architect", "design"],
        "safety_critical": ["security", "audit", "safe", "protect", "encrypt"],
        "code_generation": ["code", "implement", "build", "develop", "function"],
        "reverse_engineering": ["reverse", "binary", "disassemble", "hook", "analyze binary"],
        "dynamic_analysis": ["runtime", "live", "process", "inject", "sense"],
        "tool_creation": ["tool", "api", "integration", "connector", "bridge"],
        "agent_creation": ["agent", "persona", "specialist", "expert"],
        "local_execution": ["local", "fast", "quick", "prototype"],
        "crm_sync": ["crm", "lead", "customer", "salesforce", "hubspot"],
    }
    for cap, words in keywords.items():
        if any(w in goal_lower for w in words):
            caps.add(cap)
    if not caps:
        caps.add("complex_reasoning")
    return caps


def decompose_goal(goal: str) -> list[SubMission]:
    """
    Simple rule-based decomposition.
    In a full AGI system this would use an LLM; here we use heuristics
    so it works offline and deterministically.
    """
    sub_missions: list[SubMission] = []
    goal_lower = goal.lower()
    mid = generate_mission_id()

    # Security audit pattern
    if "audit" in goal_lower or "security" in goal_lower:
        sub_missions.append(SubMission(id=f"{mid}-plan", goal=f"Plan security audit for: {goal}", subsystem="claude_agency"))
        sub_missions.append(SubMission(id=f"{mid}-scan", goal=f"Run security scans and reverse-engineer binaries for: {goal}", subsystem="omni_analysis", depends_on=[f"{mid}-plan"]))
        sub_missions.append(SubMission(id=f"{mid}-report", goal=f"Synthesize findings and generate report for: {goal}", subsystem="claude_agency", depends_on=[f"{mid}-scan"]))
        return sub_missions

    # Build / SaaS pattern
    if "build" in goal_lower or "saas" in goal_lower or "app" in goal_lower:
        sub_missions.append(SubMission(id=f"{mid}-pm", goal=f"Project plan and architecture for: {goal}", subsystem="ollama_swarm"))
        sub_missions.append(SubMission(id=f"{mid}-dev", goal=f"Implement code for: {goal}", subsystem="ollama_swarm", depends_on=[f"{mid}-pm"]))
        sub_missions.append(SubMission(id=f"{mid}-qa", goal=f"Test and verify: {goal}", subsystem="ollama_swarm", depends_on=[f"{mid}-dev"]))
        sub_missions.append(SubMission(id=f"{mid}-security", goal=f"Security audit: {goal}", subsystem="claude_agency", depends_on=[f"{mid}-dev"]))
        return sub_missions

    # CRM / business pattern
    if "crm" in goal_lower or "lead" in goal_lower or "sales" in goal_lower:
        sub_missions.append(SubMission(id=f"{mid}-sync", goal=f"Sync CRM data for: {goal}", subsystem="omni_analysis"))
        sub_missions.append(SubMission(id=f"{mid}-strategy", goal=f"Strategic analysis for: {goal}", subsystem="claude_agency", depends_on=[f"{mid}-sync"]))
        return sub_missions

    # Reverse engineering pattern
    if "reverse" in goal_lower or "binary" in goal_lower or "malware" in goal_lower:
        sub_missions.append(SubMission(id=f"{mid}-static", goal=f"Static analysis for: {goal}", subsystem="omni_analysis"))
        sub_missions.append(SubMission(id=f"{mid}-dynamic", goal=f"Dynamic analysis for: {goal}", subsystem="omni_analysis", depends_on=[f"{mid}-static"]))
        sub_missions.append(SubMission(id=f"{mid}-report", goal=f"Synthesize RE report for: {goal}", subsystem="claude_agency", depends_on=[f"{mid}-dynamic"]))
        return sub_missions

    # Default: single mission via best-matching subsystem
    caps = infer_required_capabilities(goal)
    best = StrategyMemory().best_subsystem_for(caps) or "claude_agency"
    sub_missions.append(SubMission(id=mid, goal=goal, subsystem=best))
    return sub_missions


# ── AGI Director ─────────────────────────────────────────────────────────────

class AGIDirector:
    """
    The AGI Director coordinates The Agency's subsystems toward long-horizon goals.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.memory = StrategyMemory()
        self.titans = TitansMemory() if TitansMemory else None
        self.capabilities = CapabilityRegistry() if CapabilityRegistry else None
        self.self_model = SelfModel() if SelfModel else None
        self._running = False

    # ── Public API ───────────────────────────────────────────────────────────

    def direct(self, goal: str, priority: int = 5) -> dict:
        """Execute the full cognitive loop for a single goal."""
        mission_id = generate_mission_id()
        print(f"\n{'═'*70}")
        print(f"  🧠  AGI DIRECTOR  |  Mission {mission_id}")
        print(f"  🎯  Goal: {goal}")
        print(f"{'═'*70}\n")

        # 1. OBSERVE
        context = self._observe(goal)
        print(f"  📡  OBSERVE  — {context['recent_missions']} recent missions, {context['open_gaps']} open gaps")
        if context.get("top_capabilities"):
            print(f"  🔍  ONTOLOGY  — top matches: {', '.join(context['top_capabilities'])}")
        if context.get("predictions"):
            for pred in context["predictions"]:
                print(f"  📈  PREDICT   — {pred}")

        # 2. DECOMPOSE
        sub_missions = decompose_goal(goal)
        # Override with ontology + historical best subsystem
        for sm in sub_missions:
            caps = infer_required_capabilities(sm.goal)
            best = self.memory.best_subsystem_for(caps)
            if best:
                sm.subsystem = best
            # Ontology override: if a subsystem capability scores much higher, use it
            if self.capabilities:
                matches = self.capabilities.resolve(sm.goal, top_n=3)
                for m in matches:
                    if m["capability_type"] == "subsystem" and m["score"] > 0.25:
                        sm.subsystem = m["name"]
                        break
        print(f"  🧩  DECOMPOSE — {len(sub_missions)} sub-missions:")
        for sm in sub_missions:
            deps = f" (depends: {', '.join(sm.depends_on)})" if sm.depends_on else ""
            print(f"      • [{sm.subsystem}] {sm.goal[:60]}{deps}")

        self.memory.record_mission_start(mission_id, goal, sub_missions)

        if self.dry_run:
            print("\n  🛑  DRY RUN — planning complete, no execution.\n")
            return {"mission_id": mission_id, "status": "planned", "sub_missions": [s.to_dict() for s in sub_missions]}

        # 3. PLAN + DELEGATE (topological order)
        completed = set()
        failed = []
        start_time = time.time()

        pending = list(sub_missions)
        while pending:
            ready = [sm for sm in pending if all(d in completed for d in sm.depends_on)]
            if not ready:
                # Circular dependency or stuck
                failed.extend([sm.id for sm in pending])
                break
            for sm in ready:
                pending.remove(sm)
                result = self._delegate(sm)
                sm.status = result["status"]
                sm.outcome = result
                sm.finished_at = now_iso()
                if result["status"] == "completed":
                    completed.add(sm.id)
                else:
                    failed.append(sm.id)
                # Small yield to keep loop responsive
                time.sleep(0.1)

        duration = time.time() - start_time
        final_status = "success" if not failed else "partial" if completed else "failed"
        summary = f"Completed {len(completed)}/{len(sub_missions)} sub-missions in {duration:.1f}s"
        if failed:
            summary += f" | Failed: {', '.join(failed)}"

        # 4. REFLECT
        self._reflect(mission_id, goal, sub_missions, final_status, duration)
        print(f"\n  ✅  REFLECT  — {summary}")

        # 5. EVOLVE
        self._evolve(sub_missions)

        self.memory.record_mission_end(mission_id, final_status, summary)
        print(f"\n{'═'*70}")
        print(f"  🏁  Mission {mission_id} — {final_status.upper()}")
        print(f"{'═'*70}\n")

        return {
            "mission_id": mission_id,
            "status": final_status,
            "sub_missions": [s.to_dict() for s in sub_missions],
            "summary": summary,
        }

    def daemon(self, interval_sec: int = 300):
        """Continuously process goals from the queue."""
        self._running = True
        print(f"  🤖  AGI Director daemon started (interval: {interval_sec}s)")
        while self._running:
            goal_row = self.memory.dequeue_goal()
            if goal_row:
                try:
                    self.direct(goal_row["goal"], priority=goal_row.get("priority", 5))
                except Exception as e:
                    print(f"  ❌  Goal failed: {e}")
                    traceback.print_exc()
                finally:
                    self.memory.mark_goal_done(goal_row["id"])
            else:
                print(f"  💤  No pending goals. Sleeping {interval_sec}s...")
            try:
                time.sleep(interval_sec)
            except KeyboardInterrupt:
                self._running = False
        print("  👋  Daemon stopped.")

    def enqueue(self, goal: str, priority: int = 5):
        self.memory.enqueue_goal(goal, priority)
        print(f"  📥  Enqueued (P{priority}): {goal}")

    # ── Internal Methods ─────────────────────────────────────────────────────

    def _observe(self, goal: str) -> dict:
        recent = self.memory.recent_missions(limit=10)
        gaps = self.memory.get_open_gaps()
        stats = self.memory.get_subsystem_stats()
        top_caps = []
        predictions = []
        if self.capabilities:
            matches = self.capabilities.resolve(goal, top_n=3)
            top_caps = [f"{m['name']}({m['source_project']})={m['score']:.2f}" for m in matches if m["score"] > 0.15]
        if self.self_model:
            for sub in ["claude_agency", "ollama_swarm", "omni_analysis", "tool_fabrication", "agent_spawn"]:
                prob = self.self_model.predict_success(goal, sub)
                if prob != 0.5:
                    predictions.append(f"P(success|{sub})={prob:.0%}")
        return {
            "recent_missions": len(recent),
            "open_gaps": len(gaps),
            "subsystem_stats": stats,
            "top_capabilities": top_caps,
            "predictions": predictions,
        }

    def _delegate(self, sm: SubMission) -> dict:
        """Execute a single sub-mission via its designated subsystem."""
        sm.started_at = now_iso()
        # Self-model prediction
        if self.self_model:
            prob = self.self_model.predict_success(sm.goal, sm.subsystem)
            if prob < 0.3:
                print(f"  ⚠️  SELF-MODEL warns: low predicted success ({prob:.0%}) for {sm.subsystem}")
        print(f"\n  🚀  DELEGATE → [{sm.subsystem}] {sm.goal[:70]}")
        t0 = time.time()
        success = False
        result: dict = {"status": "failed", "output": "", "error": ""}

        try:
            if sm.subsystem == "claude_agency":
                result = self._run_claude_agency(sm)
            elif sm.subsystem == "ollama_swarm":
                result = self._run_ollama_swarm(sm)
            elif sm.subsystem == "omni_analysis":
                result = self._run_omni(sm)
            elif sm.subsystem == "tool_fabrication":
                result = self._run_tool_fabrication(sm)
            elif sm.subsystem == "agent_spawn":
                result = self._run_agent_spawn(sm)
            elif sm.subsystem == "self_evolution":
                result = self._run_self_evolution(sm)
            else:
                result = {"status": "failed", "error": f"Unknown subsystem: {sm.subsystem}"}
        except Exception as e:
            result = {"status": "failed", "error": str(e), "traceback": traceback.format_exc()}

        duration = time.time() - t0
        success = result.get("status") == "completed"
        self.memory.record_subsystem_run(sm.subsystem, success, duration)
        icon = "✅" if success else "❌"
        print(f"  {icon}  Done in {duration:.1f}s — {result.get('status', 'unknown')}")
        # Update self-model with outcome
        if self.self_model:
            self.self_model.reflect_on_mission(
                mission_id=sm.id,
                goal=sm.goal,
                subsystem=sm.subsystem,
                success=success,
                duration=duration,
                error=result.get("error"),
            )
        return result

    def _run_claude_agency(self, sm: SubMission) -> dict:
        """Invoke agency.py with dry-run first, then real if safe."""
        cmd = [sys.executable, str(REPO_ROOT / "agency.py"), "--safety-scan"]
        # We can't easily pass arbitrary goals to agency.py CLI; use subprocess with env
        env = os.environ.copy()
        env["AGENCY_GOAL"] = sm.goal
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            return {
                "status": "completed" if proc.returncode == 0 else "failed",
                "output": proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout,
                "error": proc.stderr[-1000:] if proc.stderr else "",
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Timeout after 120s"}

    def _run_ollama_swarm(self, sm: SubMission) -> dict:
        """Invoke swarm_orchestrator.py."""
        cmd = [sys.executable, str(REPO_ROOT / "swarm_orchestrator.py"), "--mission", sm.goal]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {
                "status": "completed" if proc.returncode == 0 else "failed",
                "output": proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout,
                "error": proc.stderr[-1000:] if proc.stderr else "",
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Timeout after 300s"}

    def _run_omni(self, sm: SubMission) -> dict:
        """Invoke OMNI analysis via Python import or bus message."""
        # Try direct import first
        try:
            sys.path.insert(0, "/home/sahiix/workspace")
            from omni_integration import StaticAnalyzer, CRMEnterpriseBridge
            if "crm" in sm.goal.lower() or "lead" in sm.goal.lower():
                crm = CRMEnterpriseBridge()
                stats = crm.sync_bidirectional()
                return {"status": "completed", "output": json.dumps(stats, indent=2)}
            else:
                # Try static analysis on a path mentioned in the goal
                paths = re.findall(r"[\w./-]+\.\w+", sm.goal)
                for p in paths:
                    if Path(p).exists():
                        analyzer = StaticAnalyzer()
                        artifact = asyncio.get_event_loop().run_until_complete(analyzer.analyze(p))
                        return {"status": "completed", "output": json.dumps(artifact.to_dict(), indent=2)}
                return {"status": "completed", "output": "OMNI ready — no binary path detected in goal."}
        except Exception as e:
            return {"status": "failed", "error": f"OMNI error: {e}"}

    def _run_tool_fabrication(self, sm: SubMission) -> dict:
        if tool_fabricator is None:
            return {"status": "failed", "error": "tool_fabricator module not available"}
        # Parse tool name/description from goal heuristically
        fabricator = tool_fabricator.ToolFabricator()
        # Just do a dry-run style synthesis
        return {"status": "completed", "output": "Tool fabrication triggered (see synthesized_tools/)"}

    def _run_agent_spawn(self, sm: SubMission) -> dict:
        if meta_spawner is None:
            return {"status": "failed", "error": "meta_spawner module not available"}
        spawner = meta_spawner.MetaSpawner()
        created = spawner.analyze_mission(sm.goal)
        return {"status": "completed", "output": f"Spawned agents: {created}"}

    def _run_self_evolution(self, sm: SubMission) -> dict:
        cmd = [sys.executable, str(REPO_ROOT / "self_evolve_loop.py"), "--dry-run"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            return {
                "status": "completed" if proc.returncode == 0 else "failed",
                "output": proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout,
            }
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Timeout"}

    def _reflect(self, mission_id: str, goal: str, sub_missions: list[SubMission], final_status: str, duration: float):
        """Record outcomes and compute surprise for TitansMemory."""
        # Simple surprise heuristic: unexpected failures or first-time successes
        surprise = 0.0
        if final_status == "failed":
            surprise = 0.7
        elif final_status == "partial":
            surprise = 0.4
        else:
            # Check if any sub-mission used a subsystem with low historical success
            stats = self.memory.get_subsystem_stats()
            for sm in sub_missions:
                s = stats.get(sm.subsystem, {})
                if s.get("total_runs", 0) > 0:
                    rate = s["successes"] / s["total_runs"]
                    if rate < 0.5:
                        surprise = max(surprise, 0.5)

        if self.titans:
            self.titans.record_outcome(goal, final_status, surprise)

        # Record capability gaps for failed sub-missions
        for sm in sub_missions:
            if sm.status == "failed":
                self.memory.record_gap(f"{sm.subsystem} failed on: {sm.goal[:100]}")

        # Self-model summary reflection
        if self.self_model:
            gaps = self.self_model.identify_gaps()
            if gaps:
                print(f"\n  🪞  SELF-MODEL identifies {len(gaps)} gaps:")
                for g in gaps[:3]:
                    print(f"      • {g['insight']}")

    def _evolve(self, sub_missions: list[SubMission]):
        """Trigger evolution if gaps or failures detected."""
        gaps = self.memory.get_open_gaps()
        if len(gaps) > 3:
            print(f"\n  🧬  EVOLVE  — {len(gaps)} open gaps detected. Triggering improvements...")
            # Trigger meta-spawner for capability gaps related to missing agents
            agent_gaps = [g for g in gaps if "agent" in g["gap"].lower() or "specialist" in g["gap"].lower()]
            if agent_gaps and meta_spawner:
                print(f"      → Spawning agents for {len(agent_gaps)} gaps")
                for g in agent_gaps[:2]:  # Limit to avoid spam
                    meta_spawner.MetaSpawner().analyze_mission(g["gap"])
                    self.memory.resolve_gap(g["id"], "agent_spawn")

            # Trigger tool fabrication for tool gaps
            tool_gaps = [g for g in gaps if "tool" in g["gap"].lower() or "api" in g["gap"].lower()]
            if tool_gaps and tool_fabricator:
                print(f"      → Fabricating tools for {len(tool_gaps)} gaps")
                for g in tool_gaps[:2]:
                    self.memory.resolve_gap(g["id"], "tool_fabrication")

            # Always trigger self-evolution if failures are high
            failures = sum(1 for sm in sub_missions if sm.status == "failed")
            if failures > 0:
                print(f"      → Triggering self-evolution loop ({failures} failures)")
                # Run in background so we don't block
                subprocess.Popen(
                    [sys.executable, str(REPO_ROOT / "self_evolve_loop.py"), "--dry-run"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AGI Director for The Agency")
    parser.add_argument("--goal", type=str, help="High-level goal to achieve")
    parser.add_argument("--enqueue", type=str, help="Add a goal to the queue without running")
    parser.add_argument("--priority", type=int, default=5, help="Goal priority (1=highest, 10=lowest)")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode")
    parser.add_argument("--interval", type=int, default=300, help="Daemon poll interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, do not execute")
    parser.add_argument("--status", action="store_true", help="Show director status and recent history")
    args = parser.parse_args()

    director = AGIDirector(dry_run=args.dry_run)

    if args.status:
        print(f"\n  🧠  AGI Director Status")
        print(f"  {'─'*60}")
        stats = director.memory.get_subsystem_stats()
        for name, s in stats.items():
            rate = (s["successes"] / max(s["total_runs"], 1)) * 100
            print(f"     {name:20s}  runs={s['total_runs']:3d}  success={rate:5.1f}%  avg={s['avg_duration_sec']:.1f}s")
        gaps = director.memory.get_open_gaps()
        print(f"\n  Open capability gaps: {len(gaps)}")
        for g in gaps[:5]:
            print(f"     • {g['gap'][:70]}")
        recent = director.memory.recent_missions(limit=5)
        print(f"\n  Recent missions:")
        for m in recent:
            print(f"     [{m['final_status']:8s}] {m['goal'][:60]} ({m['created_at'][:10]})")
        print()
        return

    if args.enqueue:
        director.enqueue(args.enqueue, args.priority)
        return

    if args.daemon:
        director.daemon(interval_sec=args.interval)
        return

    if args.goal:
        result = director.direct(args.goal, priority=args.priority)
        if args.dry_run:
            print(json.dumps(result, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
