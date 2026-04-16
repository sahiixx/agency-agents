# JARVIS Voice-Controlled AI Assistant

A cross-platform (Windows + Linux) voice assistant with wake-word support, speech I/O, command parsing, system controls, automation workflows, and utility modules.

## Features

- Continuous listening with wake word (`jarvis` / `hey jarvis`)
- Speech-to-text using `SpeechRecognition` + Google Speech API
- Offline text-to-speech via `pyttsx3` with queue-based speaking
- Keyword + fuzzy intent matching from `data/commands.json`
- Cross-platform system controls (volume/power/lock/sleep)
- App launch/close, web search, screenshots, notes, reminders
- Weather/news, jokes, datetime, battery/network/process insights
- GitHub integration (list repos, repo status, issue creation)
- Workflow and task scheduling framework
- Logging to `jarvis/data/jarvis.log`

## Installation

### 1) Create environment

```bash
cd jarvis
python3 -m venv .venv
source .venv/bin/activate  # Linux
# .venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
```

### 2) PyAudio notes

- **Linux** (Debian/Ubuntu):
  ```bash
  sudo apt update
  sudo apt install -y portaudio19-dev python3-pyaudio
  pip install pyaudio
  ```
- **Windows**:
  - Install a matching wheel for your Python version, then:
  ```powershell
  pip install pyaudio
  ```

## Configuration

Edit environment variables (optional):

- `JARVIS_OWNER_NAME` (default: `Sir`)
- `JARVIS_GITHUB_TOKEN` (optional, required for issue creation)
- `JARVIS_GITHUB_USERNAME` (default: `sahiixx`)
- `JARVIS_NEWS_API_KEY` (optional for live headlines)
- `JARVIS_SMTP_SERVER`, `JARVIS_SMTP_PORT`, `JARVIS_SMTP_USERNAME`, `JARVIS_SMTP_PASSWORD`

Defaults are in `config.py`.

## Run

```bash
cd jarvis
python main.py
```

Say commands like:

- `jarvis open chrome`
- `hey jarvis what's the weather in dubai`
- `jarvis list repos`
- `jarvis take screenshot`
- `jarvis calculate 18 * 7`
- `jarvis goodbye`

## Supported Command Categories

- **System Control**: volume, mute, brightness, shutdown, restart, sleep, lock
- **Apps**: open/close apps by name
- **Files**: create/delete/move/copy/search
- **Web/Search**: open websites, Google/YouTube/Wikipedia search
- **Media**: play/pause/next/previous
- **Clipboard**: copy/paste/history buffer
- **Screen**: screenshots (+ recording placeholder hook)
- **Info**: weather, news, datetime, battery, network, processes
- **Productivity**: reminders, notes, calculator
- **GitHub**: list repos, repo status, create issue
- **Automation**: reusable workflows, recurring schedules, macros

## Custom Commands

Add/modify intents in `data/commands.json`:

1. Add a new object under `intents`
2. Set `name`, `action`, and `keywords`
3. Map that intent in `core/engine.py` to a module action

## Workflows

Workflows live in `data/workflows.json`:

```json
{
  "workflows": {
    "my routine": ["open youtube", "tell me the news"]
  }
}
```

Use `automation/workflow_engine.py` to run chains through the engine executor.

## Troubleshooting

- **No microphone found**: JARVIS falls back to keyboard input.
- **Speech not audible**: verify speaker output and pyttsx3 engine availability.
- **Linux media controls fail**: install `playerctl`.
- **Brightness/volume control incomplete**: install platform tools (`amixer`, `pactl`, `screen-brightness-control`, `pycaw`).
- **GitHub issue creation fails**: set a valid `JARVIS_GITHUB_TOKEN` with repo scope.
