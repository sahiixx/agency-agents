#!/usr/bin/env python3
"""
kimi_bridge/bridge.py — Core bridge between Agency agent registry and Kimi CLI execution.

Reads agent .md prompts from the Agency's specialized/ tree and executes them
via Kimi CLI's Agent tool with full bash/file/web/subagent capabilities.
"""

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent.parent.resolve()
AGENTS_DIR = REPO_ROOT / "specialized"
SKILL_ROOT = Path.home() / ".agents" / "skills"

# ── Agent registry mapping ───────────────────────────────────────────────────
# Maps short agent keys to their SKILL.md directory names under ~/.agents/skills/
DEFAULT_REGISTRY = {
    # Core orchestration
    "pm":               "project-manager-senior",
    "architect":        "design-ux-architect",
    "ui-designer":      "design-ui-designer",
    "ux-researcher":    "design-ux-researcher",
    # Engineering
    "frontend":         "engineering-frontend-developer",
    "backend":          "engineering-backend-architect",
    "senior-dev":       "engineering-senior-developer",
    "ai-engineer":      "engineering-ai-engineer",
    "devops":           "engineering-devops-automator",
    "security":         "engineering-security-engineer",
    "database":         "engineering-database-optimizer",
    "mobile":           "engineering-mobile-app-builder",
    "rapid-proto":      "engineering-rapid-prototyper",
    # Testing & QA
    "qa":               "testing-reality-checker",
    "evidence-qa":      "testing-evidence-collector",
    "api-tester":       "testing-api-tester",
    "perf-tester":      "testing-performance-benchmarker",
    # Marketing
    "growth":           "marketing-growth-hacker",
    "content":          "marketing-content-creator",
    "seo":              "marketing-seo-specialist",
    "social":           "marketing-social-media-strategist",
    # Sales
    "sales-strategist": "sales-deal-strategist",
    "sales-outbound":   "sales-outbound-strategist",
    # Real Estate (UAE)
    "re-leads":         "real-estate-lead-qualification-specialist",
    "re-matching":      "real-estate-property-matching-engine",
    "re-negotiation":   "real-estate-deal-negotiation-strategist",
    "re-compliance":    "real-estate-compliance-rera-guardian",
    "re-pitch":         "real-estate-investor-pitch-specialist",
    "re-crm":           "real-estate-crm-pipeline-orchestrator",
    "re-referral":      "real-estate-post-sale-referral-engine",
    "re-market":        "real-estate-market-intelligence-analyst",
    # Specialized
    "core":             "specialized-claude-reasoning-core",
    "prompt-arch":      "specialized-prompt-architect",
    "trust-graph":      "specialized-trust-graph-operator",
    "mcp-builder":      "specialized-mcp-builder",
    "linux":            "specialized-linux-sysadmin",
    "model-qa":         "specialized-model-qa",
    "reverse-engineer": "specialized-ai-tools-reverse-engineer",
    # Support
    "analytics":        "support-analytics-reporter",
    "finance":          "support-finance-tracker",
    "legal":            "support-legal-compliance-checker",
}


def _find_skill_path(key: str) -> Path | None:
    """Resolve a registry key to an actual SKILL.md file path."""
    if key not in DEFAULT_REGISTRY:
        # Try direct lookup
        for root in [SKILL_ROOT, AGENTS_DIR]:
            candidate = root / f"{key}/SKILL.md"
            if candidate.exists():
                return candidate
            candidate = root / f"{key}.md"
            if candidate.exists():
                return candidate
        return None

    rel = DEFAULT_REGISTRY[key]
    # Try ~/.agents/skills/ first (Kimi CLI skills)
    skill_path = SKILL_ROOT / rel / "SKILL.md"
    if skill_path.exists():
        return skill_path

    # Fallback to Agency specialized/ dir
    agency_path = AGENTS_DIR / f"{rel}.md"
    if agency_path.exists():
        return agency_path

    return None


