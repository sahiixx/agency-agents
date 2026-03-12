# 🧠 Claude Integration — Reasoning Core & Constitutional AI

This fork of The Agency has been upgraded to run entirely on **Claude (Anthropic)** as the AI backbone.

---

## What Changed

| File | Change |
|---|---|
| `mission_control.py` | Rewritten to use `claude-sonnet-4-6` via `langchain-anthropic`. Adds `--reason` and `--info` commands. |
| `swarm_orchestrator.py` | Rewritten with Claude-native pipeline: PM → Dev → QA → Security → **Reasoning Core verdict** |
| `specialized/specialized-claude-reasoning-core.md` | New agent: Claude operating as the swarm's judgment layer |

---

## Setup

```bash
# Install deepagents SDK
cd deepagents/libs/deepagents && pip install -e . && cd ../../..

# Install Anthropic support
pip install langchain-anthropic anthropic

# Set your key
export ANTHROPIC_API_KEY="your_key_here"
export PYTHONPATH=$PYTHONPATH:$(pwd)/deepagents/libs/deepagents
```

---

## Usage

```bash
# List all 146 agents
python3 mission_control.py --list

# Filter by domain
python3 mission_control.py --list --filter engineering

# Launch any agent
python3 mission_control.py --launch engineering/engineering-frontend-developer.md \
  --query "Build a login form in React"

# Invoke Claude Reasoning Core directly (judgment, ethics, synthesis)
python3 mission_control.py --reason \
  --query "Review this copy for ethical issues: ..."

# Show agent details
python3 mission_control.py --info specialized/specialized-claude-reasoning-core.md

# Run the full swarm pipeline
python3 swarm_orchestrator.py --mission "Build a high-performance analytics dashboard"

# Fast mode (skip security scan)
python3 swarm_orchestrator.py --mission "Build a landing page" --mode fast
```

---

## Swarm Pipeline

```
User Mission
    │
    ▼
[PM Agent]          → Creates execution plan
    │
    ▼
[Frontend Dev]      → Implements the UI
    │
    ▼
[QA Agent]          → Audits implementation
    │
    ▼
[Security Engineer] → Threat review (full mode)
    │
    ▼
[🧠 Claude Core]    → Constitutional review → GO / NO-GO verdict
```

Every agent in the swarm is powered by `claude-sonnet-4-6`.
The Reasoning Core is the final gate before any output is considered complete.

---

*The Agency — now running on Claude.*
