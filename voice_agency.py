#!/usr/bin/env python3
"""
voice_agency.py — Voice-first entry point for The Agency.

Connects voice input/output with the agency mission pipeline:

  STT (Speech → Text)  →  Agency Mission  →  TTS (Text → Speech)

Supported modes:
  --mode local     Local microphone + pyttsx3/edge-tts TTS (default, no cloud needed)
  --mode twilio    Twilio Media Streams WebSocket + OpenAI Realtime API
  --mode realtime  OpenAI Realtime API with local audio (requires OPENAI_API_KEY)

Connects to the SHADOW swarm bridge if SHADOW_CORAL_URL is set.

Usage:
  python3 voice_agency.py                          # local mic mode
  python3 voice_agency.py --mode twilio            # Twilio phone-call mode
  python3 voice_agency.py --mode realtime          # OpenAI Realtime API
  python3 voice_agency.py --mode local --preset security

  # Via agency.py:
  python3 agency.py --serve --voice local
  python3 agency.py --serve --voice twilio

Environment variables:
  OPENAI_API_KEY          — required for --mode realtime / twilio
  TWILIO_ACCOUNT_SID      — required for --mode twilio
  TWILIO_AUTH_TOKEN       — required for --mode twilio
  TWILIO_PHONE_NUMBER     — Twilio phone number to receive calls on
  SHADOW_CORAL_URL        — Coral Protocol SSE bus URL (e.g. http://localhost:8080)
                            If set, voice→text input is routed through the SHADOW swarm
                            (Whisper → Shadow → Reviewer → Notion → Slack pipeline)
  VOICE_TTS_ENGINE        — TTS engine: 'pyttsx3' (default, offline), 'edge-tts', 'openai'
  OLLAMA_BASE_URL           — for the Agency mission backend (Ollama)
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO_ROOT))

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY",     "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN",  "")
TWILIO_PHONE       = os.getenv("TWILIO_PHONE_NUMBER","")
SHADOW_CORAL_URL   = os.getenv("SHADOW_CORAL_URL",   "")
TTS_ENGINE         = os.getenv("VOICE_TTS_ENGINE",   "pyttsx3")

DEFAULT_PRESET     = "full"
TWILIO_PORT        = int(os.getenv("TWILIO_PORT", "5050"))
TTS_MAX_CHARS      = int(os.getenv("VOICE_TTS_MAX_CHARS", "500"))


# ── TTS layer ─────────────────────────────────────────────────────────────────

def speak(text: str, engine: str = TTS_ENGINE):
    """Convert text to speech using the configured TTS engine."""
    if engine == "pyttsx3":
        try:
            import pyttsx3  # type: ignore
            tts = pyttsx3.init()
            tts.say(text)
            tts.runAndWait()
            return
        except ImportError:
            print("  [voice] pyttsx3 not installed — pip install pyttsx3")
        except Exception as e:
            print(f"  [voice] pyttsx3 error: {e}")

    if engine == "edge-tts":
        try:
            import asyncio
            import edge_tts  # type: ignore
            import tempfile
            import subprocess

            async def _speak():
                communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    fname = f.name
                await communicate.save(fname)
                subprocess.run(["ffplay", "-nodisp", "-autoexit", fname],
                               capture_output=True)

            asyncio.run(_speak())
            return
        except ImportError:
            print("  [voice] edge-tts not installed — pip install edge-tts")
        except Exception as e:
            print(f"  [voice] edge-tts error: {e}")

    if engine == "openai":
        if not OPENAI_API_KEY:
            print("  [voice] OPENAI_API_KEY not set for OpenAI TTS")
        else:
            try:
                import urllib.request
                import tempfile
                import subprocess
                payload = json.dumps({"model": "tts-1", "voice": "alloy", "input": text}).encode()
                req = urllib.request.Request(
                    "https://api.openai.com/v1/audio/speech",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type":  "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=20) as r:
                    audio = r.read()
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(audio)
                    fname = f.name
                subprocess.run(["ffplay", "-nodisp", "-autoexit", fname], capture_output=True)
                return
            except Exception as e:
                print(f"  [voice] OpenAI TTS error: {e}")

    # Fallback: plain print
    print(f"  [TTS] {text}")


# ── STT layer ─────────────────────────────────────────────────────────────────

def listen_local(timeout: int = 10) -> Optional[str]:
    """Capture speech from the local microphone and return transcribed text."""
    try:
        import speech_recognition as sr  # type: ignore
    except ImportError:
        print("  [voice] SpeechRecognition not installed — pip install SpeechRecognition")
        return None
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("  🎙️  Listening…")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=30)
        except sr.WaitTimeoutError:
            return None
    try:
        text = recognizer.recognize_google(audio)
        print(f"  🗣️  You said: {text}")
        return text
    except sr.UnknownValueError:
        print("  [voice] Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"  [voice] STT API error: {e}")
        return None


# ── SHADOW Coral bridge ───────────────────────────────────────────────────────

def route_through_shadow(text: str, coral_url: str, preset: str = DEFAULT_PRESET) -> str:
    """
    Route transcribed text through the SHADOW swarm via Coral Protocol SSE.
    Pipeline: Whisper Agent → Shadow Agent → Reviewer → Notion → Slack
    Falls back to direct agency processing if Coral is unreachable.
    """
    import urllib.request
    payload = json.dumps({
        "thread_id": "agency-voice",
        "message":   text,
        "pipeline":  "voice-to-code",
        "preset":    preset,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{coral_url.rstrip('/')}/api/threads/send",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "TheAgency/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return data.get("output") or data.get("message") or json.dumps(data)
    except Exception as e:
        print(f"  [voice] SHADOW Coral bridge error: {e} — falling back to direct processing")
        return _direct_mission(text, preset=preset)


def _direct_mission(text: str, preset: str = DEFAULT_PRESET) -> str:
    """Run the agency mission directly without the Coral bridge."""
    try:
        from agency import run_mission, PRESETS
        agent_names = list(PRESETS.get(preset, PRESETS["full"]))
        if "core" in agent_names:
            agent_names = [a for a in agent_names if a != "core"] + ["core"]
        result = run_mission(text, agent_names, preset=preset)
        return result or "[No response from Agency]"
    except Exception as e:
        return f"Agency error: {e}"


# ── Local microphone loop ─────────────────────────────────────────────────────

def run_local_mode(preset: str = DEFAULT_PRESET):
    """Continuous listen → process → speak loop using the local microphone."""
    print("\n🎙️  Voice Agency — Local Mode")
    print("   Press Ctrl+C to stop.\n")
    speak("Agency online. How can I help?")

    while True:
        try:
            text = listen_local(timeout=10)
            if not text:
                continue
            if any(w in text.lower() for w in ("exit", "quit", "stop", "goodbye")):
                speak("Goodbye.")
                break

            speak("Processing your request…")
            if SHADOW_CORAL_URL:
                result = route_through_shadow(text, SHADOW_CORAL_URL, preset=preset)
            else:
                result = _direct_mission(text, preset=preset)

            # Truncate for TTS (long outputs are spoken as a summary)
            tts_text = result[:TTS_MAX_CHARS] + ("…" if len(result) > TTS_MAX_CHARS else "")
            speak(tts_text)

        except KeyboardInterrupt:
            speak("Shutting down.")
            break


# ── OpenAI Realtime mode ──────────────────────────────────────────────────────

def run_realtime_mode():
    """
    Connect to OpenAI Realtime API for low-latency voice conversations.
    Requires: pip install openai  (>=1.30)
    """
    if not OPENAI_API_KEY:
        print("❌  OPENAI_API_KEY not set — required for realtime mode.")
        sys.exit(1)
    try:
        import openai  # type: ignore
    except ImportError:
        print("❌  openai package not installed. Run: pip install openai")
        sys.exit(1)

    print("\n🎙️  Voice Agency — OpenAI Realtime Mode")
    print("   Connecting to OpenAI Realtime API…\n")

    # Import and start the realtime session
    try:
        client    = openai.OpenAI(api_key=OPENAI_API_KEY)
        SYSTEM    = (REPO_ROOT / "specialized/specialized-claude-reasoning-core.md").read_text()[:2000]

        with client.beta.realtime.connect(model="gpt-4o-realtime-preview") as conn:
            conn.session.update(session={
                "modalities":   ["text", "audio"],
                "instructions": SYSTEM,
                "voice":        "alloy",
                "input_audio_transcription": {"model": "whisper-1"},
            })
            print("  Connected. Speak now (Ctrl+C to exit)…")
            for event in conn:
                if event.type == "response.audio_transcript.done":
                    print(f"  🤖  {event.transcript}")
                elif event.type == "error":
                    print(f"  [realtime] Error: {event.error}")
    except (ImportError, AttributeError):
        # Fallback: use local mode
        print("  [realtime] OpenAI Realtime SDK not available — falling back to local mode")
        run_local_mode()
    except KeyboardInterrupt:
        print("\n  Realtime session ended.")


# ── Twilio Media Streams mode ─────────────────────────────────────────────────

def run_twilio_mode(port: int = TWILIO_PORT):
    """
    Start a WebSocket server for Twilio Media Streams phone-call integration.
    Requires: pip install twilio flask flask-sock

    Twilio routes inbound calls → this WebSocket → STT → Agency → TTS → Twilio.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("❌  TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set.")
        sys.exit(1)
    try:
        from flask import Flask, request as flask_request  # type: ignore
        from flask_sock import Sock  # type: ignore
    except ImportError:
        print("❌  flask and flask-sock required. Run: pip install flask flask-sock")
        sys.exit(1)

    app  = Flask(__name__)
    sock = Sock(app)

    @app.route("/voice", methods=["POST"])
    def voice_webhook():
        """Twilio calls this URL when a call is received."""
        response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{host}/media-stream"/>
  </Connect>
