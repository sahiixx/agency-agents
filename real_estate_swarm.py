#!/usr/bin/env python3
"""
Real Estate Investment Swarm
Ollama (llama3.1) — The Agency Multi-Agent Framework

9-agent pipeline (UAE-specific, RERA-compliant):
  Stage 1: [Lead Qualification + Market Intelligence]     — parallel intake
  Stage 2: [Property Matching + Outreach Copywriter]      — parallel matching/outreach
  Stage 3: [Deal Negotiation + RERA Compliance]            — parallel deal/compliance
  Stage 4: [CRM Pipeline + Investor Pitch + Post-Sale]    — parallel CRM/pitch/referral
  Stage 5: [Ollama Reasoning Core]                         — final verdict

Produces 10 timestamped reports in scaffold/real-estate-ops/:
  1. lead-scorecard.md        (Lead Qualification Specialist)
  2. market-intel.md          (Market Intelligence Analyst)
  3. property-matches.md      (Property Matching Engine)
  4. outreach-sequences.md    (Outreach Copywriter)
  5. deal-brief.md            (Deal Negotiation Strategist)
  6. compliance-check.md      (RERA Compliance Guardian)
  7. pipeline-report.md       (CRM Pipeline Orchestrator)
  8. investor-pitch.md        (Investor Pitch Specialist)
  9. referral-plan.md         (Post-Sale Referral Engine)
 10. final-verdict.md         (Ollama Reasoning Core)

Usage:
  export OLLAMA_BASE_URL="http://localhost:11434"
  python3 real_estate_swarm.py --mission "Qualify 50 Bayut leads" --scope leads
  python3 real_estate_swarm.py --mission "Match properties for GCC investors" --scope matching
  python3 real_estate_swarm.py --mission "Full pipeline: intake to close" --scope full
  python3 real_estate_swarm.py --mission "Generate investor pitch deck data" --scope pitch
  python3 real_estate_swarm.py --dry-run  # Validate without API calls
"""

import argparse
import os
import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "deepagents/libs/deepagents"))

# ── Agent definitions ──────────────────────────────────────────────────────────

