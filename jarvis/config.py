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

# AI Brain
OLLAMA_MODEL = "llama3"
OLLAMA_URL = "http://localhost:11434"
USE_LOCAL_LLM = True

# Whisper
WHISPER_MODEL = "base"
USE_WHISPER = True

# TTS Engine
TTS_ENGINE = "piper"  # or "pyttsx3"

# Vision
FACE_AUTH_ENABLED = False
GESTURE_CONTROL_ENABLED = False

# Smart Home
HOME_ASSISTANT_URL = ""
HOME_ASSISTANT_TOKEN = ""

# Spotify
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""

# Telegram
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Dashboard
DASHBOARD_PORT = 8080
DASHBOARD_ENABLED = True

# Security
ENCRYPTION_ENABLED = True

# Knowledge Base
KNOWLEDGE_BASE_DIR = "~/Documents"
AUTO_INDEX_ON_STARTUP = True
