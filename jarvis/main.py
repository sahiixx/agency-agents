"""Entry point for the JARVIS assistant."""

from __future__ import annotations

import os

from jarvis.core.command_parser import CommandParser
from jarvis.modules.ai.personality_engine import PersonalityEngine

try:
    from jarvis.core.engine import JarvisEngine as _JarvisEngine

    JarvisEngine: type[_JarvisEngine] | None = _JarvisEngine
except ImportError:  # pragma: no cover
    JarvisEngine = None

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
    import sys
    import time
    print(BANNER)
    if JarvisEngine is not None:
        JarvisEngine().start()
        return
    app = JarvisApp()
    print(app.handle("JARVIS, status"))

    # Container / daemon mode: block forever when no TTY is present
    if os.getenv("JARVIS_DAEMON") or not sys.stdin or not sys.stdin.isatty():
        print("[JARVIS] Daemon mode active. Standing by for commands.")
        while True:
            time.sleep(60)

    # Interactive CLI mode
    print("\nType 'quit' to exit.")
    while True:
        try:
            text = input("[You] ").strip()
            if text.lower() in ("quit", "exit", "bye"):
                break
            if text:
                print(app.handle(text))
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    main()
