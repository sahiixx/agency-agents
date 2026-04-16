#!/usr/bin/env python3
"""Basic smoke tests for the JARVIS package."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
JARVIS_ROOT = REPO_ROOT / "jarvis"


class TestJarvisSmoke(unittest.TestCase):
    """Lightweight unit tests for local JARVIS behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(JARVIS_ROOT))
        from automation.workflow_engine import WorkflowEngine
        from core.command_parser import CommandParser
        from modules.calculator import Calculator

        cls.WorkflowEngine = WorkflowEngine
        cls.CommandParser = CommandParser
        cls.Calculator = Calculator

    def test_command_parser_matches_known_intent(self):
        parsed = self.CommandParser().parse("please volume up")
        self.assertEqual(parsed["intent"], "system_control")

    def test_calculator_evaluates_expression(self):
        result = self.Calculator().evaluate("2 + 3 * 4")
        self.assertIn("14", result)

    def test_workflow_engine_can_add_and_run_workflow(self):
        engine = self.WorkflowEngine()
        engine.add_workflow("test workflow", ["a", "b"])
        outputs = engine.run_workflow("test workflow", lambda step: f"ok-{step}")
        self.assertEqual(outputs, ["ok-a", "ok-b"])

    def test_unknown_intent_returns_unknown(self):
        parsed = self.CommandParser().parse("completely unrelated command")
        self.assertEqual(parsed["intent"], "unknown")

    def test_calculator_handles_invalid_expression(self):
        result = self.Calculator().evaluate("import os")
        self.assertIn("Calculation failed", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
