# Agency Memory — Shared Context

This file is loaded by all agents at startup via MemoryMiddleware.
Every agent in the swarm has this shared situational awareness.

## Who We Are
The Agency is a swarm of 150+ specialized AI agents. Runs on a multi-model stack:
**local Ollama by default** (`qwen3:8b`, overridable via `OLLAMA_MODEL`), with
Claude (`ANTHROPIC_MODEL`), OpenAI (`OPENAI_MODEL`), and Gemini (`GEMINI_MODEL`)
available per provider. Every agent has access to this shared memory and can spawn
subagents via the `task` tool.

## Active Architecture
- Model: qwen3:8b via Ollama (default; see env vars above)
- Orchestration: deepagents SDK (LangGraph-based)
- Memory: This file, injected at startup by MemoryMiddleware (FilesystemBackend)
- Reasoning Gate: specialized/specialized-claude-reasoning-core.md
- Entry point: agency.py --mission "..." --preset [full|saas|research|aiops]
- Eval gate: specialized/specialized-agent-evaluator.md
- Safety gate: specialized/specialized-ai-safety-reviewer.md

## 2026 Knowledge Refresh (what changed, and why it matters)
- **Local model lineup (Ollama)**: qwen3 (8b/14b/32b — strong general default),
  qwen3-coder:30b (agentic coding), llama3.3:70b (flagship chat), deepseek-r1
  (reasoning/math), gemma3 (multimodal), mistral-small (multilingual). Prefer the
  smallest model that clears the eval bar.
- **Claude (Anthropic)**: sonnet class remains the workhorse for agentic coding;
  model IDs are pinned via `ANTHROPIC_MODEL` — do not hardcode new model names
  from memory; verify against the API first.
- **OpenAI**: gpt-5.x class; pin via `OPENAI_MODEL`.
- **MCP (Model Context Protocol)** is the standard agent tool interface — this
  repo's `mcp_tools.py` + `mcp_registry.py` already follow it. Assume any new
  integration is MCP-first.
- **A2A (agent-to-agent)** is the standard for cross-agent interoperability —
  `a2a_protocol.py` implements v0.3. Prefer A2A for external agent calls.
- **Eval-driven development**: every model/prompt/tool change should pass the
  eval harness (`--preset aiops` runs evaluate → observe → safety-review).
- **Agent memory**: Titans-style surprise-weighted memory remains the pattern;
  keep ledger writes small and high-signal.
- **Local-first / privacy**: fine-tuning, memory, and inference should stay local
  (`--provider ollama`) unless the user opts into a hosted provider.

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
- task tool routes by agent name — use exact registry keys: pm, backend, frontend, qa,
  security, core, spy, docs, cloudflare, trust, wpscan, linux, learn, re-*, biz-*,
  llm-finetuner, agent-observability, agent-evaluator, safety-reviewer
- Context budget: ~13,500 tokens across all agent prompts (6.8% of 200k limit)
- Model defaults come from env: OLLAMA_MODEL, ANTHROPIC_MODEL, OPENAI_MODEL, GEMINI_MODEL

## Repo Ecosystem (sahiixx — 42 confirmed public repos)

Every agent should be aware of the full repo ecosystem available as integration targets.

### 🟢 Active Integrations (wired to Agency)
| Repo | Integration | Key Agents / Tools |
|------|------------|-------------------|
| `agency-agents` | Core — this repo | All agents |
| `Fixfiz` / `Fixfizx` | NOWHERE.AI platform | biz-sales, biz-mkt, biz-content, biz-analytics, biz-ops + qualify_lead_nowhere / analyze_dubai_market / create_campaign_nowhere |
| `moltworker` | Cloudflare Gateway (Telegram/Discord/Slack/Web) | trigger_moltbot_mission MCP tool; preset: moltbot |
| `SHADOW` | Coral Protocol swarm (Voice→Code→Review→Log) | integrations/shadow-swarm-bridge.md; preset includes coral agents |
| `Coral-BlackboxAI-Agent` | Coral Protocol bridge | integrations/coral-protocol-bridge.md |
| `Trust-graph-` | Neo4j trust graph | trust agent + query_trust_graph MCP tool; preset: trust |
| `ae-lead-scraper---` | UAE property lead scraper | scrape_ae_leads MCP tool |
| `v0-nowire-os-blueprint` | Nowire OS Next.js frontend | integrations/nowire-os-frontend.md; frontend agent |
| `nextjs-ai-chatbot` / `nextjs-ai-chatbotg` | Next.js AI chatbot | integrations/nextjs-chatbot-deployment.md |
| `system-prompts-and-models-of-ai-tools` | 31+ tool system prompts + 26 patterns | spy agent; preset: intel |
| `Y` | Prompt pattern library (26 universal patterns) | specialized/specialized-prompt-architect.md |
| `agents-for-multi-agent-systems` | Multi-agent test scenarios | Dubai/research presets |

