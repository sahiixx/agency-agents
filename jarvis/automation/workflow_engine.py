"""Workflow engine to execute multi-step command chains."""

from __future__ import annotations

from typing import Callable

from config import WORKFLOWS_FILE
from utils.helpers import load_json, save_json


class WorkflowEngine:
    """Load, store, and execute named workflows."""

    def __init__(self) -> None:
        self.workflows = load_json(WORKFLOWS_FILE, {"workflows": {}})

    def list_workflows(self) -> list[str]:
        """Return all workflow names."""
        return sorted(self.workflows.get("workflows", {}).keys())

    def add_workflow(self, name: str, steps: list[str]) -> None:
        """Persist a workflow under the given name."""
        payload = self.workflows.setdefault("workflows", {})
        payload[name] = steps
        save_json(WORKFLOWS_FILE, self.workflows)

    def run_workflow(self, name: str, executor: Callable[[str], str]) -> list[str]:
        """Execute each command in a workflow using provided executor callback."""
        steps = self.workflows.get("workflows", {}).get(name, [])
        outputs: list[str] = []
        for step in steps:
            outputs.append(executor(step))
        return outputs
