#!/usr/bin/env python3
"""
Test suite for real_estate_swarm.py
Runs offline structural tests — no API key needed.
"""

import os
import sys
import json
import unittest
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "real_estate_swarm.py"
SCAFFOLD = REPO_ROOT / "scaffold" / "real-estate-ops"
AGENT_DIR = REPO_ROOT / "real-estate"

EXPECTED_AGENTS = [
    "Lead Qualification Specialist",
    "Market Intelligence Analyst",
    "Property Matching Engine",
    "Outreach Copywriter",
    "Deal Negotiation Strategist",
    "RERA Compliance Guardian",
    "CRM Pipeline Orchestrator",
    "Investor Pitch Specialist",
    "Post-Sale Referral Engine",
    "Claude Reasoning Core",
]

EXPECTED_OUTPUTS = [
    "lead-scorecard.md",
    "market-intel.md",
    "property-matches.md",
    "outreach-sequences.md",
    "deal-brief.md",
    "compliance-check.md",
    "pipeline-report.md",
    "investor-pitch.md",
    "referral-plan.md",
    "final-verdict.md",
]

EXPECTED_AGENT_FILES = [
    "real-estate-lead-qualification-specialist.md",
    "real-estate-property-matching-engine.md",
    "real-estate-outreach-copywriter.md",
    "real-estate-deal-negotiation-strategist.md",
    "real-estate-market-intelligence-analyst.md",
    "real-estate-compliance-rera-guardian.md",
    "real-estate-crm-pipeline-orchestrator.md",
    "real-estate-investor-pitch-specialist.md",
    "real-estate-post-sale-referral-engine.md",
]

EXPECTED_SCOPES = ["full", "leads", "matching", "deals", "pitch"]


class TestRealEstateSwarmStructure(unittest.TestCase):
    """Structural tests — no API key needed."""

    def test_script_exists(self):
        self.assertTrue(SCRIPT.exists(), "real_estate_swarm.py must exist")

    def test_script_is_python(self):
        content = SCRIPT.read_text()
        self.assertIn("#!/usr/bin/env python3", content)
        self.assertIn("def main()", content)

    def test_script_syntax(self):
        """Verify the script compiles without syntax errors."""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(SCRIPT)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error: {result.stderr}")

    def test_nine_agents_defined(self):
        content = SCRIPT.read_text()
        for agent in EXPECTED_AGENTS:
            self.assertIn(f'"{agent}"', content, f"Agent '{agent}' missing from pipeline")

    def test_agent_count(self):
        """Verify exactly 10 agents (9 specialists + Core) are defined."""
        content = SCRIPT.read_text()
        count = content.count('"name":')
        self.assertEqual(count, 10, f"Expected 10 agents, found {count}")

    def test_output_files_defined(self):
        content = SCRIPT.read_text()
        for fname in EXPECTED_OUTPUTS:
            self.assertIn(fname, content, f"Output file '{fname}' missing")

    def test_scopes_defined(self):
        content = SCRIPT.read_text()
        for scope in EXPECTED_SCOPES:
            self.assertIn(f'"{scope}"', content, f"Scope '{scope}' missing")

    def test_cli_args(self):
        content = SCRIPT.read_text()
        self.assertIn("--mission", content)
        self.assertIn("--scope", content)
        self.assertIn("--dry-run", content)

    def test_scaffold_dir_can_be_created(self):
        SCAFFOLD.mkdir(parents=True, exist_ok=True)
        self.assertTrue(SCAFFOLD.is_dir())

    def test_agent_files_exist(self):
        """Verify all 9 real-estate agent files exist."""
        for fname in EXPECTED_AGENT_FILES:
            fpath = AGENT_DIR / fname
            self.assertTrue(fpath.exists(), f"Agent file missing: {fpath}")

    def test_dry_run(self):
        """Dry run should succeed without API key."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--mission", "Test pipeline", "--dry-run"],
            capture_output=True, text=True,
            env={**os.environ, "ANTHROPIC_API_KEY": ""},
        )
        self.assertEqual(result.returncode, 0, f"Dry run failed: {result.stderr}")
        self.assertIn("DRY RUN", result.stdout)

    def test_dry_run_leads_scope(self):
        """Dry run with leads scope should succeed."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--mission", "Test leads", "--scope", "leads", "--dry-run"],
            capture_output=True, text=True,
            env={**os.environ, "ANTHROPIC_API_KEY": ""},
        )
        self.assertEqual(result.returncode, 0, f"Dry run (leads) failed: {result.stderr}")
        self.assertIn("DRY RUN", result.stdout)

    def test_pipeline_stage_order(self):
        """Verify agents appear in correct stage order."""
        content = SCRIPT.read_text()
        lead_pos = content.index('"Lead Qualification Specialist"')
        match_pos = content.index('"Property Matching Engine"')
        deal_pos = content.index('"Deal Negotiation Strategist"')
        crm_pos = content.index('"CRM Pipeline Orchestrator"')
        core_pos = content.index('"Claude Reasoning Core"')
        self.assertLess(lead_pos, match_pos, "Stage 1 must precede Stage 2")
        self.assertLess(match_pos, deal_pos, "Stage 2 must precede Stage 3")
        self.assertLess(deal_pos, crm_pos, "Stage 3 must precede Stage 4")
        self.assertLess(crm_pos, core_pos, "Stage 4 must precede Stage 5")

    def test_dld_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("DLD", content, "Should reference Dubai Land Department")

    def test_rera_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("RERA", content, "Should reference RERA")

    def test_aed_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("AED", content, "Should reference AED currency")

    def test_golden_visa_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("golden visa", content.lower(), "Should reference golden visa")

    def test_verdict_parsing(self):
        content = SCRIPT.read_text()
        self.assertIn("VERDICT", content)
        for v in ["GO", "CONDITIONAL GO", "NO-GO"]:
            self.assertIn(v, content, f"Verdict '{v}' missing")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  Real Estate Investment Swarm — Test Suite")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2)
