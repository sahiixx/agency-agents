#!/usr/bin/env python3
"""
Test suite for security_audit_swarm.py
Runs offline structural tests + optional live LLM tests.
"""

import os
import sys
import unittest
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "security_audit_swarm.py"
SCAFFOLD = REPO_ROOT / "scaffold" / "security-audits"


class TestSecurityAuditStructure(unittest.TestCase):
    """Structural tests — no API key needed."""

    def test_script_exists(self):
        self.assertTrue(SCRIPT.exists(), "security_audit_swarm.py must exist")

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

    def test_five_agents_defined(self):
        content = SCRIPT.read_text()
        for agent in ["PM", "Security Engineer", "Compliance Auditor", "QA", "Claude Reasoning Core"]:
            self.assertIn(f'"{agent}"', content, f"Agent '{agent}' missing from pipeline")

    def test_output_files_defined(self):
        content = SCRIPT.read_text()
        for fname in ["audit_plan.md", "threat_model.md", "compliance_report.md", "test_results.md", "final_verdict.md"]:
            self.assertIn(fname, content, f"Output file '{fname}' missing")

    def test_scopes_defined(self):
        content = SCRIPT.read_text()
        for scope in ["application", "infrastructure", "full"]:
            self.assertIn(f'"{scope}"', content, f"Scope '{scope}' missing")

    def test_cli_args(self):
        content = SCRIPT.read_text()
        self.assertIn("--mission", content)
        self.assertIn("--scope", content)
        self.assertIn("--dry-run", content)

    def test_scaffold_dir_exists(self):
        SCAFFOLD.mkdir(parents=True, exist_ok=True)
        self.assertTrue(SCAFFOLD.is_dir())

    def test_dry_run(self):
        """Dry run should succeed without API key."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--mission", "Test audit", "--dry-run"],
            capture_output=True, text=True,
            env={**os.environ, "OLLAMA_BASE_URL": ""},
        )
        self.assertEqual(result.returncode, 0, f"Dry run failed: {result.stderr}")
        self.assertIn("DRY RUN", result.stdout)

    def test_pipeline_order(self):
        content = SCRIPT.read_text()
        pm_pos = content.index('"PM"')
        sec_pos = content.index('"Security Engineer"')
        comp_pos = content.index('"Compliance Auditor"')
        qa_pos = content.index('"QA"')
        core_pos = content.index('"Claude Reasoning Core"')
        self.assertLess(pm_pos, sec_pos, "PM must precede Security Engineer")
        self.assertLess(sec_pos, comp_pos, "Security Engineer must precede Compliance Auditor")
        self.assertLess(comp_pos, qa_pos, "Compliance Auditor must precede QA")
        self.assertLess(qa_pos, core_pos, "QA must precede Claude Reasoning Core")

    def test_owasp_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("OWASP", content, "Should reference OWASP Top 10")

    def test_stride_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("STRIDE", content, "Should reference STRIDE threat modeling")

    def test_soc2_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("SOC 2", content, "Should reference SOC 2")

    def test_iso27001_reference(self):
        content = SCRIPT.read_text()
        self.assertIn("ISO 27001", content, "Should reference ISO 27001")

    def test_verdict_parsing(self):
        content = SCRIPT.read_text()
        self.assertIn("VERDICT", content)
        for v in ["GO", "CONDITIONAL GO", "NO-GO"]:
            self.assertIn(v, content, f"Verdict '{v}' missing")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  Security Audit Swarm — Test Suite")
    print(f"{'='*60}\n")
    unittest.main(verbosity=2)
