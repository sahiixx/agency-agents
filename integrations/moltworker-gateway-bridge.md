---
name: Moltworker Gateway Bridge
description: Integration guide for delivering The Agency's mission outputs across Telegram, Discord, Slack, and Web channels via the Moltbot Cloudflare Worker gateway (sahiixx/moltworker).
color: "#f6ad55"
emoji: ⚡
vibe: One mission, every channel — Telegram, Discord, Slack, or Web, all from the same Agency run.
---

# Moltworker Gateway Bridge

The **Moltworker Gateway** (`sahiixx/moltworker`) is a Cloudflare Worker that hosts a Moltbot AI gateway inside a Cloudflare Sandbox container. It bridges The Agency's Claude-powered swarm to end-users across every messaging channel simultaneously.

## 🗺️ Architecture

```
agency.py --mission "..." --preset full
     │
     ▼
The Agency Swarm (LangGraph / deepagents)
     │
     ▼
trigger_moltbot_mission() MCP tool
     │
     ▼ HTTP POST to Moltbot Admin API
┌──────────────────────────────────────────┐
│  Cloudflare Worker  (moltworker/src/)    │
│  - Proxies HTTP/WebSocket traffic        │
│  - Admin UI at /_admin/                  │
│  - API endpoints at /api/*               │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Cloudflare Sandbox Container            │
│  ┌──────────────────────────────────┐   │
│  │  Moltbot Gateway (port 18789)   │   │
│  │  - WebSocket RPC protocol        │   │
│  │  - ANTHROPIC_API_KEY injected    │   │
│  └──────────┬───────────────────────┘   │
└─────────────┼────────────────────────────┘
              │ delivers to
    ┌─────────┼──────────────┐
    ▼         ▼              ▼
Telegram  Discord/Slack   Web UI
```

## 🔧 Setup

### 1. Deploy moltworker to Cloudflare
```bash
git clone https://github.com/sahiixx/moltworker.git
cd moltworker
npm install
cp .dev.vars.example .dev.vars
# Edit .dev.vars:
# ANTHROPIC_API_KEY=sk-ant-...
# DEV_MODE=true (for local testing)
# TELEGRAM_BOT_TOKEN=...
# DISCORD_BOT_TOKEN=...
# SLACK_BOT_TOKEN=...
# SLACK_APP_TOKEN=...
npm run deploy
```

### 2. Configure Agency → Moltbot connection
```python
# In mcp_tools.py, trigger_moltbot_mission:
MOLTBOT_GATEWAY_URL = os.getenv("MOLTBOT_GATEWAY_URL", "http://localhost:8787")
MOLTBOT_GATEWAY_TOKEN = os.getenv("MOLTBOT_GATEWAY_TOKEN", "")
```

Add to your `.env`:
```bash
MOLTBOT_GATEWAY_URL=https://your-worker.your-subdomain.workers.dev
MOLTBOT_GATEWAY_TOKEN=your-token
```

### 3. Fire missions via Moltbot
```bash
# CLI: use mcp tool directly via agency
python3 agency.py --mission "Qualify our Dubai B2B leads" --preset dubai

# Programmatic: trigger_moltbot_mission MCP tool
# Results are delivered to all configured channels simultaneously
```

## 📡 Channel Configuration

### Telegram
```bash
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
# Users interact via @YourBot in Telegram
# Agency responses appear as bot messages
```

### Discord
```bash
DISCORD_BOT_TOKEN=your-discord-bot-token
# Agency runs can be triggered with /mission command
# Multi-agent pipeline visible as threaded messages
```

### Slack
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
# Agency missions fire from Slack slash commands
# Results post to configured channel
```

## 🔑 Moltbot Config Schema (Key Rules)
```jsonc
{
  "gateway": {
    "mode": "local",         // required for headless
    "token": "YOUR_TOKEN"    // from CLAWDBOT_GATEWAY_TOKEN env
  },
  "agents": {
    "defaults": {
      "model": { "primary": "claude-sonnet-4-6" }  // must be object, not string
    }
  },
  "channels": {
    "telegram": { "botToken": "YOUR_TELEGRAM_BOT_TOKEN" },
    "discord":  { "token": "YOUR_DISCORD_BOT_TOKEN" },
    "slack":    { "botToken": "YOUR_SLACK_BOT_TOKEN", "appToken": "YOUR_SLACK_APP_TOKEN" }
  }
}
```

## 🛠️ CLI Commands (via clawdbot CLI in container)
```bash
# Always include --url flag:
clawdbot devices list --json --url ws://localhost:18789

# Note: CLI outputs "Approved" (capital A) on success
# Use case-insensitive check: stdout.lower().includes('approved')
```

## ⚡ Working Protocol

**Conciseness mandate**: Channel-specific outputs stay ≤4 paragraphs. Telegram messages ≤1,000 chars. Slack blocks use sections, not prose.

**Parallel execution**: When delivering to multiple channels, trigger all simultaneously via the Moltbot gateway fan-out. Do not wait for Telegram to confirm before sending to Discord.

**Verification gate**: After triggering a mission via Moltbot:
1. HTTP 200 from `POST /api/gateway/trigger`?
2. `devices list` shows at least 1 active device?
3. Channel message appears within 30 seconds?
4. Error log clean? (`wrangler tail | grep ERROR`)

## 🚨 Non-Negotiables
- Never put `ANTHROPIC_API_KEY` in `wrangler.jsonc` — use Cloudflare secrets
- CLI is `clawdbot` (not `moltbot`) until upstream renames — use exact CLI name
- WebSocket proxying requires deployed Worker — local `wrangler dev` has WS limitations
- R2 bucket is mounted via s3fs — never `rm -rf /data/moltbot/*` (deletes backup data)
- `agents.defaults.model` must be `{ "primary": "model/name" }` object, not a string