### 🟡 Deployment Templates (available to devops/cloudflare agent)
| Repo | Stack | Use |
|------|-------|-----|
| `react-router-starter-template` | React Router v7 + Cloudflare Pages | Full-stack TypeScript apps |
| `containers-template` | Cloudflare Containers + TypeScript | Long-running Docker workloads |
| `examples-hello-world` | HTML + Cloudflare Worker | Minimal Worker scaffolds |
| `examples-with-fresh` | Fresh (Deno) + Cloudflare | Deno edge apps |
| `moltbot-sandbox` / `moltbot-sandboxt` / `moltbot-sandboxuu` | TypeScript + Moltbot | Test environments for moltworker |

### 🟡 Documentation Targets (available to docs agent)
| Repo | Platform | Use |
|------|----------|-----|
| `mintlify-docs` | Mintlify (MDX) | Primary docs site |
| `docs` | Mintlify (MDX) | API reference / secondary docs |

### 🔵 Product UIs (available to frontend/ux agent)
| Repo | Stack | Use |
|------|-------|-----|
| `Sahiix` | TypeScript | Personal portfolio site |
| `app` | HTML | Simple web app |
| `X` | JavaScript | JS project |
| `open` | JavaScript | Open-source project |

### ⚪ Empty / Placeholder (no actionable content)
`H`, `Bag`, `Big`, `Gg`, `Bvvh`, `Hh`, `musical-octo-journey`, `MINS`, `7`, `Gsje`,
`Hjjj`, `studious-sniffle`, `sahiix-agent-s-` (empty), `TelegramCrmBot` (empty),
`racx-reflection-pipeline` (stub), `Xxxxxxx`

## System Prompts Intelligence (system-prompts-and-models-of-ai-tools)
31+ AI tool prompts catalogued: Cursor, Claude Code, Devin AI, Windsurf, Manus, Kiro,
Amp, GitHub Copilot, Lovable, Replit, Junie, Augment Code, Same.dev, Trae, Warp.dev,
Leap.new, Orchids.app, Perplexity, Cluely, NotionAI, CodeBuddy, VSCode Agent, Qoder,
Poke, Traycer AI, Xcode, Z.ai Code, dia, Comet Assistant, v0 Prompts.
26 universal patterns extracted. See `specialized/specialized-ai-tools-reverse-engineer.md`.

## Available Presets
| Preset | Agents | Use |
|--------|--------|-----|
| `full` | pm, backend, frontend, qa, security, core | Full-stack product build |
| `saas` | pm, copywriter, frontend, qa, core | SaaS landing + MVP |
| `research` | pm, ai, qa, core | Research, analysis |
| `realestate` | 9 RE specialists + core | Dubai RE full pipeline |
| `dubai` | 5 biz + 3 RE + core | UAE B2B + market intel |
| `security` | security, wpscan, linux, devops, core | Security audit |
| `intel` | spy, prompt-arch, core | Competitive AI intelligence |
| `docs` | pm, docs, core | Documentation generation |
| `moltbot` | pm, backend, frontend, core | Deliver via Moltbot channels |
| `trust` | trust, re-comply, core | UAE entity trust vetting |
| `lead-machine` | re-capture, re-qual, re-geo, re-sched, re-report, core | RE lead E2E chain |
| `voice` | pm, backend, core | Voice-driven missions |
| `n8n` | pm, devops, backend, core | n8n workflow automation |
| `sovereign` | pm + 6 eng + 3 biz + 2 RE + core | Full ecosystem |
| `explore` | explorer, ai, core | Autonomous exploration |
| `agi` | explorer + build + verify + core | AGI pipeline |
| `aiops` | llm-finetuner, agent-observability, agent-evaluator, safety-reviewer, ai, core | Agent platform ops: tune, observe, eval, gate |
| `all` | every registered agent + core | Maximum coverage |

## Mission Memory (Titans-weighted, most memorable first)
- [2026-04-30] GO — Say hello (surprise=0.80, weight=0.80)
- [2026-04-30] GO — Say hello (surprise=1.00, weight=0.63)
- [2026-04-29] FAILED — Test ecosystem connectivity (surprise=0.70, weight=0.35)
- [2026-04-28] FAILED — report status (surprise=0.70, weight=0.25)
- [2026-04-27] FAILED —  (surprise=0.70, weight=0.18)
