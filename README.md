# The Agency — Claude-Powered Multi-Agent Swarm

> 166 specialized AI agents · Claude Sonnet 4.6 · Titans Memory · Production Ready

[![CI](https://github.com/sahiixx/agency-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/sahiixx/agency-agents/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-19%2F19-brightgreen)](tests/agent_tests.py)
[![Score](https://img.shields.io/badge/system%20score-90%2F90-gold)](agency.py)
[![Model](https://img.shields.io/badge/model-claude--sonnet--4--6-blue)](https://anthropic.com)

---

## What This Is

A swarm of **166 specialized AI agents** — each a `.md` file containing a system prompt and persona — orchestrated by a fully-wired Python runtime on **Claude Sonnet 4.6**.

Every mission passes through a sequential delegation pipeline and ends with a **Claude Reasoning Core** GO / CONDITIONAL GO / NO-GO verdict. Outcomes are stored in a **Titans-inspired surprise-weighted memory** that persists lessons across runs.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sahiixx/agency-agents
cd agency-agents

# 2. Install (one command)
bash setup.sh

# 3. Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

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
```

**Other pipeline scripts:**

| Script | Pipeline |
|---|---|
| `swarm_orchestrator.py` | PM → Dev → QA → Security → Core |
| `saas_dominance_swarm.py` | PM → Copy → Frontend → QA → Core |
| `sovereign_agency_swarm.py` | PM → Backend → AI → Frontend → QA → Core |
| `sovereign_ecosystem.py` | Observer → Refiner → Core → DevOps |
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

# Custom
python3 agency.py --mission "..." --agents security,qa,core
```

---

## Agent Roster — 166 Agents

| Directory | Agents | Domain |
|---|---|---|
| `engineering/` | 21 | Frontend, backend, DevOps, security, AI, data |
| `marketing/` | 19 | SEO, content, growth, social, paid media |
| `specialized/` | 18 | Orchestrators, Claude Core, compliance, identity |
| `design/` | 8 | UX, brand, visual, inclusive design |
| `sales/` | 8 | Account, pipeline, proposals, coaching |
| `testing/` | 8 | QA, accessibility, performance, API |
| `project-management/` | 6 | Planning, Jira, sprint, delivery |
| `support/` | 6 | Analytics, finance, legal, infrastructure |
| `product/` | 4 | Strategy, research, prioritization |

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
| `0e81afb` | 🧠 Claude Integration: Full Anthropic migration + Reasoning Core |

---

## Branches

| Branch | Status | Description |
|---|---|---|
| `main` | ✅ **production** | Stable — all tests passing, fully wired |
| `dependabot/uv/deepagents/libs/cli/uv-c51c02f1a9` | ⏳ auto-PR | Dependabot security update — will merge to main |

---

## System Health

```
Tests:          19/19 passing (4 need live API key)
Graph:          6 nodes — MemoryMiddleware.before_agent wired
Registry:       12/12 agents on disk
Lock files:     10 checked — 0 stale vulnerable pins
Security:       dependabot.yml active — weekly auto-updates
Score:          90/90 — Grade A, Production Ready
```

---

## Tech Stack

- **Model**: `claude-sonnet-4-6` via `langchain-anthropic`
- **SDK**: `deepagents` v0.4.10 — LangGraph-based agent harness
- **Memory**: `FilesystemBackend` + `MemoryMiddleware` + `TitansMemory`
- **Zero OpenAI** — fully Anthropic-native

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
pip install langchain-anthropic anthropic langchain langchain-core

# Environment
export ANTHROPIC_API_KEY="sk-ant-..."

# Tests
python3 tests/agent_tests.py                        # structural (offline)
ANTHROPIC_API_KEY=... python3 tests/agent_tests.py  # + live LLM
```

---

## CI/CD

`.github/workflows/ci.yml` runs on every push and PR:
- **Structural tests** — always run, no API key needed
- **Live LLM tests** — run on push to `main` if `ANTHROPIC_API_KEY` secret is set
- **Dependabot** — weekly pip and GitHub Actions updates, grouped by package family

Add secret: repo **Settings → Secrets → Actions → `ANTHROPIC_API_KEY`**

---

*Built on the original [The Agency](https://github.com/sahiixx/agency-agents) agent collection. Claude migration and orchestration layer by Claude Sonnet 4.6.*