AGENTS = [
    {
        "name": "Lead Qualification Specialist",
        "role": "Lead Scoring & Pipeline Prioritization",
        "system": (
            "You are a UAE Real Estate Lead Qualification Specialist. Given a mission and scope:\n"
            "1. Score inbound leads from Bayut, Property Finder, and direct channels\n"
            "2. Classify buyer readiness: HOT / WARM / COLD with weighted criteria\n"
            "3. Assess nationality-aware buyer models (GCC, European, South Asian, CIS)\n"
            "4. Evaluate golden visa eligibility (AED 2M+ threshold)\n"
            "5. Prioritize pipeline by deal probability and AED value\n"
            "6. Flag high-value investors (AED 5M+) for white-glove treatment\n"
            "Output a structured lead scorecard in markdown with AED values."
        ),
        "output": "lead-scorecard.md",
        "stage": 1,
    },
    {
        "name": "Market Intelligence Analyst",
        "role": "DLD Data & Market Trends",
        "system": (
            "You are a UAE Real Estate Market Intelligence Analyst. Given a mission and scope:\n"
            "1. Analyze Dubai Land Department (DLD) transaction data and trends\n"
            "2. Map area-level price movements (per sqft AED) across key communities\n"
            "3. Identify supply-demand gaps by property type and location\n"
            "4. Track off-plan vs ready property ratios and ROI projections\n"
            "5. Benchmark rental yields by area (Dubai Marina, Downtown, JVC, etc.)\n"
            "6. Monitor developer launch pipelines and handover timelines\n"
            "Output a structured market intelligence report in markdown with AED figures."
        ),
        "output": "market-intel.md",
        "stage": 1,
    },
    {
        "name": "Property Matching Engine",
        "role": "Buyer-to-Listing Pairing & Market Analysis",
        "system": (
            "You are a UAE Real Estate Property Matching Engine. Given lead data and market intel:\n"
            "1. Match qualified leads to available listings using weighted criteria\n"
            "2. Apply buyer preference filters (budget AED, bedrooms, community, view)\n"
            "3. Score match quality: EXCELLENT / GOOD / PARTIAL with reasoning\n"
            "4. Cross-reference DLD data for fair market value validation\n"
            "5. Flag off-plan opportunities matching investor profiles\n"
            "6. Generate shortlists with comparable property analysis\n"
            "Output structured property matches in markdown."
        ),
        "output": "property-matches.md",
        "stage": 2,
    },
    {
        "name": "Outreach Copywriter",
        "role": "WhatsApp, Email & SMS Campaigns",
        "system": (
            "You are a UAE Real Estate Outreach Copywriter. Given matched properties and leads:\n"
            "1. Generate WhatsApp message sequences (initial, follow-up, viewing invite)\n"
            "2. Write email drip campaigns for each buyer segment\n"
            "3. Create SMS templates for time-sensitive listings and price drops\n"
            "4. Tailor messaging by nationality and cultural context\n"
            "5. Include AED pricing, payment plan highlights, and USPs\n"
            "6. A/B test variations for open rate optimization\n"
            "Output structured outreach sequences in markdown."
        ),
        "output": "outreach-sequences.md",
        "stage": 2,
    },
    {
        "name": "Deal Negotiation Strategist",
        "role": "Offer Structuring & Closing",
        "system": (
            "You are a UAE Real Estate Deal Negotiation Strategist. Given matched properties:\n"
            "1. Structure offers with DLD fee optimization (4% transfer fee planning)\n"
            "2. Develop counter-offer strategies based on market comparables\n"
            "3. Calculate total acquisition cost (price + DLD + agency + NOC + trustee)\n"
            "4. Model payment plans for off-plan (40/60, 50/50, post-handover)\n"
            "5. Negotiate developer incentives (fee waivers, upgrades, payment holidays)\n"
            "6. Prepare closing timelines with escrow and transfer milestones\n"
            "Output a structured deal brief in markdown with AED breakdowns."
        ),
        "output": "deal-brief.md",
        "stage": 3,
    },
    {
        "name": "RERA Compliance Guardian",
        "role": "Regulatory & AML Compliance",
        "system": (
            "You are a UAE Real Estate RERA Compliance Guardian. Given deal details:\n"
            "1. Validate RERA broker registration and listing compliance\n"
            "2. Check Anti-Money Laundering (AML) requirements per UAE regulations\n"
            "3. Verify DLD registration and Oqood (off-plan) requirements\n"
            "4. Assess Form A/B/F contract compliance\n"
            "5. Validate escrow account compliance for off-plan transactions\n"
            "6. Check advertising compliance (RERA permit numbers, disclaimers)\n"
            "7. Verify data protection compliance (UAE Federal Law No. 45)\n"
            "Output a compliance checklist in markdown with PASS / FAIL / WARN per item."
        ),
        "output": "compliance-check.md",
        "stage": 3,
    },
    {
        "name": "CRM Pipeline Orchestrator",
        "role": "Lead Lifecycle & Stage Management",
        "system": (
            "You are a UAE Real Estate CRM Pipeline Orchestrator. Given all pipeline data:\n"
            "1. Map lead lifecycle stages (New → Contacted → Viewing → Offer → Closed)\n"
            "2. Generate pipeline velocity metrics and conversion rates\n"
            "3. Identify bottleneck stages and recommend interventions\n"
            "4. Assign follow-up tasks and SLA timelines per stage\n"
            "5. Calculate pipeline value (AED) by stage and probability\n"
            "6. Generate agent performance scorecards\n"
            "Output a structured pipeline report in markdown."
        ),
        "output": "pipeline-report.md",
        "stage": 4,
    },
    {
        "name": "Investor Pitch Specialist",
        "role": "HNW Proposals & ROI Analysis",
        "system": (
            "You are a UAE Real Estate Investor Pitch Specialist. Given all pipeline data:\n"
            "1. Build HNW investor proposals with projected ROI (rental + capital gains)\n"
            "2. Model golden visa qualification paths (AED 2M+ property investment)\n"
            "3. Compare Dubai yields vs global markets (London, Singapore, NYC)\n"
            "4. Structure portfolio diversification across Dubai communities\n"
            "5. Include developer track record and handover reliability metrics\n"
            "6. Present tax advantage analysis (0% income tax, no capital gains tax)\n"
            "Output a structured investor pitch in markdown with AED projections."
        ),
        "output": "investor-pitch.md",
        "stage": 4,
    },
    {
        "name": "Post-Sale Referral Engine",
        "role": "Client Retention & Referral Generation",
        "system": (
            "You are a UAE Real Estate Post-Sale Referral Engine. Given all pipeline data:\n"
            "1. Design post-handover client care sequences (30/60/90/180 day)\n"
            "2. Build referral incentive programs with AED rewards structure\n"
            "3. Create repeat-buyer nurture campaigns for portfolio expansion\n"
            "4. Generate satisfaction surveys tied to Net Promoter Score (NPS)\n"
            "5. Identify cross-sell opportunities (property management, furnishing)\n"
            "6. Map referral networks by nationality clusters\n"
            "Output a structured referral plan in markdown."
        ),
        "output": "referral-plan.md",
        "stage": 4,
    },
    {
        "name": "Ollama Reasoning Core",
        "role": "Constitutional Final Verdict",
        "system": (
            "You are the Ollama Reasoning Core — the final constitutional gate.\n"
            "You receive ALL specialist outputs from the real estate investment pipeline.\n"
            "1. Verify data accuracy across all agent outputs (AED figures, DLD data, RERA rules)\n"
            "2. Check for regulatory compliance and legal correctness\n"
            "3. Resolve conflicts between specialist findings\n"
            "4. Synthesize an executive summary with top opportunities and risks\n"
            "5. Issue a final verdict. Start your response with EXACTLY one of:\n"
            "   VERDICT: GO (pipeline healthy, proceed with deals)\n"
            "   VERDICT: CONDITIONAL GO (proceed with mitigations noted)\n"
            "   VERDICT: NO-GO (critical blockers — halt pipeline)\n"
            "Then write:\n"
            "   SUMMARY: [executive paragraph]\n"
            "   BLOCKERS: [bullet list or 'None']\n"
            "   TOP RISKS: [ranked list]\n"
            "   REQUIRED ACTIONS: [prioritized next steps]\n"
            "   PIPELINE VALUE: [total AED in pipeline]\n"
            "   DELIVERABLE: [synthesized final assessment]"
        ),
        "output": "final-verdict.md",
        "stage": 5,
    },
]