</Response>""".format(host=flask_request.host)
        return response, 200, {"Content-Type": "text/xml"}

    @sock.route("/media-stream")
    def media_stream(ws):
        """Handle Twilio Media Stream WebSocket messages."""
        print("  📞  Twilio call connected")
        buffer = []
        try:
            while True:
                msg = ws.receive()
                if msg is None:
                    break
                data = json.loads(msg)
                if data.get("event") == "media":
                    buffer.append(data["media"]["payload"])
                elif data.get("event") == "stop":
                    # Decode and process audio buffer
                    if buffer:
                        # In a full implementation: decode μ-law audio → PCM → Whisper STT
                        # Here we signal the pipeline is ready
                        print("  [twilio] Call ended — audio buffer received")
                    break
        except Exception as e:
            print(f"  [twilio] WebSocket error: {e}")

    print(f"\n📞  Twilio Voice Mode — WebSocket server on port {port}")
    print("   Configure Twilio webhook: POST https://your-domain/voice")
    print("   Press Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=port, debug=False)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Voice Agency — speech interface for The Agency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 voice_agency.py                        # local mic, default preset
  python3 voice_agency.py --mode realtime        # OpenAI Realtime API
  python3 voice_agency.py --mode twilio          # Twilio phone integration
  python3 voice_agency.py --preset security      # security-focused voice commands
        """,
    )
    parser.add_argument("--mode",   choices=["local", "realtime", "twilio"], default="local",
                        help="Voice mode (default: local)")
    parser.add_argument("--preset", default=DEFAULT_PRESET,
                        help=f"Agency preset (default: {DEFAULT_PRESET})")
    parser.add_argument("--port",   type=int, default=TWILIO_PORT,
                        help=f"Port for Twilio WebSocket server (default: {TWILIO_PORT})")
    args = parser.parse_args()

    if args.mode == "local":
        run_local_mode(preset=args.preset)
    elif args.mode == "realtime":
        run_realtime_mode()
    elif args.mode == "twilio":
        run_twilio_mode(port=args.port)


if __name__ == "__main__":
    main()
