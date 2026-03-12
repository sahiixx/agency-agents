# Agency Memory — Shared Context

This file is loaded by all agents at startup via MemoryMiddleware.
Every agent in the swarm has this shared situational awareness.

## Who We Are
The Agency is a swarm of 130+ specialized AI agents built on Claude Sonnet 4.6.
Every agent has access to this shared memory and can spawn subagents via the `task` tool.

## Active Architecture
- Model: claude-sonnet-4-6 (Anthropic)
- Orchestration: deepagents SDK (LangGraph-based)
- Memory: This file, injected at startup by MemoryMiddleware (FilesystemBackend)
- Reasoning Gate: specialized/specialized-claude-reasoning-core.md
- Entry point: agency.py --mission "..." --preset [full|saas|research]

## How Memory Works (Titans-inspired design)
The agency memory architecture is informed by the Titans paper (Google, NeurIPS 2025).
Titans introduced a neural long-term memory module that works alongside attention:

- **Attention = short-term memory**: precise, but limited to current context window
- **Neural memory = long-term memory**: persists key facts across the full sequence
- **Surprise metric**: Titans prioritizes memorizing information that violates expectations
  (high-gradient inputs), mirroring how human memory works

Our AGENTS.md acts as the agency's persistent long-term memory — the facts that must
survive across every agent invocation, analogous to Titans' neural memory module.
Agents use their attention (context window) for the current task, and this file for
stable shared state.

## Collaboration Protocol
- Agents may spawn subagents for specialized subtasks via the `task` tool
- All mission outputs pass through Claude Reasoning Core before finalizing
- Handoffs must include full context — never assume the next agent knows what happened
- When in doubt: flag it, don't guess
- Parallel delegation preferred over sequential waterfall

## Quality Standards
- Every output must be production-ready or explicitly marked as draft
- Cite assumptions when making them
- If a task is outside your domain, say so and name the right agent

## Key Lessons (updated from live runs)
- FilesystemBackend required for local memory file access (not StateBackend)
- SubAgentMiddleware injects agent names+descriptions into orchestrator's system prompt
- task tool routes by agent name — use exact registry keys: pm, backend, frontend, qa, security, core
- Context budget: ~13,500 tokens across all agent prompts (6.8% of 200k limit)

## Mission Memory (Titans-weighted, most memorable first)
- [2026-03-12] NO-GO — Architect a real-time trading system (surprise=1.00, weight=1.00)
- [2026-03-12] GO — Generate marketing copy (surprise=0.33, weight=0.27)
- [2026-03-12] GO — Design a database schema for multi-tenancy (surprise=0.40, weight=0.25)
- [2026-03-12] CONDITIONAL GO — Build a SaaS landing page (surprise=1.00, weight=0.25)
- [2026-03-12] GO — Write a technical spec for user auth API (surprise=0.40, weight=0.16)