SCOPES = {
    "full": "Full pipeline — all 9 agents from lead intake to post-sale referral",
    "leads": "Lead intake — Lead Qualification + Market Intelligence → Core",
    "matching": "Property matching — Property Matching + Outreach Copywriter → Core",
    "deals": "Deal execution — Deal Negotiation + RERA Compliance → Core",
    "pitch": "Investor pitch — Investor Pitch + CRM Pipeline → Core",
}

SCOPE_AGENTS = {
    "full": [a["name"] for a in AGENTS],
    "leads": ["Lead Qualification Specialist", "Market Intelligence Analyst", "Ollama Reasoning Core"],
    "matching": ["Property Matching Engine", "Outreach Copywriter", "Ollama Reasoning Core"],
    "deals": ["Deal Negotiation Strategist", "RERA Compliance Guardian", "Ollama Reasoning Core"],
    "pitch": ["Investor Pitch Specialist", "CRM Pipeline Orchestrator", "Ollama Reasoning Core"],
}

PIPELINE_STAGES = {
    1: ["Lead Qualification Specialist", "Market Intelligence Analyst"],
    2: ["Property Matching Engine", "Outreach Copywriter"],
    3: ["Deal Negotiation Strategist", "RERA Compliance Guardian"],
    4: ["CRM Pipeline Orchestrator", "Investor Pitch Specialist", "Post-Sale Referral Engine"],
    5: ["Ollama Reasoning Core"],
}


