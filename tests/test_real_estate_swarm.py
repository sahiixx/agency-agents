#!/usr/bin/env python3
"""
Test suite for real_estate_swarm.py
Runs offline structural tests — no API key needed.
"""

import os
import sys
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
    "Ollama Reasoning Core",
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
            env={**os.environ, "OLLAMA_BASE_URL": ""},
        )
        self.assertEqual(result.returncode, 0, f"Dry run failed: {result.stderr}")
        self.assertIn("DRY RUN", result.stdout)

    def test_dry_run_leads_scope(self):
        """Dry run with leads scope should succeed."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--mission", "Test leads", "--scope", "leads", "--dry-run"],
            capture_output=True, text=True,
            env={**os.environ, "OLLAMA_BASE_URL": ""},
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
        core_pos = content.index('"Ollama Reasoning Core"')
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


# ── Dubai Business Agent Tests (ported from agents-for-multi-agent-systems) ──

BUSINESS_AGENT_DIR = REPO_ROOT / "business"
BUSINESS_AGENT_FILES = [
    "business-sales-agent.md",
    "business-marketing-agent.md",
    "business-content-agent.md",
    "business-analytics-agent.md",
    "business-operations-agent.md",
]

AGENCY_SCRIPT = REPO_ROOT / "agency.py"
MCP_TOOLS_SCRIPT = REPO_ROOT / "mcp_tools.py"


class TestDubaiBusinessAgents(unittest.TestCase):
    """Structural tests for Dubai/UAE business agent suite — no API key needed."""

    def test_business_agent_dir_exists(self):
        self.assertTrue(BUSINESS_AGENT_DIR.is_dir(), "business/ directory must exist")

    def test_all_business_agent_files_exist(self):
        """All 5 Dubai business agent files must be present (biz-sales, biz-mkt, biz-content, biz-analytics, biz-ops)."""
        for fname in BUSINESS_AGENT_FILES:
            fpath = BUSINESS_AGENT_DIR / fname
            self.assertTrue(fpath.exists(), f"Business agent file missing: {fpath}")

    def test_business_agent_frontmatter(self):
        """Every business agent file must have valid YAML frontmatter."""
        for fname in BUSINESS_AGENT_FILES:
            fpath = BUSINESS_AGENT_DIR / fname
            if not fpath.exists():
                self.skipTest(f"{fname} not found")
            content = fpath.read_text()
            self.assertTrue(content.startswith("---"), f"{fname}: must start with frontmatter '---'")
            self.assertIn("name:", content, f"{fname}: frontmatter must include 'name:'")
            self.assertIn("description:", content, f"{fname}: frontmatter must include 'description:'")

    def test_business_agents_have_working_protocol(self):
        """Every business agent must include a Working Protocol section."""
        for fname in BUSINESS_AGENT_FILES:
            fpath = BUSINESS_AGENT_DIR / fname
            if not fpath.exists():
                self.skipTest(f"{fname} not found")
            content = fpath.read_text()
            self.assertIn("Working Protocol", content, f"{fname}: must have '## ⚡ Working Protocol' section")

    def test_sales_agent_aed_pricing(self):
        """Sales agent must reference AED pricing tiers (Dubai market requirement)."""
        fpath = BUSINESS_AGENT_DIR / "business-sales-agent.md"
        if not fpath.exists():
            self.skipTest("business-sales-agent.md not found")
        content = fpath.read_text()
        self.assertIn("AED", content, "Sales agent must reference AED currency")

    def test_sales_agent_lead_scoring(self):
        """Sales agent must include lead scoring tiers."""
        fpath = BUSINESS_AGENT_DIR / "business-sales-agent.md"
        if not fpath.exists():
            self.skipTest("business-sales-agent.md not found")
        content = fpath.read_text()
        for tier in ["A-tier", "B-tier", "C-tier", "D-tier"]:
            self.assertIn(tier, content, f"Sales agent must define {tier}")

    def test_marketing_agent_uae_channels(self):
        """Marketing agent must include UAE-specific channel strategy."""
        fpath = BUSINESS_AGENT_DIR / "business-marketing-agent.md"
        if not fpath.exists():
            self.skipTest("business-marketing-agent.md not found")
        content = fpath.read_text()
        for channel in ["LinkedIn", "WhatsApp", "Instagram"]:
            self.assertIn(channel, content, f"Marketing agent must reference {channel}")

    def test_marketing_agent_ramadan_awareness(self):
        """Marketing agent must include Ramadan calendar awareness."""
        fpath = BUSINESS_AGENT_DIR / "business-marketing-agent.md"
        if not fpath.exists():
            self.skipTest("business-marketing-agent.md not found")
        content = fpath.read_text()
        self.assertIn("Ramadan", content, "Marketing agent must include Ramadan strategy")

    def test_content_agent_arabic_support(self):
        """Content agent must support Arabic language."""
        fpath = BUSINESS_AGENT_DIR / "business-content-agent.md"
        if not fpath.exists():
            self.skipTest("business-content-agent.md not found")
        content = fpath.read_text()
        self.assertIn("Arabic", content, "Content agent must reference Arabic language support")

    def test_analytics_agent_uae_benchmarks(self):
        """Analytics agent must include UAE market benchmarks."""
        fpath = BUSINESS_AGENT_DIR / "business-analytics-agent.md"
        if not fpath.exists():
            self.skipTest("business-analytics-agent.md not found")
        content = fpath.read_text()
        self.assertIn("UAE", content, "Analytics agent must reference UAE market data")
        self.assertIn("AED", content, "Analytics agent must use AED currency")

    def test_operations_agent_uae_labour_law(self):
        """Operations agent must reference UAE Labour Law."""
        fpath = BUSINESS_AGENT_DIR / "business-operations-agent.md"
        if not fpath.exists():
            self.skipTest("business-operations-agent.md not found")
        content = fpath.read_text()
        self.assertIn("Labour Law", content, "Operations agent must reference UAE Labour Law")

    def test_operations_agent_vat(self):
        """Operations agent must reference UAE VAT requirements."""
        fpath = BUSINESS_AGENT_DIR / "business-operations-agent.md"
        if not fpath.exists():
            self.skipTest("business-operations-agent.md not found")
        content = fpath.read_text()
        self.assertIn("VAT", content, "Operations agent must reference UAE VAT")

    def test_dubai_preset_in_agency(self):
        """agency.py must define the 'dubai' preset."""
        content = AGENCY_SCRIPT.read_text()
        self.assertIn('"dubai"', content, "agency.py must define dubai preset")
        self.assertIn("biz-sales", content, "dubai preset must include biz-sales")
        self.assertIn("biz-mkt", content, "dubai preset must include biz-mkt")
        self.assertIn("biz-analytics", content, "dubai preset must include biz-analytics")
        self.assertIn("biz-ops", content, "dubai preset must include biz-ops")
        self.assertIn("biz-content", content, "dubai preset must include biz-content")

    def test_business_agents_in_registry(self):
        """All 5 business agents must be wired into AGENT_REGISTRY."""
        content = AGENCY_SCRIPT.read_text()
        for key in ["biz-sales", "biz-mkt", "biz-content", "biz-analytics", "biz-ops"]:
            self.assertIn(f'"{key}"', content, f"AGENT_REGISTRY missing key: {key}")

    def test_ollama_provider_in_agency(self):
        """agency.py must support the Ollama provider option."""
        content = AGENCY_SCRIPT.read_text()
        self.assertIn("ollama", content.lower(), "agency.py must support Ollama provider")
        self.assertIn("--provider", content, "agency.py must have --provider CLI argument")

    def test_scrape_ae_leads_tool_exists(self):
        """mcp_tools.py must define the scrape_ae_leads MCP tool."""
        content = MCP_TOOLS_SCRIPT.read_text()
        self.assertIn("scrape_ae_leads", content, "mcp_tools.py must define scrape_ae_leads tool")
        self.assertIn("dubizzle", content.lower(), "scrape_ae_leads must reference Dubizzle")

    def test_coral_bridge_integration_exists(self):
        """Coral Protocol bridge integration file must exist."""
        coral_path = REPO_ROOT / "integrations" / "coral-protocol-bridge.md"
        self.assertTrue(coral_path.exists(), "integrations/coral-protocol-bridge.md must exist")
        content = coral_path.read_text()
        self.assertIn("Coral", content, "Coral bridge must reference Coral Protocol")
        self.assertIn("SSE", content, "Coral bridge must reference SSE transport")

    def test_prompt_architect_agent_exists(self):
        """specialized-prompt-architect.md must exist."""
        pa_path = REPO_ROOT / "specialized" / "specialized-prompt-architect.md"
        self.assertTrue(pa_path.exists(), "specialized/specialized-prompt-architect.md must exist")
        content = pa_path.read_text()
        self.assertIn("Working Protocol", content, "Prompt Architect must include Working Protocol")
        self.assertIn("26", content, "Prompt Architect must reference the 26 universal patterns")

    def test_agency_syntax(self):
        """agency.py must compile without syntax errors after all upgrades."""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(AGENCY_SCRIPT)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error in agency.py: {result.stderr}")

    def test_mcp_tools_syntax(self):
        """mcp_tools.py must compile without syntax errors after all upgrades."""
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(MCP_TOOLS_SCRIPT)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Syntax error in mcp_tools.py: {result.stderr}")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  Real Estate Investment Swarm — Test Suite")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2)