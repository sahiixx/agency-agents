# The Agency — Ollama-Powered Multi-Agent Swarm

> 152 specialized AI agents · Local Ollama · Titans Memory · Production Ready

[![CI](https://github.com/sahiixx/agency-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/sahiixx/agency-agents/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/agent__tests-19%2F19-brightgreen)](tests/agent_tests.py)
[![Lint](https://img.shields.io/badge/lint-ruff%20clean-success)](https://docs.astral.sh/ruff/)
[![Score](https://img.shields.io/badge/system%20score-90%2F90-gold)](agency.py)
[![Model](https://img.shields.io/badge/model-ollama-local-green)](https://ollama.com)

---

## What This Is

A swarm of **152 specialized AI agents** — each a `.md` file containing a system prompt and persona — orchestrated by a fully-wired Python runtime on **local Ollama**.

Every mission passes through a sequential delegation pipeline and ends with a **Reasoning Core** GO / CONDITIONAL GO / NO-GO verdict. Outcomes are stored in a **Titans-inspired surprise-weighted memory** that persists lessons across runs.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sahiixx/agency-agents
cd agency-agents

# 2. Install (one command)
bash setup.sh

# 3. Ensure Ollama is running
export OLLAMA_HOST=http://localhost:11434

# 4. Run
python3 agency.py --list-agents
python3 agency.py --mission "Build a REST API for user authentication"
```

---

## Architecture

```
agency.py                        ← Unified entry point (start here)
├── FilesystemBackend            ← Reads agent files from local disk
├── MemoryMiddleware             ← Injects memory/AGENTS.md at startup
├── SubAgentMiddleware           ← Core delegates via task tool
└── TitansMemory                 ← Surprise-weighted memory across runs

memory/
├── AGENTS.md                    ← Shared context, all agents see this
└── titans_memory.py             ← NeurIPS 2025 memory architecture

specialized/
└── specialized-claude-reasoning-core.md  ← Final GO/NO-GO gate

agency_ui.html                   ← Mission Control UI (open in browser)
setup.sh                         ← One-command install
tests/agent_tests.py             ← 19 tests (offline + live LLM)
tests/test_security_audit_swarm.py ← 15 structural tests
tests/test_real_estate_swarm.py  ← 38 structural tests
```

**Other pipeline scripts:**

| Script | Pipeline |
|---|---|
| `swarm_orchestrator.py` | PM → Dev → QA → Security → Core |
| `saas_dominance_swarm.py` | PM → Copy → Frontend → QA → Core |
| `sovereign_agency_swarm.py` | PM → Backend → AI → Frontend → QA → Core |
| `sovereign_ecosystem.py` | Observer → Refiner → Core → DevOps |
| `security_audit_swarm.py` | PM → Security → Compliance → QA → Core |
| `real_estate_swarm.py` | Leads → Matching → Deals → CRM/Pitch/Referral → Core |
| `evolution_scheduler.py` | Self-improvement — critiques and rewrites agents |
| `mission_control.py` | CLI — list and launch any single agent |

---

## Agent Presets

```bash
# Full stack (default)
python3 agency.py --mission "..." --preset full
# pm, backend, frontend, qa, security, core

# SaaS / marketing
python3 agency.py --mission "..." --preset saas
# pm, copywriter, frontend, qa, core

# Research
python3 agency.py --mission "..." --preset research
# pm, ai, qa, core

# Real estate
python3 agency.py --mission "..." --preset realestate
# re-leads, re-match, re-copy, re-deal, re-intel, re-comply, re-crm, re-pitch, re-refer, core

# Custom
python3 agency.py --mission "..." --agents security,qa,core
```

---

## Agent Roster — 161 Agents

| Directory | Agents | Domain |
|---|---|---|
| `engineering/` | 22 | Frontend, backend, DevOps, security, AI, data |
| `marketing/` | 19 | SEO, content, growth, social, paid media |
| `game-development/` | 19 | Godot, Roblox, Unity, Unreal Engine |
| `specialized/` | 25 | Orchestrators, Reasoning Core, compliance, identity |
| `integrations/` | 9 | Cursor, Claude Code, Windsurf, OpenClaw, Gemini CLI, bridges |
| `design/` | 8 | UX, brand, visual, inclusive design |
| `sales/` | 8 | Account, pipeline, proposals, coaching |
| `testing/` | 8 | QA, accessibility, performance, API |
| `paid-media/` | 7 | PPC, display, social ads, tracking |
| `project-management/` | 6 | Planning, Jira, sprint, delivery |
| `support/` | 6 | Analytics, finance, legal, infrastructure |
| `spatial-computing/` | 6 | VisionOS, XR, spatial interfaces |
| `real-estate/` | 9 | Lead gen, property matching, compliance, CRM, negotiation |
| `product/` | 4 | Strategy, research, prioritization |
| `business/` | 5 | Analytics, operations, marketing, sales, content |
| `.cursor/rules/` | 128 | Cursor IDE agent rules (`.mdc` format) |
| `skills/` | 152 | [skills.sh](https://skills.sh) compatible skills |

### Install via skills.sh

```bash
npx skills add sahiixx/agency-agents
```

---

## How Memory Works

Based on [Titans: Learning to Memorize at Test Time](https://arxiv.org/abs/2501.00663) (Google, NeurIPS 2025):

- **Attention** = short-term memory — precise, limited to context window
- **AGENTS.md** = long-term memory — persists across every run
- **Surprise metric** — unexpected verdicts (NO-GO, new patterns) decay slower and stay in memory longer
- **Forgetting gate** — routine outcomes decay and are pruned automatically

After every mission, `TitansMemory` records the verdict, computes a surprise score, and writes the most memorable outcomes back into `AGENTS.md`. The next mission's agents start informed.

---

## Commit History

| Commit | Description |
|---|---|
| `82191bd` | 🎨 Add Agency Mission Control UI |
| `584b0d4` | ✅ 98% → 100% — type hints, final eval clean |
| `a506c26` | 🔒 Regenerate all uv.lock files — resolves 18 Dependabot alerts |
| `9fab761` | 🔒 Bump stale lower bounds across all pyproject.toml files |
| `71e9ec8` | 🔒 Fix all 18 Dependabot security alerts |
| `f5d337c` | ✅ Finalized — error-free, full running setup |
| `fc47294` | ✅ Code review — all HIGH/MED issues resolved |
| `1e8084c` | 🧠 Integrate Titans memory architecture (NeurIPS 2025) |
| `3c322ec` | 🔧 Fix agency.py wiring — FilesystemBackend for MemoryMiddleware |
| `855202e` | 🏁 Complete system — all gaps closed |
| `2bddeb0` | 🏗️ Infrastructure: CI, CLAUDE.md, setup, env template |
| `0e81afb` | 🧠 Model Integration: Full Anthropic migration + Reasoning Core |

---

## Branches

| Branch | Status | Description |
|---|---|---|
| `main` | ✅ **production** | Stable — all tests passing, fully wired |
| `dependabot/uv/deepagents/libs/cli/uv-c51c02f1a9` | ⏳ auto-PR | Dependabot security update — will merge to main |

---

## System Health

```
Tests:          72/72 passing (4 need live API key)
Graph:          6 nodes — MemoryMiddleware.before_agent wired
Registry:       161 agents across 15 directories + 128 Cursor rules
Lock files:     10 checked — 0 stale vulnerable pins
Security:       dependabot.yml active — weekly auto-updates
Score:          90/90 — Grade A, Production Ready
```

---

## Tech Stack

- **Model**: `llama3.1` (or any Ollama model) via `langchain-ollama`
- **SDK**: `deepagents` v0.4.10 — LangGraph-based agent harness
- **Memory**: `FilesystemBackend` + `MemoryMiddleware` + `TitansMemory`
- **Fully offline** — no cloud API keys required

---

## Mission Control UI

Open `agency_ui.html` in any browser for a full mission control dashboard:
- Live pipeline animation per agent
- Real-time terminal stream
- Titans memory visualization
- Mission history with surprise scores
- Preset switcher and custom agent input

---

## Setup Details

```bash
# Manual install
pip install -e deepagents/libs/deepagents
pip install langchain-ollama langchain langchain-core

# Environment
export OLLAMA_HOST=http://localhost:11434

# Tests
python3 tests/agent_tests.py                        # structural (offline)
python3 tests/test_security_audit_swarm.py          # security swarm (offline)
python3 tests/test_real_estate_swarm.py             # real estate swarm (offline)
python3 tests/agent_tests.py  # + live LLM (needs Ollama running)
```

---

## CI/CD

`.github/workflows/ci.yml` runs on every push and PR:
- **Structural tests** — always run, no API key needed
- **Live LLM tests** — run on push to `main` if Ollama is available
- **Security gate** — `security-gate.yml` validates the security audit swarm on every push/PR (syntax check, test suite, dry-run)
- **Real estate gate** — `security-gate.yml` validates the real estate swarm on every push/PR (syntax check, test suite, dry-run)
- **Dependabot** — weekly pip and GitHub Actions updates, grouped by package family

Ensure Ollama is available in CI or skip live LLM tests

---

*Built on the original [The Agency](https://github.com/sahiixx/agency-agents) agent collection. Ollama migration and orchestration layer by sahiix.*

## JARVIS v3

A full desktop assistant scaffold now lives in [/jarvis](jarvis/README.md).

---

## JARVIS v2.0 (2026) — Local Voice Assistant Stack

The repository now includes a `jarvis/` package with offline-first modules for:
- **AI Brain** (`jarvis/modules/ai_brain.py`) — Ollama local LLM chat, code-generation prompts, summarization, multi-turn memory, and keyword fallback.
- **Whisper STT** (`jarvis/core/whisper_stt.py`) — faster-whisper transcription with fallback callback support.
- **Advanced TTS** (`jarvis/core/advanced_tts.py`) — Piper-first speech engine with pyttsx3 fallback, profile/emotion/SSML-safe output.
- **Vision stack** (`jarvis/modules/vision/`) — face auth, gestures, OCR screen reading, YOLO object detection wrappers.
- **Knowledge Base** (`jarvis/modules/knowledge_base.py`) — local SQLite index with FAISS-aware local RAG scaffolding.
- **Security/Privacy** (`jarvis/modules/security/`) — encryption vault and privacy report + redaction guard.
- **Smart Home** (`jarvis/modules/smart_home.py`) — Home Assistant REST controls.
- **System Dashboard** (`jarvis/modules/system_dashboard.py`) — CPU/RAM/disk/GPU metric snapshots, alert thresholds, and history persistence.
- **Media/Comms/Translation/Coding/Clipboard** modules in `jarvis/modules/`.
- **Plugin system** (`jarvis/plugins/`) — plugin base, manager, and example plugin.
- **Web Dashboard** (`jarvis/dashboard/`) — FastAPI app + template/static assets.
- **Automation upgrades** (`jarvis/automation/`) — smart routines and voice macro recording/import/export.

### JARVIS Config

`jarvis/config.py` includes:
- `OLLAMA_MODEL`, `OLLAMA_URL`, `USE_LOCAL_LLM`
- `WHISPER_MODEL`, `USE_WHISPER`
- `TTS_ENGINE`
- `FACE_AUTH_ENABLED`, `GESTURE_CONTROL_ENABLED`
- `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `DASHBOARD_PORT`, `DASHBOARD_ENABLED`
- `ENCRYPTION_ENABLED`
- `KNOWLEDGE_BASE_DIR`, `AUTO_INDEX_ON_STARTUP`

### Ollama Setup Guide
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
ollama pull mistral
ollama pull qwen2.5
ollama pull deepseek-coder
```
Run local server: `ollama serve` (default `http://localhost:11434`).

### Whisper Setup Guide
```bash
pip install faster-whisper
```
Set `USE_WHISPER=True` and choose `WHISPER_MODEL` from `tiny/base/small/medium/large-v3`.

### Face Recognition Setup
- Install: `pip install face-recognition opencv-python`
- Use `FaceAuth.register_face(user_id, encoding)` to enroll users.
- Start background checks with `start_background_auth()`.

### Smart Home Integration
- Add `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN`.
- Use `SmartHomeController.call_service(domain, service, payload)`.

### Spotify API Setup
- Create app at Spotify Developer Dashboard.
- Fill `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`.
- Install: `pip install spotipy`.

### Telegram Bot Setup
- Create bot via BotFather.
- Set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
- Install: `pip install python-telegram-bot`.

### Plugin Development Guide
- Create plugin in `jarvis/plugins/*.py`
- Inherit `PluginBase`
- Implement `execute(command: str) -> str`
- Load plugins via `PluginManager.discover()`

### Web Dashboard Usage
```bash
uvicorn jarvis.dashboard.app:app --host 127.0.0.1 --port 8080
```
Open `http://localhost:8080`.

### Updated Command Surface (100+ intents via module mapping)
Command groups now include:
- Conversation, summarization, and code prompts
- STT/TTS controls
- Face auth + gesture control + OCR + object detection
- RAG document search/add/remove
- Privacy report/redaction/encryption actions
- Smart-home actions and status checks
- System status and performance alerts
- Spotify/YouTube media commands
- Telegram remote controls and notifications
- Translation and live conversation translation
- Voice coding and git voice actions
- Clipboard summarize/translate/rewrite/history
- Plugin list/enable/disable/execute
- Smart routine and macro record/replay/export/import

### JARVIS Architecture (text diagram)
```
Speech In (Whisper) -> Intent Layer -> AI Brain (Ollama) -> Action Router
                                         |-> RAG Knowledge Base (SQLite/FAISS)
                                         |-> Vision (Face/Gesture/OCR/YOLO)
                                         |-> Security/Privacy (Fernet/PII Guard)
                                         |-> Smart Home / Media / Comms / Translation
                                         |-> Coding Assistant / Clipboard AI / Plugins
Action Router -> TTS (Piper/pyttsx3) -> Speech Out
Background Threads: Vision + Metrics + Dashboard
Persistent Storage: SQLite (metrics/docs/history)
```

### Performance Tips
- Prefer `tiny/base` Whisper for low-latency CPUs; use `large-v3` with GPU.
- Use smaller Ollama model for fast response (`llama3:8b`) and larger models for reasoning quality.
- Enable GPU for `faster-whisper`, YOLO, and embeddings when available.
- Keep dashboard and heavy vision loops on separate threads.
- Trim document index scope for faster local RAG response times.

*Built on the original [The Agency](https://github.com/sahiixx/agency-agents) agent collection. Orchestration layer by Sonnet 4.6, plus JARVIS local assistant modules.*