def load_agent_prompt(key: str) -> str:
    """Load the system prompt for an agent by registry key."""
    path = _find_skill_path(key)
    if path is None:
        available = ", ".join(list_available_agents())
        raise KeyError(f"Agent '{key}' not found. Available: {available}")
    return path.read_text(encoding="utf-8")


def list_available_agents() -> list[str]:
    """Return all agent keys available in the registry + filesystem."""
    keys = set(DEFAULT_REGISTRY.keys())
    # Add any discovered skills on disk
    if SKILL_ROOT.exists():
        for d in SKILL_ROOT.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                keys.add(d.name)
    return sorted(keys)


class KimiAgent:
    """
    Wrapper around a single Agency agent executed via Kimi CLI subagent spawn.

    Unlike Ollama agents that generate text, KimiAgent agents can:
      - Execute bash commands (Shell)
      - Read/write project files (ReadFile, WriteFile, StrReplaceFile)
      - Search the live web (SearchWeb, FetchURL)
      - Spawn further subagents (Agent tool)
      - Capture visual evidence (ReadMediaFile)
    """

    def __init__(
        self,
        agent_key: str,
        model: str | None = None,
        timeout: int = 3600,
        working_dir: str | None = None,
    ):
        self.agent_key = agent_key
        self.prompt = load_agent_prompt(agent_key)
        self.model = model
        self.timeout = timeout
        self.working_dir = working_dir or str(Path.cwd())
        self.history: list[dict[str, Any]] = []

    def run(self, task: str, context: dict[str, str] | None = None) -> str:
        """
        Execute this agent on a task via Kimi CLI subagent spawn.

        Because we cannot directly invoke the Kimi Agent tool from Python,
        we instead generate a self-contained executable script that the user
        (or a parent orchestrator) can run inside a Kimi CLI session.

        Returns the path to the generated run-script for execution.
        """
        # Build a rich prompt with context injection
        full_prompt = self._build_prompt(task, context)

        # Generate a timestamped run script
        ts = int(time.time())
        script_name = f"run_{self.agent_key}_{ts}.py"
        script_path = Path(self.working_dir) / ".kimi_runs" / script_name
        script_path.parent.mkdir(parents=True, exist_ok=True)

        script_content = self._generate_run_script(full_prompt, ts)
        script_path.write_text(script_content, encoding="utf-8")

        # Record in history
        self.history.append({
            "task": task,
            "script": str(script_path),
            "timestamp": ts,
        })

        return str(script_path)

    def _build_prompt(self, task: str, context: dict[str, str] | None = None) -> str:
        """Inject task + shared context into the agent's system prompt."""
        ctx_blocks = []
        if context:
            for k, v in context.items():
                ctx_blocks.append(f"## {k}\n\n{v}\n")
        ctx_str = "\n".join(ctx_blocks)

        return f"""{self.prompt}

---

## CURRENT MISSION

{task}

{ctx_str}

## EXECUTION INSTRUCTIONS
- You have FULL tool access: Shell, ReadFile, WriteFile, StrReplaceFile, SearchWeb, FetchURL, Agent, ReadMediaFile
- Work in directory: {self.working_dir}
- Produce production-ready output
- If you need to spawn a specialist subagent, use the Agent tool
- Report what files you created or modified
"""

    def _generate_run_script(self, prompt: str, ts: int) -> str:
        """Generate a Python script that runs this agent in Kimi CLI."""
        escaped_prompt = json.dumps(prompt)
        model_flag = f'--model "{self.model}"' if self.model else ""

        return textwrap.dedent(f'''\
            #!/usr/bin/env python3
            """
            Auto-generated Kimi CLI run script for agent: {self.agent_key}
            Generated at: {ts}
            """
            import subprocess
            import sys

            PROMPT = {escaped_prompt}

            # This script is designed to be invoked from within a Kimi CLI session.
            # It prints the exact prompt so the parent session can feed it to a subagent.
            print("=" * 60)
            print("KIMI_AGENT_PROMPT_START")
            print(PROMPT)
            print("KIMI_AGENT_PROMPT_END")
            print("=" * 60)
            ''')


