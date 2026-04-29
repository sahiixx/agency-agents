# CLAUDE.md — Agency Context

Auto-loaded by Claude Code. Full context so every session starts informed.

## What This Repo Is

**The Agency** — 152 specialized AI agent personas powered by local Ollama.
Each agent = a `.md` file with a system prompt. Python scripts orchestrate them.

## Entry Point

**`agency.py`** — use this for everything:
```bash
export OLLAMA_BASE_URL="http://localhost:11434"
python3 agency.py --list-agents
python3 agency.py --mission "Build a REST API for user auth"
python3 agency.py --mission "Design a SaaS page" --preset saas
python3 agency.py --mission "Research AI trends" --preset research
python3 agency.py --mission "Audit our security" --agents security,qa,core
python3 agency.py --mission "Qualify these Dubai leads" --preset dubai
```

## Architecture

```
agency.py                    <- unified orchestrator (START HERE)
memory/AGENTS.md             <- shared context, injected at startup
memory/titans_memory.py      <- Titans-inspired surprise-weighted memory
specialized/specialized-claude-reasoning-core.md  <- final GO/NO-GO gate
tests/agent_tests.py         <- 19 tests (15 offline + 4 live LLM)
setup.sh                     <- one-command install
```

## Tech Stack

- Model: `llama3.1` via `langchain-ollama` (local, private, no API key)
- SDK: `deepagents` v0.4.10 (in `deepagents/libs/deepagents`) — LangGraph-based
- Memory: `FilesystemBackend` + `MemoryMiddleware` + `TitansMemory`
- No cloud API dependencies — fully offline and private

## Rules

1. **Never remove the reasoning core** — it's the constitutional backbone
2. **All scripts use `ChatOllama`** — no `ChatAnthropic` or `ChatOpenAI`
3. **Agent files need frontmatter** — `---` block with `name`, `description`
4. **Run tests before committing** — `python3 tests/agent_tests.py`
5. **All pipelines end with Claude Core** — final step is always the reasoning core
6. **Error handling on all agent calls** — every `agent.invoke()` is in try/except
7. **Provider defaults to Ollama** — use `--provider ollama --ollama-model llama3.1`

## Key SDK Facts

- `create_deep_agent(memory=["path"])` requires `backend=FilesystemBackend(root_dir=REPO_ROOT)` — default `StateBackend` does NOT read local files
- `SubAgentMiddleware` appends `"Available subagent types: - name: description"` to orchestrator's system prompt automatically
- `task` tool routes to subagents by `name` field — use exact registry keys
- Context budget: ~13,500 tokens across all agent prompts (6.8% of 200k limit)

## Integration Points

- **sahiixx-bus** (port 9000): A2A gateway for multi-agent routing
- **friday-os**: Voice-first personal AI OS, consumes agency agents
- **sovereign-swarm-v2**: Multi-agent control plane with safety council
- **Ollama**: Local LLM serving on port 11434

## Adding a New Agent

Create `.md` in the right directory with frontmatter:
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

## Adding a New Swarm

Follow `swarm_orchestrator.py` pattern:
1. Sequential `run_agent()` calls with try/except
2. Claude Core as the last step — final verdict
3. Save artifacts to `scaffold/`
