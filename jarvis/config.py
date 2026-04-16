"""Runtime configuration for JARVIS modules."""

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
