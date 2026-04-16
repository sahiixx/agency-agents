"""Voice-first coding helper backed by local LLM prompts."""

from __future__ import annotations

import subprocess

from .ai_brain import AIBrain


class CodeAssistant:
    def __init__(self, brain: AIBrain):
        self.brain = brain

    def generate_code(self, prompt: str) -> str:
        return self.brain.ask(prompt).text

    def explain_code(self, code: str) -> str:
        return self.brain.ask(f"Explain this code:\n{code}").text

    def run_git_commit(self, message: str) -> tuple[bool, str]:
        try:
            result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, check=False)
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as exc:
            return False, str(exc)