class KimiSwarm:
    """
    Orchestrate multiple KimiAgent instances in a pipeline with quality gates.

    Pipeline: PM → ArchitectUX → [Dev ↔ QA Loop] → Integration → Reality Checker
    """

    def __init__(self, working_dir: str | None = None):
        self.working_dir = working_dir or str(Path.cwd())
        self.agents: dict[str, KimiAgent] = {}
        self.results: dict[str, Any] = {}
        self.logs: list[dict[str, Any]] = []

    def register(self, key: str, agent: KimiAgent) -> "KimiSwarm":
        """Register an agent for pipeline use."""
        self.agents[key] = agent
        return self

    def step(self, agent_key: str, task: str, context_keys: list[str] | None = None) -> str:
        """
        Execute one pipeline step.

        Gathers context from previous steps, runs the agent, and stores the result.
        Returns the path to the generated run-script.
        """
        if agent_key not in self.agents:
            raise KeyError(f"Agent '{agent_key}' not registered. Registered: {list(self.agents.keys())}")

        # Gather context from previous steps
        ctx = {}
        if context_keys:
            for ck in context_keys:
                if ck in self.results:
                    ctx[ck] = self.results[ck]

        agent = self.agents[agent_key]
        script_path = agent.run(task, context=ctx)

        self.logs.append({
            "step": len(self.logs) + 1,
            "agent": agent_key,
            "task": task,
            "script": script_path,
        })

        return script_path

    def run_dev_qa_loop(
        self,
        dev_key: str,
        qa_key: str,
        task: str,
        max_retries: int = 3,
        context_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run a Dev → QA loop with retry logic.

        The dev agent implements, the QA agent validates.
        If QA fails, feed feedback back to dev (up to max_retries).
        """
        ctx = {}
        if context_keys:
            for ck in context_keys:
                if ck in self.results:
                    ctx[ck] = self.results[ck]

        dev_agent = self.agents[dev_key]
        qa_agent = self.agents[qa_key]

        for attempt in range(1, max_retries + 1):
            print(f"\n🔄 Dev-QA Loop | Attempt {attempt}/{max_retries}")

            # Dev implementation
            dev_task = task if attempt == 1 else f"{task}\n\n## QA FEEDBACK (Attempt {attempt-1})\n{qa_feedback}"
            dev_script = dev_agent.run(dev_task, context=ctx)
            print(f"  💻  Dev script: {dev_script}")

            # QA validation
            qa_task = f"Validate the implementation from {dev_key}. Check for correctness, quality, and completeness. Provide PASS or FAIL with specific feedback."
            qa_script = qa_agent.run(qa_task, context={**ctx, "dev_output": f"See script: {dev_script}"})
            print(f"  🧪  QA script:  {qa_script}")

            # In a real Kimi CLI session, these scripts would be executed and their outputs parsed.
            # For now, we record the loop structure.
            qa_feedback = f"[QA output from {qa_script}]"

            # Simulate pass for structure demonstration
            # In production, parse the QA agent's actual output
            if attempt == max_retries:
                print(f"  ⚠️  Max retries reached. Escalate to core review.")
                break

        return {
            "dev_script": dev_script,
            "qa_script": qa_script,
            "attempts": attempt,
            "status": "NEEDS_WORK" if attempt == max_retries else "PASS",
        }

    def report(self) -> str:
        """Generate a pipeline progress report."""
        lines = [
            "# Kimi Swarm Pipeline Report",
            "",
            f"**Working Directory**: `{self.working_dir}`",
            f"**Registered Agents**: {len(self.agents)}",
            f"**Completed Steps**: {len(self.logs)}",
            "",
            "## Step Log",
            "",
        ]
        for log in self.logs:
            lines.append(f"### Step {log['step']}: `{log['agent']}`")
            lines.append(f"- **Task**: {log['task']}")
            lines.append(f"- **Run Script**: `{log['script']}`")
            lines.append("")
        return "\n".join(lines)


if __name__ == "__main__":
    # Quick sanity check
    print("Available agents:", list_available_agents())
    print(f"Registry size: {len(DEFAULT_REGISTRY)}")
