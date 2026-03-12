# CLAUDE.md — Agency Memory File

This file is loaded automatically by Claude Code. It gives Claude full context about this repository so every session starts informed.

## What This Repo Is

**The Agency** — a swarm of 146 specialized AI agent personas, all running on Claude Sonnet 4.6 (Anthropic). Each agent is a `.md` file containing a system prompt / personality. The repo also includes Python orchestration scripts that chain agents into multi-step pipelines.

## The Most Important File

`specialized/specialized-claude-reasoning-core.md` — This is Claude operating as the agency's **Reasoning Core**: judgment layer, constitutional reviewer, and final gate on every swarm pipeline. Every pipeline ends with this agent giving a GO/NO-GO verdict.

## Architecture

```
mission_control.py          ← CLI: list/launch any agent, invoke reasoning core
swarm_orchestrator.py       ← Full pipeline: PM→Dev→QA→Security→Claude Core
saas_dominance_swarm.py     ← SaaS pipeline: PM→Copy→Frontend→QA→Claude Core
sovereign_agency_swarm.py   ← Full-stack: PM→Backend→AI→Frontend→QA→Claude Core
evolution_scheduler.py      ← Autonomous: Claude critiques & rewrites random agents
run_custom_agent.py         ← Single agent with custom tools
run_deep_research.py        ← Research agent with academic/market tools
tests/agent_tests.py        ← 19 tests: structural (offline) + live LLM
```

## Tech Stack

- **Model**: `claude-sonnet-4-6` via `langchain-anthropic`
- **SDK**: `deepagents` (in `deepagents/libs/deepagents`) — LangGraph-based agent harness
- **No OpenAI dependency** — fully migrated to Anthropic

## Setup

```bash
cd deepagents/libs/deepagents && pip install -e .
pip install langchain-anthropic anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
export PYTHONPATH=$PYTHONPATH:$(pwd)/deepagents/libs/deepagents
```

## Key Commands

```bash
python3 mission_control.py --list                          # all 146 agents
python3 mission_control.py --launch <agent.md> --query ""  # launch agent
python3 mission_control.py --reason --query ""             # reasoning core direct
python3 swarm_orchestrator.py --mission ""                 # full swarm
python3 evolution_scheduler.py                             # self-improvement cycle
python3 tests/agent_tests.py                               # run tests
```

## Agent Directories

| Directory | Domain |
|---|---|
| `engineering/` | Frontend, backend, DevOps, security, data, AI |
| `design/` | UI, UX, brand, visual |
| `marketing/` | SEO, social, content, growth |
| `sales/` | Account, pipeline, proposals, coaching |
| `specialized/` | Orchestrators, Claude Core, compliance |
| `testing/` | QA, accessibility, performance, API |
| `support/` | Analytics, finance, legal, infrastructure |
| `product/` | Strategy, research, prioritization |
| `project-management/` | Planning, Jira, sprint management |

## Rules When Working In This Repo

1. **Never remove the reasoning core** — `specialized/specialized-claude-reasoning-core.md` is the constitutional backbone
2. **All scripts must use `ChatAnthropic`** — no `ChatOpenAI` or OpenAI API keys
3. **Agent files must have frontmatter** — `---` with `name`, `description`, `emoji`, `color`
4. **Run tests before committing** — `python3 tests/agent_tests.py`
5. **Swarm pipelines end with Claude Core** — every pipeline's final step is the reasoning core verdict
6. **PYTHONPATH must include deepagents SDK** — `deepagents/libs/deepagents`

## CI/CD

- `.github/workflows/ci.yml` runs on every push/PR
- Structural tests (no API key): always run
- Live LLM tests: run on push to main if `ANTHROPIC_API_KEY` secret is set in repo settings

## What Claude Code Should Know

When asked to add a new agent: create a `.md` in the right directory with proper frontmatter, minimum 500 chars, with sections matching the existing style.

When asked to add a new swarm: follow the pattern in `swarm_orchestrator.py` — sequential agent calls, Claude Core as final step, save artifacts to `scaffold/`.

When asked to run the system: check `ANTHROPIC_API_KEY` is set, `PYTHONPATH` includes the SDK, then use `mission_control.py`.
