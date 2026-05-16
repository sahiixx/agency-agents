"""
Kimi Swarm Bridge — Wire Agency agents into Kimi CLI's real tool-execution layer.

Gives your Ollama-powered agents the ability to:
  • Execute bash commands           (Shell tool)
  • Read/write files                (ReadFile, WriteFile, StrReplaceFile)
  • Search the live web             (SearchWeb, FetchURL)
  • Spawn specialist subagents      (Agent tool)
  • Capture screenshot evidence     (ReadMediaFile)
  • Plan complex implementations    (EnterPlanMode / ExitPlanMode)

Author: AgentsOrchestrator (Kimi CLI)
Target: The Agency by sahiixx
"""

from .bridge import KimiAgent, KimiSwarm, load_agent_prompt, list_available_agents

__all__ = ["KimiAgent", "KimiSwarm", "load_agent_prompt", "list_available_agents"]
__version__ = "1.0.0"
