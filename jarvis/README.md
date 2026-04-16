# JARVIS v3.0 — Ultimate AI Desktop Companion

A cross-platform (Windows + Linux) voice assistant stack with local-first modules, automation, and extensible AI tooling.

## Quick Start (3 commands)

```bash
pip install -r requirements.txt
python jarvis/main.py
jarvis
```

## Architecture

```text
Voice I/O -> CommandParser -> Router -> Modules -> Response Engine
                         |-> PersonalityEngine
                         |-> PersistentMemory (SQLite)
                         |-> GUI (optional PyQt6)
```

## Feature Categories

- GUI + Tray + Chat History
- Emotion/Presence + Mood Tracking
- Creative Suite (Image/Music/Voice/Wallpaper)
- Productivity (Calendar, Todo, Pomodoro, Focus, Journal, Meetings)
- Security (Vault, Breach, Cleaner, Network, VPN)
- Social/Communication (Email, Discord, WhatsApp, RSS)
- Vision (Eye tracking, doc scanning, captions)
- Hardware Control (Bluetooth, display, power, USB)
- Advanced AI (memory, multi-agent, personality, learning, dream mode)
- Infrastructure (Docker, CI, package, installers, updater)

## Installation

### Linux
```bash
bash install.sh
```

### Windows
```bat
install.bat
```

## Docker

```bash
docker compose up --build
```

## Legacy v2 Compatibility

JARVIS v2 modules are still present (AI brain, dashboard, plugins, automation, and voice stack). Existing `tests/test_jarvis_v2.py` and `tests/test_jarvis_smoke.py` continue to validate compatibility.

## Module Voice Command Examples

- `JARVIS, add task: buy groceries`
- `JARVIS, what's on my todo list?`
- `JARVIS, switch to sarcastic mode`
- `JARVIS, remember that my favorite color is blue`
- `JARVIS, check for updates`

## License

MIT
