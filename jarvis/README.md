# JARVIS v3.0 — Ultimate AI Desktop Companion

```text
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

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

## Installation Guide

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

## Module Voice Command Examples

- `JARVIS, add task: buy groceries`
- `JARVIS, what's on my todo list?`
- `JARVIS, switch to sarcastic mode`
- `JARVIS, remember that my favorite color is blue`
- `JARVIS, check for updates`

## Configuration

See `jarvis/config.py` for all feature toggles including GUI, creative tools, security, AI personality, updater, and docker mode.

## Plugin Development

Create plugins with `jarvis/core/plugin_system.py` and register callbacks via `PluginSystem.register(name, callback)`.

## Custom Personalities

Adjust mode via `PersonalityEngine.set_mode(...)` or extend `_MODE_PREFIX` in `jarvis/modules/ai/personality_engine.py`.

## Automation Workflows

Combine `CommandParser` + module calls in custom scripts for routines such as morning briefing, focus sessions, and dream mode maintenance.

## FAQ & Troubleshooting

- Missing dependency? JARVIS modules degrade gracefully and show install hints.
- No GUI? Install `PyQt6` and enable `GUI_ENABLED`.
- No cloud APIs? Local fallbacks remain available.

## Command Reference (starter)

| Module | Command |
|---|---|
| Todo | `JARVIS, add task: ...` |
| Todo | `JARVIS, what's on my todo list?` |
| Personality | `JARVIS, switch to casual mode` |
| Memory | `JARVIS, remember that ...` |
| Updater | `JARVIS, check for updates` |

## Screenshots/Mockups

- GUI orb mockup: _placeholder_
- Dashboard mockup: _placeholder_

## Roadmap

- Real-time wake-word + streaming STT/TTS
- Full local multi-agent chain execution
- Expanded command catalog and plugin marketplace

## License

MIT

## Credits

Built in `sahiixx/agency-agents`.
