"""JARVIS v3 entrypoint."""

from __future__ import annotations

from jarvis.core.command_parser import CommandParser
from jarvis.modules.ai.personality_engine import PersonalityEngine


class JarvisApp:
    """Core orchestration shell for JARVIS."""

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
    app = JarvisApp()
    print(app.handle("JARVIS, status"))


if __name__ == "__main__":
    main()
