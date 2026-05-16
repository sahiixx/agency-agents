#!/usr/bin/env python3
"""
providers/kimi_provider.py — Kimi CLI provider for The Agency.

This provider delegates agent execution to Kimi CLI, giving your Agency agents
FULL tool access: Shell, ReadFile, WriteFile, SearchWeb, FetchURL, Agent spawning.

Usage:
    agency.py --mission "Build a landing page" --provider kimi
    agency.py --mission "Audit security" --provider kimi --work-dir ./output

Requirements:
    - Kimi CLI installed: `which kimi`
    - Valid Kimi login: `kimi login`
    - Sufficient API quota for tool-executing runs
"""

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

try:
    from providers.base import BaseProvider, ProviderResult
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from providers.base import BaseProvider, ProviderResult


class KimiProvider(BaseProvider):
    """
    Kimi CLI provider — real tool execution for Agency agents.

    Unlike Ollama (text-only), Kimi agents can:
      • Execute bash commands                (Shell)
      • Read/write project files             (ReadFile, WriteFile)
      • Search the live web                  (SearchWeb, FetchURL)
      • Spawn specialist subagents           (Agent tool)
      • Plan complex implementations         (EnterPlanMode)
    """

    name = "kimi"

    def __init__(self, model: str | None = None, timeout: int = 600):
        self.model = model
        self.timeout = timeout
        self._check_cli()

    def _check_cli(self):
        if not shutil.which("kimi"):
            raise RuntimeError(
                "Kimi CLI not found in PATH. Install: https://moonshotai.github.io/kimi-cli/"
            )

    def get_llm(self, **kwargs):
        """Kimi CLI is not a LangChain model — returns None."""
        return None

    def run_agent(
        self,
        system_prompt: str,
        query: str,
        agent_name: str = "kimi-agent",
        work_dir: str | None = None,
        **kwargs,
    ) -> ProviderResult:
        """
        Execute an agent via Kimi CLI with full tool access.

        Writes the system prompt to a temp agent file, then invokes:
            kimi --quiet --yolo --agent-file <tmp> --prompt <query> --work-dir <dir>

        Returns ProviderResult with the agent's final output.
        """
        start_time = time.time()
        work_dir = work_dir or os.getcwd()
        work_path = Path(work_dir).resolve()
        work_path.mkdir(parents=True, exist_ok=True)

        # Combine system prompt + query into a single prompt
        full_prompt = f"""{system_prompt}

---

## CURRENT MISSION

{query}

## EXECUTION CONTEXT
- Working directory: {work_path}
- You have FULL tool access: Shell, ReadFile, WriteFile, StrReplaceFile, SearchWeb, FetchURL, Agent, ReadMediaFile
- Produce production-ready output
- Report all files created or modified
"""

        # Build Kimi CLI command
        cmd = [
            "kimi",
            "--quiet",
            "--yolo",
            "--prompt", full_prompt,
            "--work-dir", str(work_path),
        ]
        if self.model:
            cmd.extend(["--model", self.model])

        env = os.environ.copy()
        # Prevent Kimi from opening editors or interactive prompts
        env["EDITOR"] = "cat"
        env["PAGER"] = "cat"

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                cwd=str(work_path),
            )

            output = self._clean_output(result.stdout)

            if result.returncode != 0:
                stderr = result.stderr[:2000] if result.stderr else "(no stderr)"
                return ProviderResult(
                    output=output,
                    provider=self.name,
                    model=self.model or "default",
                    error=f"Exit code {result.returncode}: {stderr}",
                    metadata={"duration": time.time() - start_time},
                )

            return ProviderResult(
                output=output,
                provider=self.name,
                model=self.model or "default",
                metadata={
                    "duration": round(time.time() - start_time, 2),
                    "work_dir": str(work_path),
                    "command": "kimi --quiet --yolo --prompt ...",
                },
            )

        except subprocess.TimeoutExpired:
            return ProviderResult(
                output="",
                provider=self.name,
                model=self.model or "default",
                error=f"Timeout after {self.timeout}s",
                metadata={"duration": self.timeout},
            )
        except Exception as e:
            return ProviderResult(
                output="",
                provider=self.name,
                model=self.model or "default",
                error=f"{type(e).__name__}: {e}",
            )
        finally:
            pass

    def _clean_output(self, raw: str) -> str:
        """Remove Kimi session resume line and trim whitespace."""
        lines = raw.splitlines()
        # Remove "To resume this session: ..." line
        cleaned = [line for line in lines if not line.startswith("To resume this session:")]
        return "\n".join(cleaned).strip()


if __name__ == "__main__":
    # Quick sanity test
    p = KimiProvider()
    r = p.run_agent(
        system_prompt="You are a test agent. Be concise.",
        query="Say 'Kimi provider is online' and nothing else.",
        agent_name="test-agent",
    )
    print("Status:", "OK" if r.ok else "FAIL")
    print("Output:", r.output)
    print("Meta:", r.metadata)
