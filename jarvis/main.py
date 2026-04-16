"""Entry point for the JARVIS assistant."""

from __future__ import annotations

from jarvis.modules.ai.personality_engine import PersonalityEngine

try:
    from core.engine import JarvisEngine  # type: ignore
except Exception:  # pragma: no cover
    JarvisEngine = None

from jarvis.core.command_parser import CommandParser

BANNER = r"""
      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
      ██║███████║██████╔╝██║   ██║██║███████╗
 ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
 ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""


class JarvisApp:
    """Core orchestration shell fallback for non-engine mode."""

    def __init__(self) -> None:
        self.parser = CommandParser()
        self.personality = PersonalityEngine()

    def handle(self, text: str) -> str:
        command = self.parser.parse(text)
        if command.action == "todo.list":
            return self.personality.format_response("Your todo list is currently empty.")
        if command.action == "todo.add":
            return self.personality.format_response(f"Task noted: {command.payload}")
        return self.personality.format_response("At your service.")


def main() -> None:
    """Start full engine when available, otherwise run fallback shell."""
    print(BANNER)
    if JarvisEngine is not None:
        JarvisEngine().start()
        return
    app = JarvisApp()
    print(app.handle("JARVIS, status"))


if __name__ == "__main__":
    main()
