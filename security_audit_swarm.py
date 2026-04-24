#!/usr/bin/env python3
"""
Security & Compliance Audit Swarm
Claude Sonnet 4.6 — The Agency Multi-Agent Framework

5-agent pipeline:
  PM → Security Engineer → Compliance Auditor → QA → Claude Reasoning Core

Produces 5 timestamped reports in scaffold/security-audits/:
  1. audit_plan.md         (PM)
  2. threat_model.md       (Security Engineer)
  3. compliance_report.md  (Compliance Auditor)
  4. test_results.md       (QA)
  5. final_verdict.md      (Claude Reasoning Core)

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python3 security_audit_swarm.py --mission "Audit our REST API" --scope application
  python3 security_audit_swarm.py --mission "Full SOC 2 readiness" --scope full
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

# ── Agent definitions ──────────────────────────────────────────────────────────

AGENTS = [
    {
        "name": "PM",
        "role": "Security Audit Project Manager",
        "system": (
            "You are a Security Audit PM. Given a mission and scope:\n"
            "1. Define audit phases, timelines, and owners\n"
            "2. Identify target systems, data flows, and attack surfaces\n"
            "3. Map compliance frameworks (SOC 2, ISO 27001, GDPR, HIPAA, PCI-DSS)\n"
            "4. Output a structured audit plan with risk-ranked priorities\n"
            "Be concise. Output markdown."
        ),
        "output": "audit_plan.md",
    },
    {
        "name": "Security Engineer",
        "role": "Threat Modeling & Vulnerability Assessment",
        "system": (
            "You are a Security Engineer. Given the audit plan:\n"
            "1. Perform STRIDE threat modeling on every component\n"
            "2. Map attack surfaces and data flow vulnerabilities\n"
            "3. Classify findings as CRITICAL / HIGH / MEDIUM / LOW\n"
            "4. Provide concrete remediation steps for each finding\n"
            "5. Check OWASP Top 10 coverage\n"
            "Output a structured threat model in markdown."
        ),
        "output": "threat_model.md",
    },
    {
        "name": "Compliance Auditor",
        "role": "Regulatory & Framework Compliance",
        "system": (
            "You are a Compliance Auditor. Given the threat model:\n"
            "1. Evaluate against SOC 2 Trust Service Criteria\n"
            "2. Check ISO 27001 Annex A controls\n"
            "3. Assess GDPR Article 32 technical measures\n"
            "4. Review PCI-DSS requirements where applicable\n"
            "5. Flag gaps with severity and remediation timeline\n"
            "Output a compliance matrix in markdown."
        ),
        "output": "compliance_report.md",
    },
    {
        "name": "QA",
        "role": "Security Test Validation",
        "system": (
            "You are a Security QA Engineer. Given all prior outputs:\n"
            "1. Validate threat model completeness (STRIDE coverage per component)\n"
            "2. Verify compliance gaps have remediation paths\n"
            "3. Check for contradictions between security and compliance findings\n"
            "4. Run consistency checks on severity classifications\n"
            "5. Produce a test matrix with PASS / FAIL / WARN per control\n"
            "Output structured test results in markdown."
        ),
        "output": "test_results.md",
    },
    {
        "name": "Claude Reasoning Core",
        "role": "Constitutional Final Verdict",
        "system": (
            "You are the Claude Reasoning Core — the final constitutional gate.\n"
            "You receive ALL specialist outputs from the security audit pipeline.\n"
            "1. Verify technical accuracy across all agent outputs\n"
            "2. Check for safety, legal compliance, and completeness\n"
            "3. Resolve conflicts between specialist findings\n"
            "4. Synthesize an executive summary with top risks and actions\n"
            "5. Issue a final verdict. Start your response with EXACTLY one of:\n"
            "   VERDICT: GO (safe to deploy)\n"
            "   VERDICT: CONDITIONAL GO (deploy with mitigations)\n"
            "   VERDICT: NO-GO (critical blockers exist)\n"
            "Then write:\n"
            "   SUMMARY: [executive paragraph]\n"
            "   BLOCKERS: [bullet list or 'None']\n"
            "   TOP RISKS: [ranked list]\n"
            "   REQUIRED ACTIONS: [prioritized remediation]\n"
            "   DELIVERABLE: [synthesized final assessment]"
        ),
        "output": "final_verdict.md",
    },
]

SCOPES = {
    "application": "Application-layer security (APIs, auth, data handling, injection, XSS)",
    "infrastructure": "Infrastructure security (network, cloud config, secrets, IAM, containers)",
    "full": "Full-spectrum audit (application + infrastructure + compliance + supply chain)",
}


def run_agent(client, model: str, agent: dict, mission: str, scope: str, prior_outputs: dict) -> str:
    """Run a single agent in the pipeline."""
    prior_text = ""
    if prior_outputs:
        prior_text = "\n\n".join(
            f"=== {name} OUTPUT ===\n{text[:2000]}"
            for name, text in prior_outputs.items()
        )

    is_core = agent["name"] == "Claude Reasoning Core"
    if is_core:
        user_msg = (
            f"SECURITY AUDIT MISSION: {mission}\n"
            f"SCOPE: {scope} — {SCOPES.get(scope, scope)}\n\n"
            f"ALL SPECIALIST OUTPUTS:\n{prior_text}\n\n"
            "Provide your constitutional review and final verdict now."
        )
    else:
        user_msg = (
            f"SECURITY AUDIT MISSION: {mission}\n"
            f"SCOPE: {scope} — {SCOPES.get(scope, scope)}\n\n"
            f"Complete your specialist role."
        )
        if prior_text:
            user_msg += f"\n\nPRIOR AGENT OUTPUTS:\n{prior_text}"

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=agent["system"],
        messages=[{"role": "user", "content": user_msg}],
    )

    return response.content[0].text if response.content[0].type == "text" else ""


def main():
    parser = argparse.ArgumentParser(
        description="Security & Compliance Audit Swarm — The Agency"
    )
    parser.add_argument("--mission", required=True, help="Audit mission description")
    parser.add_argument(
        "--scope",
        choices=list(SCOPES.keys()),
        default="application",
        help="Audit scope (default: application)",
    )
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude model")
    parser.add_argument("--dry-run", action="store_true", help="Print pipeline without calling API")
    args = parser.parse_args()

    # Output directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = REPO_ROOT / "scaffold" / "security-audits" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("  🔒 SECURITY AUDIT SWARM — The Agency")
    print(f"{'='*60}")
    print(f"  Mission : {args.mission}")
    print(f"  Scope   : {args.scope} — {SCOPES[args.scope]}")
    print(f"  Model   : {args.model}")
    print(f"  Output  : {out_dir}")
    print(f"  Pipeline: {' → '.join(a['name'] for a in AGENTS)}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("  [DRY RUN] Pipeline validated. No API calls made.")
        for i, agent in enumerate(AGENTS, 1):
            print(f"  Stage {i}: {agent['name']} ({agent['role']}) → {agent['output']}")
        return

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    try:
        from anthropic import Anthropic
    except ImportError:
        print("ERROR: pip install anthropic")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    outputs: dict[str, str] = {}
    total_start = datetime.now(timezone.utc)

    for i, agent in enumerate(AGENTS, 1):
        name = agent["name"]
        print(f"  [{i}/{len(AGENTS)}] {name} ({agent['role']})...", end=" ", flush=True)

        start = datetime.now(timezone.utc)
        text = run_agent(client, args.model, agent, args.mission, args.scope, outputs)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        outputs[name] = text

        # Write output file
        out_file = out_dir / agent["output"]
        header = (
            f"# {name} — Security Audit Report\n\n"
            f"**Mission:** {args.mission}  \n"
            f"**Scope:** {args.scope}  \n"
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}  \n"
            f"**Model:** {args.model}  \n\n---\n\n"
        )
        out_file.write_text(header + text)

        # Parse verdict if core
        verdict_str = ""
        if name == "Claude Reasoning Core":
            match = None
            import re
            match = re.search(r"VERDICT\s*:\s*(GO|CONDITIONAL GO|NO-GO)", text, re.IGNORECASE)
            if match:
                verdict_str = f" — VERDICT: {match.group(1).upper()}"

        print(f"✅ ({elapsed:.1f}s){verdict_str}")

    total_elapsed = (datetime.now(timezone.utc) - total_start).total_seconds()

    # Write manifest
    manifest = {
        "mission": args.mission,
        "scope": args.scope,
        "model": args.model,
        "timestamp": ts,
        "agents": [a["name"] for a in AGENTS],
        "outputs": [a["output"] for a in AGENTS],
        "elapsed_seconds": round(total_elapsed, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n{'='*60}")
    print(f"  ✅ AUDIT COMPLETE ({total_elapsed:.1f}s)")
    print(f"  📁 Reports: {out_dir}/")
    for a in AGENTS:
        print(f"     • {a['output']}")
    print("     • manifest.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
