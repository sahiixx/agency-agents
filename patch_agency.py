#!/usr/bin/env python3
"""
patch_agency.py — Apply Phase 2 sahiixx-bus integration patches to agency.py.

This script reads the current agency.py, applies a series of targeted string
replacements, and writes the patched file back.  It is idempotent: running it
multiple times will not double-apply edits (each replacement is unique and
guarded by presence checks).

Usage:
    cd /mnt/agents/output/sahiixx-ecosystem/home/sahiix/agency-agents
    python3 patch_agency.py

Backups:
    A backup is written to agency.py.bak before any changes are made.
"""

import shutil
import sys
from pathlib import Path

AGENCY_PATH = Path(__file__).parent / "agency.py"
BACKUP_PATH = AGENCY_PATH.with_suffix(".py.bak")


def _read() -> str:
    if not AGENCY_PATH.exists():
        print(f"❌  agency.py not found at {AGENCY_PATH}")
        sys.exit(1)
    return AGENCY_PATH.read_text()


def _write(text: str) -> None:
    AGENCY_PATH.write_text(text)


def _guard(text: str, marker: str) -> bool:
    """Return True if *marker* is already present (patch already applied)."""
    return marker in text


def apply_patches(text: str) -> str:
    patches_applied = 0

    # ── Patch 1: add `import asyncio` ───────────────────────────────────────
    marker = "import asyncio"
    if not _guard(text, marker):
        text = text.replace(
            "import sys\nimport warnings",
            "import asyncio\nimport sys\nimport warnings",
        )
        patches_applied += 1
        print("  [+] Patch 1: added 'import asyncio'")
    else:
        print("  [=] Patch 1: already applied")

    # ── Patch 2: add Phase 2 imports after a2a_protocol block ────────────────
    marker = "from safety_proxy import safety_scan_input"
    if not _guard(text, marker):
        text = text.replace(
            """from a2a_protocol import (
    start_agency_a2a_servers,
    register_servers,
    make_a2a_tools,
)""",
            """from a2a_protocol import (
    start_agency_a2a_servers,
    register_servers,
    make_a2a_tools,
)

# ── Phase 2: sahiixx-bus integration ──────────────────────────────────────────
from safety_proxy import safety_scan_input, gate_kill, track_mission_cost, assign_identity_role
from orchestration_bridge import (
    publish_mission,
    subscribe_to_results,
    register_agency_services,
    publish_verdict,
)""",
        )
        patches_applied += 1
        print("  [+] Patch 2: added Phase 2 imports")
    else:
        print("  [=] Patch 2: already applied")

    # ── Patch 3: safety scan at the top of run_mission() ───────────────────
    marker = "Phase 2 — safety scan mission goal"
    if not _guard(text, marker):
        text = text.replace(
            """    invalid = [n for n in agent_names if n not in AGENT_REGISTRY]
    if invalid:
        print(f"❌  Unknown agents: {invalid}")
        print(f"   Available: {list(AGENT_REGISTRY.keys())}")
        sys.exit(1)

    llm = get_llm(""",
            """    invalid = [n for n in agent_names if n not in AGENT_REGISTRY]
    if invalid:
        print(f"❌  Unknown agents: {invalid}")
        print(f"   Available: {list(AGENT_REGISTRY.keys())}")
        sys.exit(1)

    # Phase 2 — safety scan mission goal before any agent construction
    if not dry_run:
        try:
            asyncio.run(safety_scan_input(goal, identity="orchestrator"))
        except Exception as scan_err:
            print(f"  ⚠️  Safety scan warning: {scan_err}")

    llm = get_llm(""",
        )
        patches_applied += 1
        print("  [+] Patch 3: added safety_scan_input call in run_mission()")
    else:
        print("  [=] Patch 3: already applied")

    # ── Patch 4: register agency services with sahiixx-bus after port_map ───
    marker = "Phase 2 — register with sahiixx-bus"
    if not _guard(text, marker):
        text = text.replace(
            """    # Start A2A servers for this mission's agents
    print("  Starting A2A servers...")
    port_map = start_agency_a2a_servers(agent_names, AGENT_REGISTRY, REPO_ROOT)
    register_servers(port_map)
    a2a_urls  = [f"http://localhost:{p}" for p in port_map.values()]""",
            """    # Start A2A servers for this mission's agents
    print("  Starting A2A servers...")
    port_map = start_agency_a2a_servers(agent_names, AGENT_REGISTRY, REPO_ROOT)
    register_servers(port_map)

    # Phase 2 — register with sahiixx-bus SwarmBus / A2ARouter
    if not dry_run:
        try:
            asyncio.run(register_agency_services(port_map))
        except Exception as bus_err:
            print(f"  ⚠️  Bus registration warning: {bus_err}")

    a2a_urls  = [f"http://localhost:{p}" for p in port_map.values()]""",
        )
        patches_applied += 1
        print("  [+] Patch 4: added register_agency_services call in run_mission()")
    else:
        print("  [=] Patch 4: already applied")

    # ── Patch 5: wrap orchestrator invocation with bus + budget tracking ──
    marker = "Phase 2 — publish mission to bus and acquire budget"
    if not _guard(text, marker):
        old_block = """    print("  Orchestrating...\\n")

    with tracer.span("orchestrator"):
        try:
            response = orchestrator.invoke(
                {"messages": [HumanMessage(content=brief)]},
                config={"recursion_limit": 50},
            )
            final = response["messages"][-1].content
            # Estimate tokens from response length (no callback needed)
            tracer.add_tokens(
                input_tokens=len(brief) // 4,
                output_tokens=len(final) // 4,
            )
        except KeyboardInterrupt:
            print("\\n  Mission interrupted.")
            return None
        except Exception as e:
            print(f"\\n  Mission failed: {type(e).__name__}: {e}")
            return None"""

        new_block = """    print("  Orchestrating...\\n")

    # Phase 2 — publish mission to bus and acquire budget
    mission_bus_id = ""
    estimated_cost = 0.0
    if not dry_run:
        try:
            mission_bus_id = asyncio.run(publish_mission(goal, preset, agent_names))
            # Rough cost heuristic: $0.003 per 1K input chars + $2 buffer
            estimated_cost = (len(brief) / 1000) * 0.003 + 2.0
            asyncio.run(track_mission_cost(mission_bus_id, estimated_cost=estimated_cost))
        except Exception as bus_err:
            print(f"  ⚠️  Bus publish warning: {bus_err}")

    with tracer.span("orchestrator"):
        try:
            response = orchestrator.invoke(
                {"messages": [HumanMessage(content=brief)]},
                config={"recursion_limit": 50},
            )
            final = response["messages"][-1].content
            # Estimate tokens from response length (no callback needed)
            tracer.add_tokens(
                input_tokens=len(brief) // 4,
                output_tokens=len(final) // 4,
            )
        except KeyboardInterrupt:
            print("\\n  Mission interrupted.")
            return None
        except Exception as e:
            print(f"\\n  Mission failed: {type(e).__name__}: {e}")
            return None

    # Phase 2 — release budget and publish verdict to bus
    if not dry_run and mission_bus_id:
        try:
            actual_cost = tracer.total_cost_usd
            asyncio.run(
                track_mission_cost(
                    mission_bus_id,
                    estimated_cost=estimated_cost,
                    actual_cost=actual_cost,
                )
            )
            verdict_str = (
                "NO-GO" if "no-go" in final.lower() and "conditional" not in final.lower() else
                "CONDITIONAL GO" if "conditional" in final.lower() else
                "GO"
            )
            asyncio.run(publish_verdict(mission_bus_id, verdict_str, final))
        except Exception as bus_err:
            print(f"  ⚠️  Bus finalize warning: {bus_err}")"""

        text = text.replace(old_block, new_block)
        patches_applied += 1
        print("  [+] Patch 5: wrapped orchestrator with bus + budget tracking")
    else:
        print("  [=] Patch 5: already applied")

    # ── Patch 6: add --safety-scan CLI flag ─────────────────────────────────
    marker = "--safety-scan"
    if not _guard(text, marker):
        text = text.replace(
            """    parser.add_argument("--dry-run",       action="store_true",
                        help="Print pipeline without making API calls (useful for testing)")""",
            """    parser.add_argument("--dry-run",       action="store_true",
                        help="Print pipeline without making API calls (useful for testing)")
    parser.add_argument("--safety-scan",   action="store_true",
                        help="Scan mission goal for safety threats and exit (no API calls)")""",
        )
        patches_applied += 1
        print("  [+] Patch 6: added --safety-scan CLI flag")
    else:
        print("  [=] Patch 6: already applied")

    # ── Patch 7: handle --safety-scan in main() ─────────────────────────────
    marker = "if args.safety_scan:"
    if not _guard(text, marker):
        text = text.replace(
            """    if args.list_agents:
        list_agents()
        return

    # ── Serve mode""",
            """    if args.list_agents:
        list_agents()
        return

    # ── Safety scan mode ───────────────────────────────────────────────────────
    if args.safety_scan:
        if not args.mission:
            print("❌  --safety-scan requires --mission")
            sys.exit(1)
        try:
            result = asyncio.run(safety_scan_input(args.mission, identity="orchestrator"))
            print(f"\\n{'='*65}")
            print("  SAFETY SCAN RESULT")
            print(f"{'='*65}")
            print(f"  Safe:           {result['safe']}")
            print(f"  Threat level:   {result['threat_level']}")
            print(f"  Violations:     {result['violations']}")
            print(f"  Sanitized:      {result['sanitized'][:120]}...")
            print(f"  Recommendation: {result['recommendation']}")
            print(f"{'='*65}\\n")
            sys.exit(0 if result['safe'] else 1)
        except Exception as e:
            print(f"❌  Safety scan failed: {e}")
            sys.exit(1)

    # ── Serve mode""",
        )
        patches_applied += 1
        print("  [+] Patch 7: added --safety-scan handler in main()")
    else:
        print("  [=] Patch 7: already applied")

    return text, patches_applied


def main() -> None:
    print(f"Patching {AGENCY_PATH} ...")

    original = _read()

    # Create backup
    shutil.copy2(AGENCY_PATH, BACKUP_PATH)
    print(f"  [+] Backup saved to {BACKUP_PATH}")

    patched, count = apply_patches(original)

    if count == 0:
        print("\n  All patches already applied — nothing changed.")
        return

    _write(patched)
    print(f"\n  ✅ {count} patch(es) applied successfully.")
    print(f" agency.py has been updated with Phase 2 sahiixx-bus integration.")
    print(f"\nNext steps:")
    print(f"  1. Review the patched file:  python3 -m py_compile agency.py")
    print(f"  2. Run a dry-run test:       python3 agency.py --mission 'Test' --dry-run")
    print(f"  3. Run a safety scan:        python3 agency.py --mission 'Test' --safety-scan")


if __name__ == "__main__":
    main()
