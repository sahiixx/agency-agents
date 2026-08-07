"""Jarvis operator integration for The Agency

This module provides a lightweight operator bridge so Jarvis can act as the
Agency operator. It attempts to use jarvis' AI brain when available and
falls back to a simple stdin interactive loop otherwise.

Safety: by default missions run in dry-run mode. To allow live missions that
call cloud LLMs, set environment variable JARVIS_OPERATOR_ALLOW_LIVE=1.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Optional


def _log(msg: str) -> None:
    print(f"[jarvis.operator] {msg}")


class JarvisOperator:
    """Operator that accepts commands (voice/text) and dispatches to agency.run_mission.

    Behavior:
    - If jarvis' AI brain is importable, uses it to parse / capture missions.
    - Otherwise, falls back to an interactive stdin loop.
    - By default runs with dry_run=True to avoid accidental live LLM calls. Set
      JARVIS_OPERATOR_ALLOW_LIVE=1 to enable live runs.
    """

    def __init__(self, allow_live: Optional[bool] = None) -> None:
        self.allow_live = (
            allow_live
            if allow_live is not None
            else os.getenv("JARVIS_OPERATOR_ALLOW_LIVE", "0") == "1"
        )
        self._brain = None
        try:
            # jarvis.modules.ai_brain should exist per repo README — try to use it
            from jarvis.modules.ai_brain import AIBrain  # type: ignore

            _log("Found Jarvis AIBrain — using it for natural language capture")
            # instantiate a brain instance with default config if available
            try:
                self._brain = AIBrain()
            except Exception as e:  # fallback if AIBrain requires args
                _log(f"AIBrain constructor failed, continuing without brain: {e}")
                self._brain = None
        except Exception:
            _log("Jarvis AIBrain not available — falling back to stdin operator")

    def _parse_command(self, text: str) -> dict:
        """Parse a short natural-language command into mission parameters.

        Returns a dict with keys: mission (str), preset (Optional[str]), agents (Optional[list[str]]), dry_run (bool)
        """
        mission = text.strip()
        preset = None
        agents = None
        dry_run = not self.allow_live

        # quick heuristics: user can include --preset <name> or --agents a,b,c in text
        if "--preset" in mission:
            parts = mission.split()
            for i, p in enumerate(parts):
                if p == "--preset" and i + 1 < len(parts):
                    preset = parts[i + 1]
        if "--agents" in mission:
            parts = mission.split()
            for i, p in enumerate(parts):
                if p == "--agents" and i + 1 < len(parts):
                    agents = [a.strip() for a in parts[i + 1].split(",") if a.strip()]

        # strip flag tokens from mission for clarity
        clean = mission.replace("--preset", "").replace("--agents", "")
        # remove known subsequent tokens crudely
        for token in (preset or "", ",".join(agents or [])):
            if token:
                clean = clean.replace(token, "")
        mission = clean.strip()

        return {"mission": mission, "preset": preset, "agents": agents, "dry_run": dry_run}

    def capture_and_dispatch(self) -> None:
        """Main loop: capture commands and dispatch to agency.run_mission."""
        _log(f"Starting JarvisOperator (allow_live={self.allow_live})")

        # Lazy import agency.run_mission to avoid top-level circular imports
        try:
            from agency import run_mission  # type: ignore
        except Exception as e:
            _log(f"Failed to import agency.run_mission: {e}")
            return

        if self._brain is not None:
            _log("Entering Jarvis AIBrain capture loop (type 'exit' to quit)")
            while True:
                try:
                    # ask for a natural-language mission via the AIBrain
                    prompt = "Listen for a mission (or say 'exit' to quit):"
                    try:
                        text = self._brain.ask(prompt)
                    except Exception as e:
                        _log(f"AIBrain ask failed: {e}")
                        # fallback to stdin
                        text = input("Mission: ")

                    if not text:
                        time.sleep(0.1)
                        continue
                    if text.strip().lower() in ("exit", "quit"):
                        _log("Exit requested — operator shutting down")
                        break

                    parsed = self._parse_command(text)
                    _log(f"Captured mission: {parsed['mission']!r}")
                    if parsed["dry_run"]:
                        _log("DRY RUN mode — no API calls will be made. Set JARVIS_OPERATOR_ALLOW_LIVE=1 to enable live runs.")

                    result = run_mission(
                        parsed["mission"],
                        parsed["agents"] or [],
                        preset=parsed["preset"] or "full",
                        dry_run=parsed["dry_run"],
                    )
                    _log("Mission completed — result below:\n" + (result or "[no result]"))
                except KeyboardInterrupt:
                    _log("Interrupted by user")
                    break
                except Exception as e:
                    _log(f"Operator loop error: {e}")
                    time.sleep(1)
        else:
            _log("Entering stdin interactive loop (type 'exit' to quit)")
            while True:
                try:
                    text = input("Mission> ")
                except EOFError:
                    break
                if not text:
                    continue
                if text.strip().lower() in ("exit", "quit"):
                    _log("Exit requested — operator shutting down")
                    break

                # If user provides explicit flags we honor them, else default preset
                parsed = self._parse_command(text)
                _log(f"Captured mission: {parsed['mission']!r}")
                if parsed["dry_run"]:
                    _log("DRY RUN mode — no API calls will be made. Set JARVIS_OPERATOR_ALLOW_LIVE=1 to enable live runs.")

                try:
                    result = run_mission(
                        parsed["mission"],
                        parsed["agents"] or [],
                        preset=parsed["preset"] or "full",
                        dry_run=parsed["dry_run"],
                    )
                    _log("Mission completed — result below:\n" + (result or "[no result]"))
                except Exception as e:
                    _log(f"Mission failed to run: {e}")


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="jarvis-operator")
    parser.add_argument("--allow-live", action="store_true", help="Allow live LLM calls (overrides env)")
    parser.add_argument("--mission", type=str, help="One-off mission to run (non-interactive)")
    parser.add_argument("--preset", type=str, default="full", help="Preset to use for a one-off mission")
    parser.add_argument("--agents", type=str, help="Comma-separated agent keys for one-off mission")

    args = parser.parse_args()

    op = JarvisOperator(allow_live=args.allow_live or None)

    if args.mission:
        try:
            from agency import run_mission  # type: ignore
        except Exception as e:
            _log(f"Failed to import agency.run_mission: {e}")
            sys.exit(1)

        agents = [a.strip() for a in args.agents.split(",")] if args.agents else []
        dry_run = not (op.allow_live or args.allow_live)
        _log(f"Running one-off mission (dry_run={dry_run})")
        res = run_mission(args.mission, agents, preset=args.preset, dry_run=dry_run)
        _log("One-off mission result:\n" + (res or "[no result]"))
        return

    # interactive
    op.capture_and_dispatch()


if __name__ == "__main__":
    cli()
