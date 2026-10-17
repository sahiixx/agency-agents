"""Cross-platform utility functions for system operations."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from jarvis.config import IS_LINUX, IS_WINDOWS


def command_exists(command: str) -> bool:
    """Return True when a shell command exists in PATH."""
    return shutil.which(command) is not None


def run_command(command: Sequence[str]) -> tuple[bool, str]:
    """Run a command and return success and captured output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def platform_name() -> str:
    """Return normalized platform name."""
    if IS_WINDOWS:
        return "windows"
    if IS_LINUX:
        return "linux"
    return "unknown"