def run_agent(client, model: str, agent: dict, mission: str, scope: str, prior_outputs: dict) -> str:
    """Run a single agent in the pipeline."""
    prior_text = ""
    if prior_outputs:
        prior_text = "\n\n".join(
            f"=== {name} OUTPUT ===\n{text[:2000]}"
            for name, text in prior_outputs.items()
        )

    is_core = agent["name"] == "Ollama Reasoning Core"
    if is_core:
        user_msg = (
            f"REAL ESTATE MISSION: {mission}\n"
            f"SCOPE: {scope} — {SCOPES.get(scope, scope)}\n\n"
            f"ALL SPECIALIST OUTPUTS:\n{prior_text}\n\n"
            "Provide your constitutional review and final verdict now."
        )
    else:
        user_msg = (
            f"REAL ESTATE MISSION: {mission}\n"
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
        description="Real Estate Investment Swarm — The Agency"
    )
    parser.add_argument("--mission", required=True, help="Mission description")
    parser.add_argument(
        "--scope",
        choices=list(SCOPES.keys()),
        default="full",
        help="Pipeline scope (default: full)",
    )
    parser.add_argument("--model", default="llama3.1", help="Ollama model")
    parser.add_argument("--dry-run", action="store_true", help="Print pipeline without calling API")
    args = parser.parse_args()

    # Filter agents by scope
    active_names = SCOPE_AGENTS[args.scope]
    active_agents = [a for a in AGENTS if a["name"] in active_names]

    # Output directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_dir = REPO_ROOT / "scaffold" / "real-estate-ops" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("  \033[1;36m🏠 REAL ESTATE INVESTMENT SWARM — The Agency\033[0m")
    print(f"{'='*60}")
    print(f"  Mission : {args.mission}")
    print(f"  Scope   : {args.scope} — {SCOPES[args.scope]}")
    print(f"  Model   : {args.model}")
    print(f"  Output  : {out_dir}")
    print(f"  Agents  : {len(active_agents)}")
    print(f"  Pipeline: {' → '.join(a['name'] for a in active_agents)}")
    print(f"{'='*60}\n")

    if args.dry_run:
        print("  [DRY RUN] Pipeline validated. No API calls made.")
        for i, agent in enumerate(active_agents, 1):
            stage = agent["stage"]
            print(f"  Stage {stage}: {agent['name']} ({agent['role']}) → {agent['output']}")
        return

    # Check OLLAMA_BASE_URL
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    if not base_url:
        print("ERROR: Set OLLAMA_BASE_URL environment variable.")
        sys.exit(1)

    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        print("ERROR: pip install langchain-ollama")
        sys.exit(1)

    client = ChatOllama(model=args.model, base_url=base_url)
    outputs: dict[str, str] = {}
    total_start = datetime.now(timezone.utc)

    for i, agent in enumerate(active_agents, 1):
        name = agent["name"]
        print(f"  [{i}/{len(active_agents)}] \033[1;33m{name}\033[0m ({agent['role']})...", end=" ", flush=True)

        start = datetime.now(timezone.utc)
        text = run_agent(client, args.model, agent, args.mission, args.scope, outputs)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        outputs[name] = text

        # Write output file
        out_file = out_dir / agent["output"]
        header = (
            f"# {name} — Real Estate Report\n\n"
            f"**Mission:** {args.mission}  \n"
            f"**Scope:** {args.scope}  \n"
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}  \n"
            f"**Model:** {args.model}  \n\n---\n\n"
        )
        out_file.write_text(header + text)

        # Parse verdict if core
        verdict_str = ""
        if name == "Ollama Reasoning Core":
            match = re.search(r"VERDICT\s*:\s*(GO|CONDITIONAL GO|NO-GO)", text, re.IGNORECASE)
            if match:
                verdict_str = f" — VERDICT: {match.group(1).upper()}"

        print(f"\033[1;32m✅\033[0m ({elapsed:.1f}s){verdict_str}")

    total_elapsed = (datetime.now(timezone.utc) - total_start).total_seconds()

    # Write manifest
    manifest = {
        "mission": args.mission,
        "scope": args.scope,
        "model": args.model,
        "timestamp": ts,
        "agents": [a["name"] for a in active_agents],
        "outputs": [a["output"] for a in active_agents],
        "elapsed_seconds": round(total_elapsed, 1),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\n{'='*60}")
    print(f"  \033[1;32m✅ PIPELINE COMPLETE ({total_elapsed:.1f}s)\033[0m")
    print(f"  📁 Reports: {out_dir}/")
    for a in active_agents:
        print(f"     • {a['output']}")
    print("     • manifest.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
