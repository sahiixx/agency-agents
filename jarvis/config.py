"""Configuration values for JARVIS."""

from __future__ import annotations

import os
import platform
from pathlib import Path

WAKE_WORD = "jarvis"
OWNER_NAME = os.getenv("JARVIS_OWNER_NAME", "Sir")
GITHUB_TOKEN = os.getenv("JARVIS_GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("JARVIS_GITHUB_USERNAME", "sahiixx")
SPEECH_RATE = int(os.getenv("JARVIS_SPEECH_RATE", "170"))
VOICE_INDEX = int(os.getenv("JARVIS_VOICE_INDEX", "0"))
LOG_LEVEL = os.getenv("JARVIS_LOG_LEVEL", "INFO")
PLATFORM = platform.system().lower()
IS_WINDOWS = PLATFORM == "windows"
IS_LINUX = PLATFORM == "linux"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "jarvis.log"
COMMANDS_FILE = DATA_DIR / "commands.json"
RESPONSES_FILE = DATA_DIR / "responses.json"
WORKFLOWS_FILE = DATA_DIR / "workflows.json"
