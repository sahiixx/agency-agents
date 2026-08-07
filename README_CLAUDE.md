# The Agency — Cloud LLM Integration

A swarm of 150+ specialized AI agents running on **cloud models only** (no local
LLM runtime). The default backbone is **Anthropic Claude** (`claude-sonnet-5`;
override with `ANTHROPIC_MODEL`), with **OpenAI** (`OPENAI_MODEL`) and **Google
Gemini** (`GEMINI_MODEL`) available. Provider selection is automatic: the first
configured cloud API key wins (`auto` mode), or you can pin it with
`AGENCY_PROVIDER=anthropic|openai|adk`.

Each agent is a `.md` file. Python scripts chain them into multi-agent pipelines.

---

## Quick Start

```bash
# 1. Install everything (one command)
bash setup.sh

# Or manually:
pip install -e deepagents/libs/deepagents
pip install langchain-anthropic anthropic langchain langchain-core
pip install langchain-openai langchain-google-genai   # optional alternatives

# 2. Configure a cloud key (Freebuff: Keys tab; locally: export)
export ANTHROPIC_API_KEY="sk-ant-..."   # or OPENAI_API_KEY / GEMINI_API_KEY

# 3. Run
python3 agency.py --list-agents
python3 agency.py --mission "Build a REST API for user auth"
```

Local Ollama is **opt-in only** (`--provider ollama`) and is never used by default.

---

## Architecture

```
agency.py                    ← Unified entry point (use this)
├── MemoryMiddleware          ← Loads memory/AGENTS.md at startup
├── SubAgentMiddleware        ← Core spawns specialists via task tool
├── FilesystemBackend         ← Reads local agent files
└── TitansMemory              ← Surprise-weighted memory across runs

providers/
├── __init__.py               ← get_cloud_llm() cloud factory (auto provider pick)
├── anthropic_provider.py     ← Claude (default backbone)
├── openai_provider.py        ← OpenAI GPT
└── adk_provider.py           ← Google Gemini

memory/
├── AGENTS.md                 ← Shared context injected into every agent
└── titans_memory.py          ← Titans-inspired memory manager (NeurIPS 2025)

specialized/
└── specialized-claude-reasoning-core.md  ← Final GO/NO-GO gate

Other scripts (sequential pipelines, all cloud-powered):
  swarm_orchestrator.py       ← PM → Dev → QA → Security → Core
  saas_dominance_swarm.py     ← PM → Copy → Frontend → QA → Core
  sovereign_agency_swarm.py   ← PM → Backend → AI → Frontend → QA → Core
  sovereign_ecosystem.py      ← Observer → Refiner → Core → DevOps
  swarm_stress_test.py        ← Stress test: generates Dashboard.tsx
  evolution_scheduler.py      ← Self-improvement: critiques + rewrites agents
  mission_control.py          ← CLI: list/launch any single agent
  run_custom_agent.py         ← Single agent with custom tools
  run_deep_research.py        ← Research agent with web/academic tools
```

---

## Agent Presets

| Preset     | Agents                                     | Use for                  |
|------------|--------------------------------------------|--------------------------|
| `full`     | pm, backend, frontend, qa, security, core  | General engineering work |
| `saas`     | pm, copywriter, frontend, qa, core         | SaaS / marketing builds  |
| `research` | pm, ai, qa, core                           | Research & analysis      |

```bash
python3 agency.py --mission "Design a SaaS landing page" --preset saas
python3 agency.py --mission "Research AI memory" --preset research
python3 agency.py --mission "Audit security" --agents security,qa,core
python3 agency.py --mission "Build an API" --provider openai --openai-model gpt-5.1
```

---

## AGI Features

| Flag | Description |
|------|-------------|
| `--explore "topic"` | Autonomous exploration and knowledge discovery |
| `--fabricate name desc` | Runtime tool synthesis from natural language |
| `--evolve-daemon` | Continuous agent evolution every 60 min |
| `--ecosystem` | Scan sahiixx GitHub repos for integration |
| `--score-all` | Score and rank all 350+ agent prompts |
| `--preset agi` | Full AGI pipeline: explore + build + verify |

---

## How Memory Works

Based on [Titans (Google, NeurIPS 2025)](https://arxiv.org/abs/2501.00663):

- **Attention** = short-term memory: precise, limited to context window
- **AGENTS.md** = long-term memory: persists across all runs
- **Surprise metric**: unexpected verdicts (NO-GO, new patterns) decay slower
- **Forgetting**: routine outcomes decay and are pruned automatically

After each mission, `TitansMemory` records the verdict and writes the most
memorable outcomes back into `AGENTS.md` — agents learn across runs.

---

## Agent Directories

| Directory            | Agents                                      |
|----------------------|---------------------------------------------|
| `engineering/`       | Frontend, backend, DevOps, security, AI     |
| `design/`            | UX, brand, visual, systems                  |
| `marketing/`         | SEO, content, growth, social                |
| `sales/`             | Account, pipeline, proposals                |
| `specialized/`       | Orchestrators, Claude Core, compliance      |
| `testing/`           | QA, accessibility, performance              |
| `support/`           | Analytics, finance, legal                   |
| `product/`           | Strategy, research, prioritization          |
| `project-management/`| Planning, sprint, delivery                  |

---

## Tests

```bash
python3 tests/agent_tests.py          # 19 structural tests (offline)
python3 tests/agent_tests.py          # + 4 live LLM tests (if a cloud API key is set)
```
