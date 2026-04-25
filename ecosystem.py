#!/usr/bin/env python3
"""
ecosystem.py — SAHIIXX Ecosystem Orchestrator

Unified control plane for the entire sahiixx repo ecosystem.

Wires together:
  - agency-agents    → 350+ agent personas, deepagents SDK
  - sovereign-swarm  → Multi-agent control plane, HermesV2 bus
  - friday-os        → Voice-first personal AI OS
  - sahiixx-bus      → Central orchestration bus
  - Fixfizx          → Dubai real estate / NOWHERE.AI platform
  - moltworker       → Cloudflare messaging gateway
  - Trust-graph-     → Neo4j entity trust scoring

Architecture:
  ecosystem.py (this) → sahiixx-bus (SwarmBus) → sovereign-swarm (HermesV2) → agency-agents (350+ agents)
                                                  → friday-os (A2A/voice)
                                                  → Fixfizx (Dubai RE API)
                                                  → moltworker (Telegram/Discord)

Usage:
  python3 ecosystem.py --status                  # Show all ecosystem services
  python3 ecosystem.py --mission "..."            # Run a mission across all systems
  python3 ecosystem.py --bridge                   # Start ecosystem bridge daemon
  python3 ecosystem.py --discover                 # Discover all available agents/skills
  python3 ecosystem.py --sync                     # Sync and update all repos
  python3 ecosystem.py --route "Build landing page"  # Route to best agent system
"""

import json
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.resolve()
HOME = Path.home()

ECOSYSTEM = {
    "agency-agents": {
        "path": REPO_ROOT,
        "type": "agents",
        "port": 8100,
        "desc": "350+ specialized AI agent personas + AGI modules",
        "status": "active",
    },
    "sovereign-swarm-v2": {
        "path": HOME / "sovereign-swarm-v2",
        "type": "orchestrator",
        "port": 18797,
        "desc": "Multi-agent control plane with HermesV2 bus, A2A, MCP",
        "status": "active",
        "a2a_port": 18797,
        "webhook_port": 18793,
    },
    "friday-os": {
        "path": HOME / "friday-os",
        "type": "voice-os",
        "port": 8000,
        "desc": "Voice-first personal AI OS with PERCEIVE->ROUTE->PLAN->EXECUTE loop",
        "status": "active",
    },
    "sahiixx-bus": {
        "path": HOME / "sahiixx-bus",
        "type": "bus",
        "port": 8090,
        "desc": "Central orchestration bus, pub/sub, MCP gateway, A2A router",
        "status": "active",
    },
    "moltworker": {
        "path": HOME / "repos" / "moltworker",
        "type": "gateway",
        "port": 8787,
        "desc": "Cloudflare Worker messaging gateway (Telegram/Discord/Slack)",
        "status": "present",
    },
    "ae-lead-scraper": {
        "path": HOME / "repos" / "ae-lead-scraper---",
        "type": "tool",
        "port": None,
        "desc": "Dubai property lead scraper (Python, deployable)",
        "status": "present",
    },
    "Fixfizx": {
        "path": HOME / "repos" / "Fixfizx",
        "type": "platform",
        "port": 8002,
        "desc": "NOWHERE.AI Dubai platform (lead qual, campaigns, market analysis)",
        "status": "present",
    },
}

# ── Ecosystem Service Manager ─────────────────────────────────────────────────

class EcosystemService:
    """Represents one service in the ecosystem."""

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.path = config["path"]
        self.alive = False

    def check_health(self) -> bool:
        """Check if the service's directory exists and has a valid Python project."""
        path = self.path
        if not path.exists():
            self.alive = False
            return False
        # Check for common project files
        indicators = [
            path / "pyproject.toml",
            path / "setup.py",
            path / "README.md",
            path / "src",
            path / "main.py",
        ]
        self.alive = any(p.exists() for p in indicators)
        return self.alive

    def git_status(self) -> str:
        """Get git status of the repo."""
        if not (self.path / ".git").exists():
            return "not a git repo"
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                capture_output=True, text=True, timeout=10,
                cwd=self.path,
            )
            if result.returncode == 0:
                return result.stdout.strip()[:80]
            return "git error"
        except Exception:
            return "error"

    def git_pull(self) -> str:
        """Pull latest changes."""
        try:
            result = subprocess.run(
                ["git", "pull", "--ff-only"],
                capture_output=True, text=True, timeout=30,
                cwd=self.path,
            )
            return result.stdout.strip()[-200:] or result.stderr.strip()[-200:]
        except Exception as e:
            return f"error: {e}"

    def __repr__(self):
        return f"<EcosystemService {self.name}: {'UP' if self.alive else 'DOWN'}>"


