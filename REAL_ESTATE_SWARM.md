# Real Estate Investment Swarm

> Claude Sonnet 4.6 · The Agency Multi-Agent Framework
> UAE-Specific · RERA-Compliant · 9-Agent Pipeline

**Build Date:** March 16, 2026
**Status:** Production Ready

---

## Overview

Multi-agent pipeline delivering comprehensive real estate investment operations through 9 specialized agents plus a Claude Reasoning Core final gate. Purpose-built for the UAE market with DLD data references, RERA compliance, AED currency, golden visa thresholds, and nationality-aware buyer models.

```
Stage 1: [Lead Qualification + Market Intelligence]    — parallel intake
Stage 2: [Property Matching + Outreach Copywriter]     — parallel matching/outreach
Stage 3: [Deal Negotiation + RERA Compliance]           — parallel deal/compliance
Stage 4: [CRM Pipeline + Investor Pitch + Post-Sale]   — parallel CRM/pitch/referral
Stage 5: [Claude Reasoning Core]                        — final verdict
```

| Capability | Details |
|---|---|
| **Lead Scoring** | Bayut, Property Finder, direct channel leads — HOT/WARM/COLD classification |
| **Market Intel** | DLD transaction data, area-level AED/sqft, yield benchmarks |
| **Property Matching** | Buyer-to-listing pairing with budget, community, and view filters |
| **Deal Structuring** | DLD fees, payment plans, developer incentives, closing timelines |
| **RERA Compliance** | Broker registration, AML, Form A/B/F, escrow, advertising rules |
| **Investor Pitch** | Golden visa paths, ROI projections, global yield comparisons |
| **Pipeline CRM** | Lead lifecycle, conversion rates, agent scorecards |
| **Post-Sale** | Referral programs, NPS tracking, repeat-buyer nurture |

---

## Quick Start

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
bash setup.sh

# Full pipeline — all 9 agents
python3 real_estate_swarm.py --mission "Full pipeline: intake to close" --scope full

# Lead intake only
python3 real_estate_swarm.py --mission "Qualify 50 Bayut leads" --scope leads

# Property matching
python3 real_estate_swarm.py --mission "Match properties for GCC investors" --scope matching

# Deal execution
python3 real_estate_swarm.py --mission "Structure 3 pending offers" --scope deals

# Investor pitch
python3 real_estate_swarm.py --mission "Generate investor pitch deck data" --scope pitch

# Dry run (no API calls)
python3 real_estate_swarm.py --mission "Test" --dry-run
```

---

## Pipeline

| Stage | Agent | Output | Focus |
|---|---|---|---|
| 1 | **Lead Qualification Specialist** | `lead-scorecard.md` | Lead scoring, buyer readiness, golden visa eligibility |
| 1 | **Market Intelligence Analyst** | `market-intel.md` | DLD data, price trends, area analysis, rental yields |
| 2 | **Property Matching Engine** | `property-matches.md` | Buyer-to-listing pairing, shortlists, comparables |
| 2 | **Outreach Copywriter** | `outreach-sequences.md` | WhatsApp, email, SMS campaigns by segment |
| 3 | **Deal Negotiation Strategist** | `deal-brief.md` | Offers, DLD fees, payment plans, closing timelines |
| 3 | **RERA Compliance Guardian** | `compliance-check.md` | RERA, AML, escrow, Form A/B/F, advertising |
| 4 | **CRM Pipeline Orchestrator** | `pipeline-report.md` | Lead lifecycle, velocity, conversion, agent scores |
| 4 | **Investor Pitch Specialist** | `investor-pitch.md` | HNW proposals, ROI, golden visa, tax advantages |
| 4 | **Post-Sale Referral Engine** | `referral-plan.md` | Client care, referral programs, repeat-buyer nurture |
| 5 | **Claude Reasoning Core** | `final-verdict.md` | GO / CONDITIONAL GO / NO-GO verdict |

Agents within the same stage run in parallel. Each stage receives outputs from all prior stages.

---

## Scopes

| Scope | Agents | Use Case |
|---|---|---|
| `full` | All 9 + Core | End-to-end pipeline from lead intake to post-sale |
| `leads` | Lead Qualification + Market Intel + Core | New lead batch processing |
| `matching` | Property Matching + Outreach + Core | Active buyer matching cycle |
| `deals` | Deal Negotiation + RERA Compliance + Core | Pending deal execution |
| `pitch` | Investor Pitch + CRM Pipeline + Core | HNW investor preparation |

---

## Output Structure

```
scaffold/real-estate-ops/
└── 20260316_1430/
    ├── lead-scorecard.md
    ├── market-intel.md
    ├── property-matches.md
    ├── outreach-sequences.md
    ├── deal-brief.md
    ├── compliance-check.md
    ├── pipeline-report.md
    ├── investor-pitch.md
    ├── referral-plan.md
    ├── final-verdict.md
    └── manifest.json
```

Each report includes mission context, scope, timestamp, and model version.

---

## UAE-Specific Features

| Feature | Details |
|---|---|
| **DLD Integration** | Dubai Land Department transaction data and fee calculations (4% transfer fee) |
| **RERA Compliance** | Real Estate Regulatory Authority broker and listing rules |
| **Golden Visa** | AED 2M+ property investment threshold qualification |
| **AML Checks** | UAE Anti-Money Laundering regulation compliance |
| **Nationality Models** | GCC, European, South Asian, CIS buyer behavior profiles |
| **Currency** | All figures in AED (United Arab Emirates Dirham) |
| **Payment Plans** | Off-plan structures: 40/60, 50/50, post-handover models |
| **Escrow** | Off-plan escrow account compliance validation |

---

## Tests

```bash
python3 tests/test_real_estate_swarm.py
```

Tests covering:
- Script existence and Python syntax
- All 9 agent definitions present
- All 10 output files defined
- All 5 scopes validated
- CLI argument parsing (--mission, --scope, --dry-run)
- Output directory creation
- Dry-run mode execution
- Pipeline stage ordering
- UAE-specific references (DLD, RERA, AED, golden visa)
- Verdict parsing (GO, CONDITIONAL GO, NO-GO)

---

## Files

| File | Type | Status |
|---|---|---|
| `real_estate_swarm.py` | Main Script | Created |
| `REAL_ESTATE_SWARM.md` | Full Docs | Created |
| `tests/test_real_estate_swarm.py` | Test Suite | Created |
| `real-estate/` | 9 Agent Files | Created |
| `scaffold/real-estate-ops/` | Output Dir | Created on run |

---

## Agent Source Files

| Agent | File |
|---|---|
| Lead Qualification Specialist | `real-estate/real-estate-lead-qualification-specialist.md` |
| Market Intelligence Analyst | `real-estate/real-estate-market-intelligence-analyst.md` |
| Property Matching Engine | `real-estate/real-estate-property-matching-engine.md` |
| Outreach Copywriter | `real-estate/real-estate-outreach-copywriter.md` |
| Deal Negotiation Strategist | `real-estate/real-estate-deal-negotiation-strategist.md` |
| RERA Compliance Guardian | `real-estate/real-estate-compliance-rera-guardian.md` |
| CRM Pipeline Orchestrator | `real-estate/real-estate-crm-pipeline-orchestrator.md` |
| Investor Pitch Specialist | `real-estate/real-estate-investor-pitch-specialist.md` |
| Post-Sale Referral Engine | `real-estate/real-estate-post-sale-referral-engine.md` |

---

*Part of The Agency — Claude-Powered Multi-Agent Swarm Framework*
