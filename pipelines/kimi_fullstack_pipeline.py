#!/usr/bin/env python3
"""
kimi_fullstack_pipeline.py — Production-grade fullstack development via Kimi CLI.

Pipeline:
  1. PM → Task decomposition
  2. ArchitectUX → Technical foundation + UX architecture
  3. Frontend Dev → Implementation (with real file writes)
  4. QA Evidence → Screenshot validation
  5. Backend Dev → API + Database (with real file writes)
  6. QA Evidence → API testing
  7. Integration → Connect frontend + backend
  8. Reality Checker → Final production readiness gate

Every step generates an executable Kimi CLI run script.
The orchestrator executes them sequentially, preserving context.

Usage:
  python3 pipelines/kimi_fullstack_pipeline.py --mission "Build a task manager app"
  python3 pipelines/kimi_fullstack_pipeline.py --mission "Dubai property listing portal" --preset realestate
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

from kimi_bridge import KimiSwarm, KimiAgent, list_available_agents

# ── Presets ──────────────────────────────────────────────────────────────────
PRESETS = {
    "saas": {
        "pm": "pm",
        "architect": "architect",
        "frontend": "frontend",
        "backend": "backend",
        "qa": "evidence-qa",
        "security": "security",
        "core": "qa",
        "description": "SaaS product: PM → Architect → Frontend ↔ QA → Backend ↔ QA → Security → Core",
    },
    "realestate": {
        "pm": "pm",
        "architect": "architect",
        "frontend": "frontend",
        "backend": "backend",
        "qa": "evidence-qa",
        "security": "security",
        "core": "qa",
        "description": "Real estate portal: PM → Architect → Frontend ↔ QA → Backend ↔ QA → Core",
    },
    "mobile": {
        "pm": "pm",
        "architect": "architect",
        "frontend": "mobile",
        "backend": "backend",
        "qa": "evidence-qa",
        "security": "security",
        "core": "qa",
        "description": "Mobile app: PM → Architect → Mobile ↔ QA → Backend ↔ QA → Core",
    },
    "ai": {
        "pm": "pm",
        "architect": "architect",
        "frontend": "frontend",
        "ai": "ai-engineer",
        "backend": "backend",
        "qa": "evidence-qa",
        "core": "qa",
        "description": "AI-powered app: PM → Architect → AI → Frontend ↔ QA → Backend ↔ QA → Core",
    },
}


def print_banner():
    print("\n" + "═" * 70)
    print("  🚀  KIMI FULLSTACK PIPELINE")
    print("  🔧  Real tool execution · Dev-QA loops · Production gates")
    print("  👤  Orchestrator: AgentsOrchestrator (Kimi CLI)")
    print("  📦  Agency: sahiixx/The-Agency")
    print("═" * 70 + "\n")


def run_pipeline(mission: str, preset_name: str, working_dir: str, dry_run: bool = False):
    preset = PRESETS.get(preset_name, PRESETS["saas"])
    print_banner()
    print(f"  🎯  Mission: {mission}")
    print(f"  📋  Preset:  {preset_name} ({preset['description']})")
    print(f"  📁  Output:  {working_dir}")
    print(f"  🧪  Mode:    {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    print()

    # ── Initialize swarm ─────────────────────────────────────────────────────
    swarm = KimiSwarm(working_dir=working_dir)

    # Register all preset agents
    for role, key in preset.items():
        if role in ("description",):
            continue
        try:
            agent = KimiAgent(key, working_dir=working_dir)
            swarm.register(role, agent)
            print(f"  ✅  Registered agent: {role} → {key}")
        except KeyError as e:
            print(f"  ⚠️  Agent '{key}' not found ({e}), skipping...")

    print()
    time.sleep(0.5)

    # ── Phase 1: Project Manager ─────────────────────────────────────────────
    print("─" * 70)
    print("  📋  PHASE 1: Project Manager — Task Decomposition")
    print("─" * 70)
    pm_task = (
        f"Decompose this mission into a detailed task list. "
        f"Quote EXACT requirements from the spec. Do NOT add luxury features.\n\n"
        f"MISSION: {mission}\n\n"
        f"Save the task list to '{working_dir}/project-tasks/tasklist.md'."
    )
    pm_script = swarm.step("pm", pm_task)
    print(f"  📝  Generated run script: {pm_script}\n")

    # ── Phase 2: ArchitectUX ─────────────────────────────────────────────────
    print("─" * 70)
    print("  🏗️   PHASE 2: ArchitectUX — Technical Foundation")
    print("─" * 70)
    arch_task = (
        f"Read the task list from '{working_dir}/project-tasks/tasklist.md'. "
        f"Create technical architecture and UX foundation.\n\n"
        f"Deliverables:\n"
        f"  1. CSS design system (save to '{working_dir}/css/design-system.css')\n"
        f"  2. Component architecture doc (save to '{working_dir}/project-docs/architecture.md')\n"
        f"  3. Database schema (save to '{working_dir}/project-docs/schema.sql')\n\n"
        f"MISSION: {mission}"
    )
    arch_script = swarm.step("architect", arch_task, context_keys=["pm"])
    print(f"  📝  Generated run script: {arch_script}\n")

    # ── Phase 3: Dev-QA Loop (Frontend) ──────────────────────────────────────
    print("─" * 70)
    print("  💻  PHASE 3: Frontend Development + QA Validation")
    print("─" * 70)
    if "frontend" in swarm.agents:
        frontend_result = swarm.run_dev_qa_loop(
            dev_key="frontend",
            qa_key="qa",
            task=(
                f"Implement the frontend based on the architecture.\n"
                f"Read '{working_dir}/project-docs/architecture.md' and '{working_dir}/css/design-system.css'.\n"
                f"Write actual files to '{working_dir}/src/'.\n\n"
                f"MISSION: {mission}"
            ),
            max_retries=3,
            context_keys=["pm", "architect"],
        )
        print(f"  📊  Frontend loop complete: {frontend_result['status']} ({frontend_result['attempts']} attempts)\n")
    else:
        print("  ⚠️  Frontend agent not registered, skipping.\n")

    # ── Phase 4: Dev-QA Loop (Backend) ───────────────────────────────────────
    print("─" * 70)
    print("  🔌  PHASE 4: Backend Development + QA Validation")
    print("─" * 70)
    if "backend" in swarm.agents:
        backend_result = swarm.run_dev_qa_loop(
            dev_key="backend",
            qa_key="qa",
            task=(
                f"Implement the backend API based on the architecture.\n"
                f"Read '{working_dir}/project-docs/architecture.md' and '{working_dir}/project-docs/schema.sql'.\n"
                f"Write actual files to '{working_dir}/api/'.\n\n"
                f"MISSION: {mission}"
            ),
            max_retries=3,
            context_keys=["pm", "architect"],
        )
        print(f"  📊  Backend loop complete: {backend_result['status']} ({backend_result['attempts']} attempts)\n")
    else:
        print("  ⚠️  Backend agent not registered, skipping.\n")

    # ── Phase 5: Security Review ─────────────────────────────────────────────
    if "security" in swarm.agents:
        print("─" * 70)
        print("  🔒  PHASE 5: Security Review")
        print("─" * 70)
        sec_task = (
            f"Review the implementation for security vulnerabilities.\n"
            f"Check '{working_dir}/src/' and '{working_dir}/api/' for OWASP risks, "
            f"injection flaws, auth issues, and secrets leakage.\n"
            f"Save audit report to '{working_dir}/project-docs/security-audit.md'."
        )
        sec_script = swarm.step("security", sec_task, context_keys=["frontend", "backend"])
        print(f"  📝  Generated run script: {sec_script}\n")

    # ── Phase 6: Integration ─────────────────────────────────────────────────
    print("─" * 70)
    print("  🔗  PHASE 6: Integration — Frontend + Backend")
    print("─" * 70)
    int_task = (
        f"Integrate frontend and backend. Ensure API contracts match.\n"
        f"Test end-to-end flows. Fix any mismatches.\n"
        f"Save integration notes to '{working_dir}/project-docs/integration.md'."
    )
    # Use senior-dev or frontend for integration
    int_agent = "senior-dev" if "senior-dev" in swarm.agents else ("frontend" if "frontend" in swarm.agents else "backend")
    int_script = swarm.step(int_agent, int_task, context_keys=["frontend", "backend"])
    print(f"  📝  Generated run script: {int_script}\n")

    # ── Phase 7: Reality Checker — Final Gate ────────────────────────────────
    print("─" * 70)
    print("  🧠  PHASE 7: Reality Checker — Production Readiness")
    print("─" * 70)
    core_task = (
        f"Perform final integration testing on the completed system.\n"
        f"Cross-validate all QA findings with comprehensive automated screenshots.\n"
        f"Default to 'NEEDS WORK' unless overwhelming evidence proves production readiness.\n\n"
        f"Review all files in '{working_dir}/src/' and '{working_dir}/api/'.\n"
        f"Check '{working_dir}/project-docs/security-audit.md'.\n"
        f"Save final verdict to '{working_dir}/project-docs/VERDICT.md'."
    )
    core_script = swarm.step("core", core_task, context_keys=["pm", "architect", "frontend", "backend", "security"])
    print(f"  📝  Generated run script: {core_script}\n")

    # ── Report ───────────────────────────────────────────────────────────────
    print("═" * 70)
    print("  ✅  PIPELINE ORCHESTRATION COMPLETE")
    print("═" * 70)
    print()
    print(swarm.report())
    print()

    # Save pipeline manifest
    manifest_path = Path(working_dir) / "project-docs" / "pipeline-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "mission": mission,
        "preset": preset_name,
        "working_dir": working_dir,
        "steps": swarm.logs,
        "generated_at": int(time.time()),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  📦  Pipeline manifest saved: {manifest_path}")

    if dry_run:
        print("\n  🧪  DRY RUN complete. No files were actually modified.")
        print("      Run again without --dry-run to execute live.")

    return swarm


def main():
    parser = argparse.ArgumentParser(description="Kimi Fullstack Pipeline — Production-grade dev with real tools")
    parser.add_argument("--mission", "-m", required=True, help="Mission description (e.g., 'Build a task manager')")
    parser.add_argument("--preset", "-p", default="saas", choices=list(PRESETS.keys()), help="Pipeline preset")
    parser.add_argument("--output", "-o", default="./output", help="Working directory for generated files")
    parser.add_argument("--dry-run", action="store_true", help="Generate scripts without executing")
    parser.add_argument("--list-agents", action="store_true", help="List all available agents and exit")
    args = parser.parse_args()

    if args.list_agents:
        print("Available agents:")
        for a in list_available_agents():
            print(f"  • {a}")
        return

    run_pipeline(
        mission=args.mission,
        preset_name=args.preset,
        working_dir=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