class EcosystemOrchestrator:
    """
    Unified orchestrator for the entire sahiixx ecosystem.

    Routes tasks to the best system, bridges between them, and provides
    a single interface for monitoring and control.
    """

    def __init__(self):
        self.services = {
            name: EcosystemService(name, cfg)
            for name, cfg in ECOSYSTEM.items()
        }

    def discover(self) -> dict:
        """Discover all services and check their health."""
        results = {}
        for name, svc in self.services.items():
            alive = svc.check_health()
            git = svc.git_status()
            results[name] = {
                "alive": alive,
                "path": str(svc.path),
                "type": svc.config["type"],
                "port": svc.config["port"],
                "desc": svc.config["desc"],
                "git": git,
            }
        return results

    def show_status(self) -> str:
        """Display ecosystem status as formatted string."""
        info = self.discover()
        lines = []
        lines.append(f"\n{'='*70}")
        lines.append(f"  SAHIIXX ECOSYSTEM — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"{'='*70}\n")

        # Group by type
        by_type = {}
        for name, svc in info.items():
            t = svc["type"]
            if t not in by_type:
                by_type[t] = []
            by_type[t].append((name, svc))

        for t, items in sorted(by_type.items()):
            lines.append(f"  [{t.upper()}]")
            for name, svc in sorted(items):
                icon = "●" if svc["alive"] else "○"
                port_str = f":{svc['port']}" if svc["port"] else ""
                git_str = svc["git"][:50] if svc["git"] != "not a git repo" else ""
                lines.append(
                    f"    {icon} {name:<25} port{port_str:<10} "
                    f"{svc['desc'][:50]:<52}"
                )
                if svc["git"] and svc["git"] != "not a git repo":
                    lines.append(f"       last commit: {git_str}")
            lines.append("")

        lines.append(f"{'='*70}")
        lines.append(f"  Total: {len(info)} services | "
                      f"Active: {sum(1 for s in info.values() if s['alive'])} | "
                      f"Inactive: {sum(1 for s in info.values() if not s['alive'])}")
        lines.append(f"{'='*70}\n")
        return "\n".join(lines)

    def sync_all(self) -> dict:
        """Pull latest changes from all git repos."""
        results = {}
        print(f"\n  Syncing all ecosystem repos...\n")
        for name, svc in self.services.items():
            path = svc.path
            if not (path / ".git").exists():
                results[name] = "not a git repo"
                continue
            print(f"  [{name}] pulling... ", end="", flush=True)
            try:
                result = subprocess.run(
                    ["git", "pull", "--ff-only"],
                    capture_output=True, text=True, timeout=30,
                    cwd=path,
                )
                if result.returncode == 0:
                    output = result.stdout.strip()
                    if "Already up to date" in output:
                        print("already up to date")
                        results[name] = "up to date"
                    else:
                        print(f"{len(output.split(chr(10)))} lines pulled")
                        results[name] = "pulled"
                else:
                    print(f"error: {result.stderr.strip()[:60]}")
                    results[name] = f"error: {result.stderr.strip()[:60]}"
            except Exception as e:
                print(f"error: {e}")
                results[name] = f"error: {e}"
        return results

    def route_task(self, task: str) -> str:
        """
        Route a task description to the best suited ecosystem component.

        Uses keyword analysis to match the task to the right system.
        """
        task_lower = task.lower()

        # Patterns for routing
        routes = [
            # Real estate / Dubai → Fixfizx (via sahiixx-bus)
            (["dubai", "real estate", "property", "lead", "rera", "ae lead", "uae"],
             "sahiixx-bus → Fixfizx",
             "Real estate / Dubai task — route through sahiixx-bus FixfizxBridge"),

            # Voice / personal assistant → friday-os
            (["voice", "speak", "hey friday", "personal assistant", "jarvis"],
             "friday-os",
             "Voice / personal AI task — route through friday-os A2A server"),

            # Multi-agent orchestration → sovereign-swarm
            (["orchestrat", "swarm", "multi-agent", "coordinate", "scheduler",
              "delegat", "pipeline", "workflow"],
             "sovereign-swarm-v2",
             "Orchestration task — route through sovereign-swarm HermesV2 bus"),

            # Agent persona / specialized skills → agency-agents
            (["design", "frontend", "backend", "security", "qa", "marketing",
              "pm ", "project manage", "write code", "build app", "architecture",
              "research", "ai engineer", "devops", "test", "documentation"],
             "agency-agents",
             "Specialized agent task — route through agency-agents (350+ personas)"),

            # Messaging → moltworker
            (["telegram", "discord", "slack", "message", "notify", "alert",
              "send to"],
             "moltworker",
             "Messaging task — route through moltworker Cloudflare gateway"),
        ]

        for keywords, target, explanation in routes:
            if any(kw in task_lower for kw in keywords):
                return f"  → {target}\n    {explanation}"

        # Default: route through sahiixx-bus for general tasks
        return ("  → sahiixx-bus (default)\n"
                "    General task — route through central orchestration bus")

    def run_mission(self, mission: str, dry_run: bool = False) -> str:
        """
        Run a mission across the ecosystem.

        In dry_run mode, shows routing plan without executing.
        In live mode, dispatches to the appropriate system.
        """
        route = self.route_task(mission)

        output = [
            f"\n{'='*70}",
            f"  ECOSYSTEM MISSION",
            f"  Mission: {mission}",
            f"  Time:    {datetime.now().strftime('%H:%M:%S')}",
            f"{'='*70}",
            f"\n  Routing:",
            f"  {route}",
        ]

        # Determine which system to use
        if "agency-agents" in route:
            output.append(f"\n  Dispatching to agency-agents...")
            if not dry_run:
                try:
                    sys.path.insert(0, str(REPO_ROOT))
                    from agency import run_mission as agency_run
                    result = agency_run(mission, agent_names=["pm", "ai", "core"])
                    output.append(f"  Result: {str(result)[:200] if result else 'None'}")
                except Exception as e:
                    output.append(f"  Agency execution: {e}")
            else:
                output.append(f"  [DRY RUN] Would run: python3 agency.py --mission \"{mission}\" --preset full")

        elif "sovereign-swarm" in route:
            output.append(f"\n  Dispatching to sovereign-swarm...")
            if not dry_run:
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "sovereign_swarm", "--repl"],
                        capture_output=True, text=True, timeout=5,
                        cwd=HOME / "sovereign-swarm-v2",
                    )
                    output.append(f"  Result: {result.stdout[:200]}")
                except Exception as e:
                    output.append(f"  Sovereign swarm: {e}")
            else:
                output.append(f"  [DRY RUN] Would dispatch to HermesV2 bus at localhost:18797")

        elif "sahiixx-bus" in route:
            output.append(f"\n  Dispatching to sahiixx-bus...")
            if not dry_run:
                try:
                    import urllib.request, json as _json
                    payload = _json.dumps({
                        "task_id": f"eco-{int(time.time())}",
                        "sender": "ecosystem-orchestrator",
                        "task_type": "mission",
                        "payload": {"mission": mission},
                        "priority": 5,
                    }).encode()
                    req = urllib.request.Request(
                        "http://localhost:8080/a2a/route",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=10) as r:
                        resp = _json.loads(r.read().decode())
                    output.append(f"  Bus response: {json.dumps(resp, indent=2)[:200]}")
                except Exception as e:
                    output.append(f"  Bus unavailable: {e}")
            else:
                output.append(f"  [DRY RUN] Would route through sahiixx-bus HTTP API")

        elif "friday-os" in route:
            output.append(f"\n  Dispatching to friday-os...")
            if not dry_run:
                try:
                    import urllib.request, json as _json
                    payload = _json.dumps({
                        "skill": "general",
                        "input": mission,
                        "session_id": f"eco-{int(time.time())}",
                        "from_agent": "ecosystem-orchestrator",
                    }).encode()
                    req = urllib.request.Request(
                        "http://localhost:8000/a2a/invoke",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=15) as r:
                        resp = _json.loads(r.read().decode())
                    output.append(f"  FRIDAY response: {str(resp)[:200]}")
                except Exception as e:
                    output.append(f"  FRIDAY unavailable: {e}")
            else:
                output.append(f"  [DRY RUN] Would invoke friday-os A2A endpoint")

        else:
            output.append(f"\n  No specific handler for this task type.")

        output.append(f"\n{'='*70}\n")
        return "\n".join(output)

    def bridge_daemon(self, interval: int = 60):
        """Run ecosystem bridge in a loop, connecting services."""
        print(f"\n  Ecosystem Bridge Daemon starting (check every {interval}s)")
        print(f"  Connected services:")
        for name, svc in self.services.items():
            status = "✓" if svc.check_health() else "✗"
            print(f"    {status} {name}")
        print(f"\n  Running... (Ctrl+C to stop)\n")

        cycle = 0
        while True:
            cycle += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Bridge cycle #{cycle}")

            # Check sahiixx-bus health
            try:
                import urllib.request, json as _json
                req = urllib.request.Request(
                    "http://localhost:8080/health",
                    headers={"User-Agent": "Ecosystem/1.0"},
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = _json.loads(r.read().decode())
                print(f"  Bus: ✓ ({len(data.get('channels', []))} channels)")
            except Exception:
                print(f"  Bus: ✗ (not running)")

            # Check sovereign-swarm A2A
            try:
                req = urllib.request.Request(
                    "http://localhost:18797/agent.json",
                    headers={"User-Agent": "Ecosystem/1.0"},
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    pass
                print(f"  Swarm A2A: ✓")
            except Exception:
                print(f"  Swarm A2A: ✗")

            # Check friday-os
            try:
                req = urllib.request.Request(
                    "http://localhost:8000/health",
                    headers={"User-Agent": "Ecosystem/1.0"},
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    pass
                print(f"  FRIDAY OS: ✓")
            except Exception:
                print(f"  FRIDAY OS: ✗")

            # Check agency-agents
            if (REPO_ROOT / "agency.py").exists():
                print(f"  Agency: ✓ ({len(list((REPO_ROOT / 'specialized').glob('*.md')))} specialist agents)")
            else:
                print(f"  Agency: ✗")

            time.sleep(interval)


# ── Legacy bridge: wire agency-agents into the ecosystem ─────────────────────

def register_with_ecosystem():
    """
    Register agency-agents with the sahiixx-bus ecosystem.

    Makes agency-agents available as a skill provider via the bus.
    """
    try:
        import urllib.request, json as _json

        # Register agent cards with the bus
        payload = _json.dumps({
            "service": "agency-agents",
            "type": "agent-framework",
            "endpoint": "http://localhost:8100",
            "agents": 35,  # registry agents
            "presets": ["full", "saas", "research", "realestate", "dubai",
                        "security", "intel", "docs", "moltbot", "trust",
                        "voice", "n8n", "sovereign", "explore", "agi"],
        }).encode()

        for port in [8080, 18797]:
            try:
                req = urllib.request.Request(
                    f"http://localhost:{port}/mcp/tools",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    pass
                print(f"  Registered with ecosystem (port {port}): OK")
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"  Registration: {e}")
        return False


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="SAHIIXX Ecosystem Orchestrator — unified control plane",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
        Examples:
          python3 ecosystem.py --status           # Show all services
          python3 ecosystem.py --sync              # Pull all repos
          python3 ecosystem.py --route "..."       # Route a task
          python3 ecosystem.py --mission "..."     # Run mission across ecosystem
          python3 ecosystem.py --bridge            # Run bridge daemon
          python3 ecosystem.py --discover          # Discover all agents/skills
          python3 ecosystem.py --register          # Register with ecosystem bus
        """),
    )
    parser.add_argument("--status", action="store_true", help="Show ecosystem status")
    parser.add_argument("--discover", action="store_true", help="Discover all agents and services")
    parser.add_argument("--sync", action="store_true", help="Pull latest from all repos")
    parser.add_argument("--route", type=str, help="Route a task description to the best system")
    parser.add_argument("--mission", type=str, help="Run a mission across the ecosystem")
    parser.add_argument("--bridge", action="store_true", help="Run ecosystem bridge daemon")
    parser.add_argument("--register", action="store_true", help="Register with ecosystem bus")
    parser.add_argument("--dry-run", action="store_true", help="Show routing plan without executing")

    args = parser.parse_args()
    eco = EcosystemOrchestrator()

    if args.status:
        print(eco.show_status())

    elif args.discover:
        info = eco.discover()
        print(f"\n  Discovered {len(info)} services:")
        for name, svc in sorted(info.items()):
            icon = "●" if svc["alive"] else "○"
            print(f"    {icon} {name:<25} {svc['type']:<12} port={svc['port']}")
            print(f"       path: {svc['path']}")
            print(f"       last: {svc['git'][:70]}")

    elif args.sync:
        results = eco.sync_all()
        up = sum(1 for v in results.values() if v == "up to date")
        pulled = sum(1 for v in results.values() if v == "pulled")
        errors = sum(1 for v in results.values() if v.startswith("error"))
        print(f"\n  Sync complete: {up} up to date, {pulled} pulled, {errors} errors")

    elif args.route:
        print(f"\n  Task: {args.route}")
        print(eco.route_task(args.route))

    elif args.mission:
        print(eco.run_mission(args.mission, dry_run=args.dry_run))

    elif args.bridge:
        eco.bridge_daemon(interval=60)

    elif args.register:
        register_with_ecosystem()

    else:
        # Default: show status
        print(eco.show_status())
