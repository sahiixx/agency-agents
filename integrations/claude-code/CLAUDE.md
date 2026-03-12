# Claude Code Integration

This directory configures Claude Code to work with The Agency repo.

## Quick Start

When you open this repo in Claude Code, it automatically loads `CLAUDE.md` from the root. That file has everything you need.

## Suggested Claude Code Commands

```bash
# Explore the agency
python3 mission_control.py --list

# Ask the reasoning core a question
python3 mission_control.py --reason --query "What are the biggest risks in this codebase?"

# Launch any agent
python3 mission_control.py --launch engineering/engineering-security-engineer.md \
  --query "Audit mission_control.py for security issues"

# Run a full mission
python3 swarm_orchestrator.py --mission "Add a new REST API endpoint for agent health checks"
```

## Adding This Repo to Claude Code

```bash
# Install Claude Code if not already
npm install -g @anthropic-ai/claude-code

# Open the repo
cd agency-agents
claude

# Claude Code will auto-load CLAUDE.md and know the full context
```

## API Key Setup for Claude Code

Claude Code uses its own Anthropic API key. The agency scripts need a separate key:

```bash
export ANTHROPIC_API_KEY="your-key"
export PYTHONPATH=$PYTHONPATH:$(pwd)/deepagents/libs/deepagents
```

Add these to your `.env` or shell profile.
