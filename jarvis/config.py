"""Configuration values for JARVIS (v2 + v3 compatible)."""

from __future__ import annotations

import os
import platform
from pathlib import Path

# Legacy/core runtime flags
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
OLLAMA_MODEL = "kimi-k2.6:cloud"
OLLAMA_URL = "http://localhost:11434"
USE_LOCAL_LLM = True

# Whisper
WHISPER_MODEL = "base"
USE_WHISPER = True

# TTS Engine
TTS_ENGINE = "piper"  # or "pyttsx3"

# Vision
FACE_AUTH_ENABLED = True
GESTURE_CONTROL_ENABLED = True

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

# GUI (v3)
GUI_ENABLED = True
GUI_THEME = "dark"
ORB_COLOR = "#00BFFF"
ALWAYS_ON_TOP = True
SYSTEM_TRAY = True

# Emotion & Presence (v3)
EMOTION_DETECTION = True
PRESENCE_DETECTION = True
EYE_TRACKING = False
MOOD_TRACKING = True

# Creative (v3)
IMAGE_GEN_ENABLED = True
SD_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
MUSIC_GEN_ENABLED = True
VOICE_CLONING_ENABLED = True

# Productivity (v3)
GOOGLE_CALENDAR_ENABLED = True
GOOGLE_CREDENTIALS_PATH = ""
POMODORO_WORK_MINS = 25
POMODORO_BREAK_MINS = 5
FOCUS_BLOCKED_APPS = ["discord", "steam", "reddit"]

# Security (v3)
PASSWORD_VAULT_ENABLED = True
BREACH_CHECK_INTERVAL_HOURS = 24
NETWORK_SCAN_ENABLED = True

# Communication (v3)
DISCORD_BOT_TOKEN = ""
DISCORD_CHANNEL_ID = ""

# Hardware (v3)
BLUETOOTH_ENABLED = True
USB_MONITORING = True
CAFFEINE_MODE = True

# AI (v3)
PERSONALITY_MODE = "professional"
PERSISTENT_MEMORY = True
MULTI_AGENT = True
DREAM_MODE = True
LEARNING_ENGINE = True

# Auto-Update (v3)
AUTO_UPDATE_CHECK = True
GITHUB_REPO = "sahiixx/agency-agents"

# Docker (v3)
DOCKER_MODE = True
