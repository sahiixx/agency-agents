# The Agency — Architecture Reference

> Comprehensive documentation of the repository architecture, components, data flow, and operational model.

---

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Core Components](#2-core-components)
3. [Agent System](#3-agent-system)
4. [Swarms & Orchestration](#4-swarms--orchestration)
5. [Dependencies](#5-dependencies)
6. [Configuration](#6-configuration)
7. [Entry Points](#7-entry-points)
8. [Data Models](#8-data-models)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment](#10-deployment)
11. [Integration Points](#11-integration-points)
12. [MCP Tools Reference](#12-mcp-tools-reference)

---

## 1. Project Structure

```
agency-agents/
│
├── agency.py                    ← Unified orchestrator & CLI entry point
├── swarm_orchestrator.py        ← Legacy sequential swarm (PM → Dev → QA → Core)
├── saas_dominance_swarm.py      ← SaaS-specific pipeline
├── sovereign_agency_swarm.py    ← Full-stack + AI pipeline
├── real_estate_swarm.py         ← Dubai real estate pipeline
├── security_audit_swarm.py      ← Security audit pipeline
├── sovereign_ecosystem.py       ← Observer → Refiner self-improvement loop
├── evolution_scheduler.py       ← Autonomous agent self-improvement via Claude Core
├── mission_control.py           ← CLI to list and launch single agents
├── run_custom_agent.py          ← Run any single agent interactively
├── run_deep_research.py         ← Deep research pipeline
├── live_run.py / live_server.py ← Live session helpers
├── swarm_stress_test.py         ← Concurrency / load testing
├── voice_agency.py              ← Voice interface (Twilio + local TTS)
│
├── mcp_tools.py                 ← 19 LangChain-compatible MCP tools
├── mcp_registry.py              ← Dynamic MCP server discovery & registration
├── a2a_protocol.py              ← Google A2A v0.3 protocol (servers + client)
├── observability.py             ← Tracing, cost tracking, span management
│
├── memory/
│   ├── AGENTS.md                ← Shared runtime context (all agents see this)
│   └── titans_memory.py         ← Titans-inspired surprise-weighted long-term memory
│
├── providers/                   ← Multi-provider abstraction layer (7 providers)
│   ├── __init__.py              ← get_provider() factory
│   ├── base.py                  ← BaseProvider ABC + ProviderResult dataclass
│   ├── anthropic_provider.py    ← Claude (default)
│   ├── ollama_provider.py       ← Local Ollama models
│   ├── openai_provider.py       ← OpenAI Agents SDK
│   ├── adk_provider.py          ← Google Agent Development Kit
│   ├── autogen_provider.py      ← Microsoft AutoGen
│   ├── rasa_provider.py         ← Rasa Open Source
│   └── n8n_provider.py          ← n8n workflow webhooks
│
├── engineering/                  ← 22 agents (backend, frontend, security, DevOps, AI, etc.)
├── marketing/                   ← 19 agents (SEO, content, growth, social, paid media)
├── specialized/                 ← 24 agents (Claude Core, orchestrators, compliance, identity)
├── design/                      ←  8 agents (UX, brand, visual, inclusive)
├── sales/                       ←  8 agents (deals, pipeline, proposals, coaching)
├── testing/                     ←  8 agents (QA, accessibility, performance, API)
├── paid-media/                  ←  7 agents (PPC, display, social ads, tracking)
├── project-management/          ←  6 agents (PM, Jira, sprint, delivery)
├── spatial-computing/           ←  6 agents (VisionOS, XR, macOS Metal)
├── support/                     ←  6 agents (analytics, finance, legal, infrastructure)
├── real-estate/                 ←  9 agents (Dubai RE: leads, matching, compliance, CRM)
├── game-development/            ←  5 agents (Godot, Roblox, Unity, Unreal)
├── business/                    ←  5 agents (UAE B2B: sales, marketing, content, analytics, ops)
├── integrations/                ←  9 agents (Cloudflare, Coral, SHADOW, n8n, bridges)
├── product/                     ←  4 agents (strategy, research, prioritization)
│
├── skills/                      ← skills.sh-compatible mirror (~151 skills)
├── .cursor/rules/               ← 128+ Cursor IDE agent rules (.mdc format)
├── strategy/                    ← Playbooks, runbooks, coordination templates
├── scaffold/                    ← Generated artifact output directory
├── examples/                    ← Usage examples
├── scripts/                     ← lint-agents.sh, convert.sh
│
├── cloudflare/                  ← Cloudflare Workers deployment (TypeScript)
│   └── src/index.ts             ← Durable Objects + Workflows + D1/KV + Anthropic SDK
├── dashboard/                   ← Next.js 14 web UI (mission control + chat)
│
├── tests/                       ← Test suites (structural + live LLM)
│   ├── agent_tests.py           ← 15 offline + 4 live LLM tests
│   ├── test_security_audit_swarm.py
│   └── test_real_estate_swarm.py
│
├── .github/workflows/           ← CI, security gate, Cloudflare deploy, agent linter
├── setup.sh                     ← One-command installer
├── requirements.txt             ← Python dependencies
├── .env.example                 ← Environment variable template
├── agency_ui.html               ← Static mission control UI
├── agency_viz.html              ← Agent network visualization
└── CLAUDE.md                    ← Auto-loaded context for Claude Code sessions
```

---

## 2. Core Components

### 2.1 Agency Orchestrator (`agency.py`)

The unified entry point — all missions flow through here.

**Key structures:**

| Symbol | Location | Purpose |
|---|---|---|
| `AGENT_REGISTRY` | `agency.py:69–106` | Maps 36 named keys → `(file_path, description)` tuples |
| `PRESETS` | `agency.py:108–134` | 13 named preset pipelines (e.g. `full`, `saas`, `dubai`) |
| `PARALLEL_GROUPS` | `agency.py:204–217` | Parallel execution plans per preset |
| `run_mission()` | `agency.py:226–390` | Core mission runner: LLM init → A2A servers → subagents → orchestrate → verdict → memory |
| `get_llm()` | `agency.py:138–178` | Provider-aware LLM factory |
| `build_subagent()` | `agency.py:189–197` | Creates SubAgent dicts from registry |

**Mission lifecycle:**

```
CLI args → resolve preset/agents → get_llm() → start A2A servers →
build subagents → create_deep_agent() → invoke orchestrator →
extract verdict → AgencyTracer report → TitansMemory update
```

### 2.2 Provider Layer (`providers/`)

Abstracts all LLM/agent frameworks behind a common interface:

```python
# providers/base.py
class BaseProvider(ABC):
    def get_llm(self, **kwargs) -> Any           # → LangChain chat model
    def run_agent(self, system_prompt, query, agent_name, **kwargs) -> ProviderResult
```

The `get_provider(name)` factory in `providers/__init__.py` (line 23) returns the correct implementation. Supported providers:

| Provider | Class | LLM returned | Notes |
|---|---|---|---|
| `anthropic` / `claude` | `AnthropicProvider` | `ChatAnthropic` | Default. Claude Sonnet 4.6 |
| `ollama` | `OllamaProvider` | `ChatOllama` | Local models (llama3.1, etc.) |
| `openai` | `OpenAIProvider` | `ChatOpenAI` | GPT-4o, o3, etc. |
| `adk` | `ADKProvider` | `ChatGoogleGenerativeAI` | Gemini 2.0 Flash |
| `autogen` | `AutoGenProvider` | Claude backbone | AutoGen manages its own LLM |
| `rasa` | `RasaProvider` | Claude backbone | External dialog service |
| `n8n` | `N8NProvider` | Claude backbone | Webhook trigger only |

### 2.3 Titans Memory (`memory/titans_memory.py`)

Surprise-weighted long-term memory inspired by [Titans: Learning to Memorize at Test Time](https://arxiv.org/abs/2501.00663) (Google, NeurIPS 2025).

**Key classes:**

- `MissionOutcome` — a single mission result with surprise/weight fields
- `TitansMemory` — manages a ledger of outcomes with decay and pruning

**Hyperparameters** (`titans_memory.py:37–39`):

| Constant | Value | Purpose |
|---|---|---|
| `SURPRISE_DECAY` | 0.9 | How fast past surprise fades (η) |
| `FORGET_THRESHOLD` | 0.1 | Prune entries below this weight |
| `MAX_LEDGER_ENTRIES` | 50 | Maximum ledger size |

**How it works:**

1. After every mission, `record_outcome()` decays all existing entries
2. Surprise is computed from verdict frequency vs. recent history
3. NO-GO verdicts get a +0.3 surprise boost (rarer = more memorable)
4. Low-weight entries are pruned; ledger capped at 50 entries
5. `inject_into_agents_md()` writes top-5 memorable outcomes into `memory/AGENTS.md`

### 2.4 Observability (`observability.py`)

LangSmith-style tracing without external dependencies.

**Classes:**

- `AgentSpan` — per-agent timing + token tracking
- `AgencyTracer` — collects spans, computes cost, writes JSON traces

**Pricing constants** (`observability.py:34–35`):

```python
PRICE_INPUT_PER_M  = 3.00   # $3.00 / 1M input tokens
PRICE_OUTPUT_PER_M = 15.00  # $15.00 / 1M output tokens
```

Traces are written to `/tmp/agency_outputs/trace_<timestamp>.json`.

### 2.5 A2A Protocol (`a2a_protocol.py`)

Implements [Google A2A spec v0.3](https://a2a-protocol.org/latest/specification/) (Linux Foundation, 2025).

**Components:**

- `A2AServer` — Starlette-based HTTP server per agent
- `A2AClient` — calls remote A2A agents via JSON-RPC 2.0
- `AgentCard` — discovery at `/.well-known/agent.json`
- `TaskManager` — lifecycle: `SUBMITTED → WORKING → COMPLETED/FAILED`
- `make_a2a_tools()` — wraps remote agents as LangChain tools

Agents are exposed on sequential ports starting at `BASE_PORT = 8100`.

### 2.6 MCP Registry (`mcp_registry.py`)

Dynamic tool discovery from MCP-compatible servers.

**Discovery modes:**

1. **Local file** — reads `registry.json` or `registry.yaml` from repo root
2. **Remote URL** — fetches from `MCP_REGISTRY_URL` env var
3. **Environment** — `MCP_SERVERS` (comma-separated base URLs)

Each server is queried via `GET /tools/list` (HTTP) or `POST / {"method":"tools/list"}` (JSON-RPC). Loaded tools are appended to `MCP_TOOLS` at import time.

---

## 3. Agent System

### 3.1 Agent File Format

Every agent is a Markdown file with YAML frontmatter:

```markdown
---
name: Frontend Developer
description: Expert frontend developer specializing in modern web technologies...
color: cyan
emoji: 💻                    # optional
vibe: Builds beautiful UIs   # optional
---

# Frontend Developer

## Core Mission
...

## Capabilities
...
```

Required frontmatter fields: `name`, `description`. The `color` field is used by the UI. Tests verify frontmatter presence with `content.startswith("---")`.

### 3.2 Agent Registry

The `AGENT_REGISTRY` in `agency.py:69–106` maps short keys to file paths:

```python
AGENT_REGISTRY = {
    "pm":        ("project-management/project-manager-senior.md",    "Senior project manager..."),
    "frontend":  ("engineering/engineering-frontend-developer.md",    "Frontend developer..."),
    "backend":   ("engineering/engineering-backend-architect.md",     "Backend architect..."),
    "core":      ("specialized/specialized-claude-reasoning-core.md", "Claude Reasoning Core..."),
    # ... 36 total agents registered
}
```

Not all 152 agents in the repo are registered — only those needed by presets and commonly used directly.

### 3.3 Agent Lifecycle

```
1. load_agent(path)       → reads .md file from disk
2. build_subagent(name)   → creates SubAgent dict: {name, description, system_prompt, tools, model}
3. create_deep_agent()    → SDK wires graph: MemoryMiddleware + SubAgentMiddleware
4. orchestrator.invoke()  → runs mission via task tool delegation
```

All agents receive:
- The full `MCP_TOOLS` list (19 tools) + any A2A tools
- Shared context from `memory/AGENTS.md` via `MemoryMiddleware`
- Access to spawn subagents via the `task` tool

### 3.4 Claude Reasoning Core

The special `core` agent (`specialized/specialized-claude-reasoning-core.md`) is the constitutional backbone:

- Always placed **last** in every pipeline (`agency.py:564–566`)
- Serves as the orchestrator's own system prompt (`agency.py:299`)
- Performs constitutional AI review (accuracy, safety, ethics)
- Issues final verdicts: **GO** / **CONDITIONAL GO** / **NO-GO**
- Tests verify required sections: `Core Mission`, `Non-Negotiables`, `Honesty`, `Constitutional`

### 3.5 Agent Counts by Directory

| Directory | Count | Domain |
|---|---|---|
| `specialized/` | 24 | Orchestrators, Claude Core, compliance, trust, docs |
| `engineering/` | 22 | Backend, frontend, DevOps, security, AI, data, SRE |
| `marketing/` | 19 | SEO, content, growth, social media, paid campaigns |
| `real-estate/` | 9 | Dubai RE: leads, matching, deals, compliance, CRM |
| `integrations/` | 9 | Cloudflare, Coral Protocol, SHADOW, n8n bridges |
| `design/` | 8 | UX, brand, visual storytelling, inclusive design |
| `sales/` | 8 | Deals, pipeline, proposals, coaching, discovery |
| `testing/` | 8 | QA, accessibility, performance, API, workflow |
| `paid-media/` | 7 | PPC, display, social ads, tracking, programmatic |
| `project-management/` | 6 | Senior PM, sprint, Jira, delivery, studio producer |
| `spatial-computing/` | 6 | VisionOS, XR, macOS Metal, terminal integration |
| `support/` | 6 | Analytics, finance, legal, infrastructure, responder |
| `game-development/` | 5 | Godot, Roblox, Unity, Unreal agents |
| `business/` | 5 | UAE B2B: sales, marketing, content, analytics, ops |
| `product/` | 4 | Strategy, research, prioritization |
| **Total** | **146 agent files** | + 128 `.cursor/rules/` + ~151 `skills/` |

---

## 4. Swarms & Orchestration

### 4.1 Primary Orchestrator (`agency.py`)

Uses `create_deep_agent()` from the deepagents SDK (LangGraph-based):

- `MemoryMiddleware` + `FilesystemBackend` — injects `AGENTS.md` at startup
- `SubAgentMiddleware` — appends available subagent names/descriptions to orchestrator system prompt
- Orchestrator delegates to subagents via the `task` tool by name
- **Parallel execution groups** define concurrent phases; groups run sequentially

### 4.2 Presets

Each preset defines which agents participate and how they run:

| Preset | Agents | Use Case |
|---|---|---|
| `full` | pm, backend, frontend, qa, security, core | Full-stack product build |
| `saas` | pm, copywriter, frontend, qa, core | SaaS landing page / MVP |
| `research` | pm, ai, qa, core | Research and analysis |
| `realestate` | 9 RE specialists + core | Dubai real estate pipeline |
| `dubai` | 5 biz + 3 RE + core | UAE B2B + market intel |
| `security` | security, wpscan, linux, devops, core | Security audit |
| `intel` | spy, prompt-arch, core | Competitive AI intelligence |
| `docs` | pm, docs, core | Documentation generation |
| `moltbot` | pm, backend, frontend, core | Deliver via Moltbot channels |
| `trust` | trust, re-comply, core | UAE entity trust vetting |
| `voice` | pm, backend, core | Voice-driven missions |
| `n8n` | pm, devops, backend, core | n8n workflow automation |
| `sovereign` | pm + 6 engineering + 3 biz + 2 RE + core | Full ecosystem |

**Important:** New presets must be added to both `PRESETS` and `PARALLEL_GROUPS` dicts in `agency.py`.

### 4.3 Parallel Execution Groups

Agents in the same group run concurrently; groups execute sequentially. Core always runs last.

```python
# Example: "full" preset
PARALLEL_GROUPS["full"] = [
    ["pm"],                              # Phase 1: planning (sequential)
    ["backend", "frontend", "security"], # Phase 2: build (concurrent)
    ["qa"],                              # Phase 3: quality (sequential)
    ["core"],                            # Phase 4: verdict (always last)
]
```

### 4.4 Legacy Swarm Scripts

Simpler pipelines without the full SDK infrastructure:

| Script | Pipeline | Notes |
|---|---|---|
| `swarm_orchestrator.py` | PM → Frontend → QA → Security → Core | `AgencySwarm` class, no MCP tools |
| `saas_dominance_swarm.py` | PM → Copy → Frontend → QA → Core | SaaS-focused |
| `sovereign_agency_swarm.py` | PM → Backend → AI → Frontend → QA → Core | Full-stack + AI |
| `security_audit_swarm.py` | PM → Security → Compliance → QA → Core | Security domain |
| `real_estate_swarm.py` | Leads → Match → Copy → Deal → … → Core | Dubai RE domain |
| `sovereign_ecosystem.py` | Observer → Refiner → Core → DevOps | Self-improvement |

All follow the same pattern: sequential `run_agent()` calls with `try/except`, Claude Core always last.

### 4.5 Evolution Scheduler

`evolution_scheduler.py` provides autonomous agent self-improvement:

1. Selects a random agent `.md` file
2. Uses Claude Reasoning Core to critique and rewrite it
3. Runs the test suite to verify nothing broke
4. Commits the improved version to git

---

## 5. Dependencies

### 5.1 Python (`requirements.txt`)

| Package | Version | Purpose |
|---|---|---|
| `anthropic` | ≥0.84.0 | Direct Anthropic SDK |
| `langchain` | ≥1.2.12 | Agent/chain framework |
| `langchain-core` | ≥1.2.18 | Tool/message primitives |
| `langchain-anthropic` | ≥1.3.4 | `ChatAnthropic` model wrapper |
| `langchain-google-genai` | ≥4.2.1 | Google Gemini models (ADK provider) |
| `langgraph` | ≥1.1.2 | Graph-based agent execution |
| `langsmith` | ≥0.7.16 | Tracing integration |
| `certifi` | ≥2026.1.4 | TLS certificates (security-pinned) |
| `cryptography` | ≥46.0.0 | Cryptography (security-pinned) |

### 5.2 Local SDK

**deepagents** v0.4.10 — lives at `deepagents/libs/deepagents/` (installed via `pip install -e`).

Key exports:
- `create_deep_agent()` — builds a LangGraph-based agent with middleware
- `SubAgent` — subagent type hint / dict interface
- `FilesystemBackend` — reads local files for `MemoryMiddleware`

### 5.3 Runtime Dependencies (imported but not in requirements.txt)

| Package | Used by | Purpose |
|---|---|---|
| `httpx` | `a2a_protocol.py` | Async HTTP client for A2A |
| `starlette` | `a2a_protocol.py` | A2A HTTP server |

### 5.4 Optional External CLIs

| Tool | Used by | Install |
|---|---|---|
| `ruff` | `code_lint` tool | `pip install ruff` |
| `trufflehog` | `scan_secrets` tool | `pip install trufflehog` |
| `airecon` | `airecon_scan` tool | `pip install airecon` |
| `shannon` | `web_pentest` tool | HTTP service at `SHANNON_URL` |

### 5.5 JavaScript (Cloudflare Worker)

- `@anthropic-ai/sdk` — Anthropic SDK for Workers
- `cloudflare:workers` — Durable Objects, Workflows, D1, KV
- TypeScript + `wrangler` for deployment

### 5.6 JavaScript (Dashboard)

- Next.js 14, React, `swr` for data fetching

---

## 6. Configuration

### 6.1 Environment Variables

**Required:**

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | All agent calls via Claude |
| `PYTHONPATH` | Must include `./deepagents/libs/deepagents` |

**Integration services (optional, with defaults):**

| Variable | Default | Service |
|---|---|---|
| `MOLTBOT_GATEWAY_URL` | `http://localhost:8787` | Moltbot Telegram/Discord/Slack gateway |
| `MOLTBOT_GATEWAY_TOKEN` | `""` | Auth token for Moltbot |
| `NOWHERE_AI_URL` | `http://localhost:8001` | NOWHERE.AI platform (FastAPI) |
| `NOWHERE_AI_JWT` | `""` | JWT for NOWHERE.AI auth |
| `TRUST_GRAPH_URL` | `http://localhost:8080` | Neo4j trust graph service |
| `TRUST_GRAPH_API_KEY` | `""` | API key for trust graph |
| `N8N_BASE_URL` | `http://localhost:5678` | n8n automation server |
| `N8N_API_KEY` | `""` | n8n auth |
| `N8N_WEBHOOK_PATH` | `/webhook/agency` | n8n webhook path |
| `PERPLEXICA_URL` | `http://localhost:3001` | Perplexica AI search |
| `SQLBOT_URL` | `http://localhost:8010` | SQLBot Text-to-SQL |
| `SQLBOT_DB` | `""` | SQLBot database connection |
| `AIRECON_URL` | `http://localhost:8020` | AIrecon OSINT service |
| `SHANNON_URL` | `http://localhost:8030` | Shannon web pentest service |

**MCP registry (optional):**

| Variable | Default | Purpose |
|---|---|---|
| `MCP_REGISTRY_URL` | `""` | Remote registry JSON endpoint |
| `MCP_SERVERS` | `""` | Comma-separated MCP server URLs |
| `BIFROST_URL` | `""` | Bifrost LLM gateway URL |
| `BIFROST_API_KEY` | `""` | Bifrost API key |

**Voice pipeline (optional):**

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | `""` | TTS (if using OpenAI TTS engine) |
| `TWILIO_ACCOUNT_SID` | `""` | Twilio account |
| `TWILIO_AUTH_TOKEN` | `""` | Twilio auth |
| `TWILIO_PHONE_NUMBER` | `""` | Twilio phone number |
| `SHADOW_CORAL_URL` | `""` | SHADOW Coral Protocol bridge |
| `VOICE_TTS_ENGINE` | `pyttsx3` | TTS engine (`pyttsx3` or `openai`) |
| `TWILIO_PORT` | `5050` | Twilio webhook port |
| `VOICE_TTS_MAX_CHARS` | `500` | Max TTS output characters |

**Tuning constants:**

| Variable | Default | Purpose |
|---|---|---|
| `PERPLEXICA_MAX_SOURCES` | `5` | Max search citations returned |
| `TRUFFLEHOG_MAX_FINDINGS` | `20` | Max secret scan findings |

### 6.2 Hard-coded Constants

| Constant | Value | File |
|---|---|---|
| `CLAUDE_MODEL` | `"claude-sonnet-4-6"` | `agency.py:65` |
| `MEMORY_FILE` | `"memory/AGENTS.md"` | `agency.py:66` |
| `BASE_PORT` | `8100` | `a2a_protocol.py` |
| `PRICE_INPUT_PER_M` | `$3.00` | `observability.py:34` |
| `PRICE_OUTPUT_PER_M` | `$15.00` | `observability.py:35` |
| `SURPRISE_DECAY` | `0.9` | `titans_memory.py:37` |
| `FORGET_THRESHOLD` | `0.1` | `titans_memory.py:38` |
| `MAX_LEDGER_ENTRIES` | `50` | `titans_memory.py:39` |
| `MAX_SCRAPE_LISTINGS` | `50` | `mcp_tools.py:49` |
| `HOT_DEAL_PRICE_THRESHOLD_AED` | `140,000` | `mcp_tools.py:52` |

---

## 7. Entry Points

### 7.1 Primary CLI (`agency.py`)

```bash
# List all agents and presets
python3 agency.py --list-agents

# Run a mission with a preset
python3 agency.py --mission "Build a REST API" --preset full

# Custom agent selection
python3 agency.py --mission "Audit security" --agents security,qa,core

# Dry run (no API calls)
python3 agency.py --mission "Ship feature" --dry-run

# Different provider
python3 agency.py --mission "Plan sprint" --provider ollama --ollama-model llama3.1
python3 agency.py --mission "Build API" --provider openai --openai-model gpt-4o

# Extra tools
python3 agency.py --mission "Scout targets" --tools airecon,trufflehog

# Serve mode (dashboard + A2A + voice)
python3 agency.py --serve --ui nextjs
python3 agency.py --serve --ui html

# Self-improvement
python3 agency.py --evolve
```

### 7.2 Other Scripts

| Script | Usage | Purpose |
|---|---|---|
| `swarm_orchestrator.py` | `--mission "..." [--mode full\|fast]` | Legacy sequential swarm |
| `mission_control.py` | Interactive CLI | List and launch single agents |
| `run_custom_agent.py` | Run any agent by path | One-off agent execution |
| `run_deep_research.py` | Research pipeline | Deep research missions |
| `evolution_scheduler.py` | (no args) | Random agent self-improvement |
| `a2a_protocol.py` | `--serve --preset full --port 8100` | Start A2A servers |
| `a2a_protocol.py` | `--call http://... --task "..."` | Call remote A2A agent |
| `voice_agency.py` | `--mode twilio\|local` | Voice pipeline |
| `live_server.py` | (starts server) | Live streaming interface |
| `setup.sh` | `bash setup.sh` | One-command install + verify |

---

## 8. Data Models

### 8.1 MissionOutcome (`memory/titans_memory.py:42`)

```python
class MissionOutcome:
    mission:  str       # Goal text
    verdict:  str       # "GO" | "NO-GO" | "CONDITIONAL GO"
    surprise: float     # 0.0 (routine) → 1.0 (unexpected)
    weight:   float     # Decays via: weight *= η * (1 - surprise * 0.3)
    ts:       str       # ISO 8601 UTC timestamp
```

Persisted as JSON in `memory/mission_ledger.json`.

### 8.2 ProviderResult (`providers/base.py:16`)

```python
@dataclass
class ProviderResult:
    output:   str              # Agent response text
    provider: str              # Provider name
    model:    str = ""         # Model identifier
    metadata: dict = {}        # Extra provider-specific data
    error:    Optional[str]    # None if successful

    @property
    def ok(self) -> bool:      # True if error is None
```

### 8.3 AgentSpan (`observability.py:39`)

```python
@dataclass
class AgentSpan:
    agent:         str
    started_at:    float       # time.time()
    ended_at:      float
    input_tokens:  int
    output_tokens: int
    error:         Optional[str]

    @property latency_ms -> float
    @property cost_usd   -> float   # Based on Sonnet 4.6 pricing
```

### 8.4 A2A Task (`a2a_protocol.py:81`)

```python
@dataclass
class A2ATask:
    id:        str             # UUID
    contextId: str             # UUID
    status:    TaskStatus      # state + timestamp + message
    artifacts: list[Artifact]  # [{artifactId, name, parts: [{text}]}]
    metadata:  dict

class TaskState(str, Enum):
    SUBMITTED  = "TASK_STATE_SUBMITTED"
    WORKING    = "TASK_STATE_WORKING"
    COMPLETED  = "TASK_STATE_COMPLETED"
    FAILED     = "TASK_STATE_FAILED"
    CANCELED   = "TASK_STATE_CANCELED"
```

### 8.5 SubAgent Dict (runtime, `agency.py:191`)

```python
{
    "name":          str,         # Registry key (e.g. "pm", "backend")
    "description":   str,         # Human-readable description
    "system_prompt": str,         # Full .md file content
    "tools":         list[Tool],  # MCP_TOOLS + A2A tools
    "model":         ChatAnthropic,
}
```

### 8.6 Trace JSON (output format)

Written to `/tmp/agency_outputs/trace_<YYYYMMDD_HHMMSS>.json`:

```json
{
  "trace_id": "20260414_173000",
  "mission": "Build a REST API",
  "preset": "full",
  "verdict": "GO",
  "total_ms": 12345.6,
  "total_cost_usd": 0.0234,
  "total_input_tokens": 5000,
  "total_output_tokens": 3000,
  "model": "claude-sonnet-4-6",
  "spans": [
    {
      "agent": "pm",
      "latency_ms": 3000.0,
      "input_tokens": 1200,
      "output_tokens": 800,
      "cost_usd": 0.0156,
      "error": null
    }
  ]
}
```

### 8.7 MCP Registry Format (`registry.json`)

```json
{
  "servers": [
    {
      "name": "custom-tool-server",
      "url": "http://localhost:8080",
      "description": "My custom tools",
      "transport": "http",
      "tags": ["search", "data"]
    }
  ]
}
```

---

## 9. Testing Strategy

### 9.1 Test Files

| File | Tests | Type | API Key? |
|---|---|---|---|
| `tests/agent_tests.py` | 15 offline + 4 live | Structural + identity | Live tests need `ANTHROPIC_API_KEY` |
| `tests/test_security_audit_swarm.py` | ~15 | Structural | No |
| `tests/test_real_estate_swarm.py` | ~18 | Structural | No |

### 9.2 Structural Tests (no API key)

- **`TestAgentFiles`**: Required `.md` files exist, have frontmatter (`---`), are not empty (>500 chars), total count >50, reasoning core has required sections (`Core Mission`, `Non-Negotiables`, `Honesty`, `Constitutional`)
- **`TestScripts`**: Required `.py` scripts exist, parse cleanly (`py_compile`), no `langchain_openai`/`ChatOpenAI` imports (Claude-native), `ChatAnthropic` present in swarm scripts, reasoning core referenced in all swarms
- **`TestReadme`**: `README.md` and `README_CLAUDE.md` exist, Claude README has setup instructions

### 9.3 Live LLM Tests (API key required)

Decorated with `@unittest.skipUnless(LIVE, ...)`:

- **Agent identity**: Calls Claude with each agent's system prompt, verifies persona keywords in response
- **Harmful output refusal**: Verifies reasoning core flags misleading claims (e.g. "cures cancer" marketing)

### 9.4 Running Tests

```bash
# Structural only (no API key needed)
python3 tests/agent_tests.py -v
python3 tests/test_security_audit_swarm.py -v
python3 tests/test_real_estate_swarm.py -v

# Including live LLM tests
ANTHROPIC_API_KEY=sk-ant-... python3 tests/agent_tests.py -v
```

### 9.5 CI Pipelines

| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | push/PR to `main` | Structural tests, agent lint (PR only), live LLM (push to main) |
| `security-gate.yml` | push/PR to `main` | Syntax check + test suite + dry-run for security & RE swarms |
| `lint-agents.yml` | (referenced by ci.yml) | Lint changed agent `.md` files via `scripts/lint-agents.sh` |
| `deploy-cloudflare.yml` | push to `main` (cloudflare/ changes) | TypeScript check + Wrangler deploy |

### 9.6 Dry-Run Support

Both `agency.py --dry-run` and individual swarm `--dry-run` flags print the full pipeline without making API calls. Used as CI gates in `security-gate.yml`.

---

## 10. Deployment

### 10.1 Local Development

```bash
# One-command setup
bash setup.sh

# Manual setup
pip install -e deepagents/libs/deepagents
pip install langchain-anthropic anthropic langchain langchain-core
export ANTHROPIC_API_KEY="sk-ant-..."
```

Requires Python 3.11+.

### 10.2 Serve Mode (Local)

```bash
# Static HTML UI + A2A server
python3 agency.py --serve --ui html

# Next.js dashboard + A2A server + voice
python3 agency.py --serve --ui nextjs
```

This starts:
1. A2A server on port 8100 (via `a2a_protocol.py --serve`)
2. Dashboard UI (Next.js at port 3000, or static HTML)
3. Voice pipeline (optional, Twilio or local TTS)

### 10.3 Cloudflare Workers (Production)

The `cloudflare/` directory contains a production-grade Cloudflare Workers deployment:

**Architecture:**
- `MissionRoom` (Durable Object) — SQLite-backed live mission state, WebSocket fan-out
- `MissionWorkflow` (Cloudflare Workflows) — durable multi-agent pipeline with retryable steps
- `AGENCY_KV` — Titans memory ledger
- `AGENCY_DB` (D1) — structured observability traces, SQL-queryable

**Deploy:**
```bash
cd cloudflare
npm ci
npx wrangler deploy
```

Automated via `.github/workflows/deploy-cloudflare.yml` on push to `main` when `cloudflare/**` files change. Requires `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` secrets.

### 10.4 Dashboard (Next.js)

```bash
cd dashboard
npm install
npm run dev  # → http://localhost:3000
```

The dashboard proxies API calls to the A2A server at `http://localhost:8100`.

### 10.5 Skills.sh Distribution

Agents are also distributed as [skills.sh](https://skills.sh) compatible skills:

```bash
npx skills add sahiixx/agency-agents
```

Each skill lives in `skills/<name>/` with `SKILL.md` + `scripts/run.sh`.

---

## 11. Integration Points

### 11.1 First-Party Integrations

| Repo | Integration | Tools / Agents |
|---|---|---|
| `sahiixx/moltworker` | Cloudflare gateway (Telegram/Discord/Slack/Web) | `trigger_moltbot_mission` tool |
| `sahiixx/Fixfizx` | NOWHERE.AI platform (FastAPI) | `qualify_lead_nowhere`, `analyze_dubai_market`, `create_campaign_nowhere` |
| `sahiixx/Trust-graph-` | Neo4j trust graph | `query_trust_graph` tool + `trust` agent |
| `sahiixx/ae-lead-scraper---` | UAE property lead scraper | `scrape_ae_leads` tool |
| `sahiixx/SHADOW` | Coral Protocol swarm (Voice→Code→Review→Log) | `integrations/shadow-swarm-bridge.md` |
| `sahiixx/Coral-BlackboxAI-Agent` | Coral Protocol bridge | `integrations/coral-protocol-bridge.md` |
| `sahiixx/v0-nowire-os-blueprint` | Nowire OS Next.js frontend | `integrations/nowire-os-frontend.md` |
| `sahiixx/system-prompts-and-models-of-ai-tools` | 31+ AI tool system prompts | `spy` agent, `intel` preset |
| `sahiixx/Y` | Prompt pattern library (26 universal patterns) | `prompt-arch` agent |
| `sahiixx/mintlify-docs` / `sahiixx/docs` | Documentation sites (Mintlify MDX) | `docs` agent |

### 11.2 External Services

| Service | Protocol | Configuration |
|---|---|---|
| Anthropic API | HTTPS | `ANTHROPIC_API_KEY` |
| DuckDuckGo | HTTPS (no key) | Built into `web_search` tool |
| Ollama | HTTP | `--ollama-url` (default `localhost:11434`) |
| OpenAI | HTTPS | `OPENAI_API_KEY` (optional) |
| Google Gemini | HTTPS | Google credentials (for ADK provider) |
| Perplexica | HTTP | `PERPLEXICA_URL` |
| n8n | HTTP webhook | `N8N_BASE_URL` + `N8N_API_KEY` |
| Twilio | HTTPS | `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` |
| Cloudflare | Wrangler CLI | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` |
| LangSmith | HTTPS | `LANGCHAIN_API_KEY` (optional) |
| Any A2A agent | HTTP/JSON-RPC | A2A URLs passed to `make_a2a_tools()` |

### 11.3 Cross-Framework Interoperability

The A2A protocol implementation enables calling agents from other frameworks:
- **CrewAI** agents (via A2A HTTP)
- **AutoGen** agents (via AutoGenProvider + A2A)
- **Google ADK** agents (via ADK provider)
- **Rasa** dialog systems (via RasaProvider)

---

## 12. MCP Tools Reference

All 19 built-in tools are defined in `mcp_tools.py` and available to every agent:

### Core Tools

| # | Tool | Description | External Dependency |
|---|---|---|---|
| 1 | `web_search` | DuckDuckGo instant answer search | None (no API key) |
| 2 | `read_file` | Read any file in the repo (path-traversal protected) | None |
| 3 | `write_output` | Write files to `/tmp/agency_outputs/` | None |
| 4 | `code_lint` | Python linting via ruff | `ruff` CLI |
| 5 | `memory_recall` | Query Titans memory for past missions | None |
| 6 | `get_datetime` | Current UTC date/time | None |

### Dubai / Real Estate Tools

| # | Tool | Description | External Dependency |
|---|---|---|---|
| 7 | `scrape_ae_leads` | Scrape Dubizzle for owner-direct RE leads | None (HTTP) |
| 8 | `query_trust_graph` | Entity trust score from Neo4j | `TRUST_GRAPH_URL` |
| 9 | `trigger_moltbot_mission` | Fire mission via Moltbot gateway | `MOLTBOT_GATEWAY_URL` |
| 10 | `qualify_lead_nowhere` | B2B lead scoring via NOWHERE.AI | `NOWHERE_AI_URL` |
| 11 | `analyze_dubai_market` | UAE market intelligence via NOWHERE.AI | `NOWHERE_AI_URL` |
| 12 | `create_campaign_nowhere` | Marketing campaign generation | `NOWHERE_AI_URL` |

### Automation & Data Tools

| # | Tool | Description | External Dependency |
|---|---|---|---|
| 13 | `n8n_trigger` | Fire n8n workflow via webhook | `N8N_BASE_URL` |
| 14 | `perplexica_search` | AI-powered search (replaces DuckDuckGo) | `PERPLEXICA_URL` |
| 15 | `sql_query` | Natural-language SQL via SQLBot | `SQLBOT_URL` |
| 16 | `api_lookup` | Discover public APIs for a topic | None (HTTP) |

### Security & Recon Tools

| # | Tool | Description | External Dependency |
|---|---|---|---|
| 17 | `airecon_scan` | OSINT/reconnaissance scan | `AIRECON_URL` or `airecon` CLI |
| 18 | `scan_secrets` | Secret scanning via TruffleHog | `trufflehog` CLI |
| 19 | `web_pentest` | Web app penetration testing | `SHANNON_URL` |

### Dynamic Tools (MCP Registry)

Additional tools are loaded at import time from:
1. `registry.json` in repo root
2. `MCP_REGISTRY_URL` remote endpoint
3. `MCP_SERVERS` environment variable

These are appended to `MCP_TOOLS` and available to all agents automatically.

---

## Adding a New Preset

1. Add the agent list to `PRESETS` in `agency.py` (~line 108)
2. Add the parallel execution plan to `PARALLEL_GROUPS` in `agency.py` (~line 204)
3. Core must always be the last agent in the preset list
4. Update `memory/AGENTS.md` "Available Presets" table if desired

## Adding a New Agent

1. Create `.md` file in the appropriate directory with YAML frontmatter:
   ```markdown
   ---
   name: Agent Name
   description: What this agent does.
   color: "#hexcolor"
   ---
   # Agent Name
   ## Core Mission
   ...
   ```
2. Register in `AGENT_REGISTRY` in `agency.py` if it will be used in presets
3. Add to relevant preset(s) in `PRESETS` and `PARALLEL_GROUPS`
4. Run tests: `python3 tests/agent_tests.py -v`

## Adding a New Provider

1. Create `providers/<name>_provider.py` implementing `BaseProvider`
2. Register in `get_provider()` factory in `providers/__init__.py`
3. Add CLI argument in `agency.py:440` and routing in `get_llm()`
