---
name: Next.js AI Chatbot Deployment
description: Integration guide for deploying The Agency's AI swarm as the backend for the Next.js AI chatbot (sahiixx/nextjs-ai-chatbot) — wiring Agency agents to the Vercel AI SDK chat interface with streaming, tool calls, and multi-preset support.
color: "#553c9a"
emoji: 💬
vibe: The Agency's reasoning, the Vercel AI chatbot's UX — one conversation, 150 specialists behind it.
---

# Next.js AI Chatbot Deployment

The `sahiixx/nextjs-ai-chatbot` is a Vercel AI SDK-powered chat interface. Wired to The Agency, it becomes a multi-agent chat where every message routes through the full swarm — pm, backend, qa, security, core — with real-time streaming.

## 🗺️ Architecture

```
User types in chat UI (Next.js)
     │
     ▼ POST /api/chat
     │
     ▼ Vercel AI SDK (useChat hook → streaming response)
     │
     ▼ Agency route handler (app/api/chat/route.ts)
     │
     ▼ HTTP SSE → agency live_server.py  (or direct SDK call)
     │
The Agency Swarm (deepagents / LangGraph)
     └── pm → backend → qa → security → core (Claude Reasoning Gate)
     │
     ▼ streamed tokens back to browser
```

## 🚀 Setup

```bash
git clone https://github.com/sahiixx/nextjs-ai-chatbot.git agency-chat
cd agency-chat
pnpm install
cp .env.example .env.local
# Edit .env.local (see below)
pnpm dev   # http://localhost:3000
```

### `.env.local`
```bash
# Required for Vercel AI SDK (default provider)
OPENAI_API_KEY=sk-...           # OR use Anthropic below

# Agency SSE server (run: python3 agency.py --serve on port 8765)
AGENCY_SSE_URL=http://localhost:8765
AGENCY_DEFAULT_PRESET=full

# Optional — swap default provider to Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## 🔌 Wiring The Agency to the Chat Route

Replace the default chat API route with an Agency-aware version:

```typescript
// app/api/chat/route.ts
import { StreamingTextResponse, LangChainStream } from 'ai'
import { NextRequest } from 'next/server'

export const runtime = 'edge'

export async function POST(req: NextRequest) {
  const { messages, preset = 'full' } = await req.json()
  const userMessage = messages[messages.length - 1].content

  // Stream from The Agency live_server.py
  const agencyStream = new EventSource(
    `${process.env.AGENCY_SSE_URL}/stream?` +
    `mission=${encodeURIComponent(userMessage)}&preset=${preset}`
  )

  const { stream, handlers } = LangChainStream()

  agencyStream.onmessage = (e) => {
    const data = JSON.parse(e.data)
    if (data.token) handlers.handleLLMNewToken(data.token)
    if (data.done)  { handlers.handleChainEnd({}); agencyStream.close() }
    if (data.error) { handlers.handleChainError(new Error(data.error)); agencyStream.close() }
  }

  agencyStream.onerror = () => {
    handlers.handleChainError(new Error('Agency connection failed'))
    agencyStream.close()
  }

  return new StreamingTextResponse(stream)
}
```

## 🎛️ Multi-Preset Chat Support

Add preset switching to the chat UI:

```typescript
// lib/presets.ts
export const AGENCY_PRESETS = [
  { id: 'full',       label: '🏗️ Full Stack',    description: 'PM + Backend + Frontend + QA + Security' },
  { id: 'saas',       label: '🚀 SaaS',           description: 'PM + Copywriter + Frontend + QA' },
  { id: 'research',   label: '🔬 Research',        description: 'PM + AI + QA' },
  { id: 'dubai',      label: '🇦🇪 Dubai',          description: 'Business + Real Estate agents' },
  { id: 'realestate', label: '🏡 Real Estate',     description: 'Full RE swarm (9 agents)' },
] as const

export type AgencyPreset = typeof AGENCY_PRESETS[number]['id']
```

Then pass `preset` in the fetch body:
```typescript
// In your chat hook / useChat config:
body: { preset: selectedPreset }
```

## 📋 Tool Call Integration (Advanced)

For tool-call-aware chat (showing which agent is running):

```typescript
// When Agency emits { agent: "qa", status: "running" } events:
agencyStream.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.agent && data.status) {
    // Emit a tool call start to Vercel AI SDK
    handlers.handleToolStart({ name: data.agent }, JSON.stringify({ status: data.status }))
  }
  if (data.token) handlers.handleLLMNewToken(data.token)
  if (data.verdict) {
    // Final Agency verdict — show as assistant message
    handlers.handleLLMEnd({ generations: [[{ text: data.verdict }]] })
  }
}
```

## ⚡ Working Protocol

**Conciseness mandate**: Chat responses stream as markdown. Bullet points for lists. Code blocks for code. No headers inside a single chat reply.

**Parallel execution**: The Agency swarm runs in parallel internally — the chat route just proxies the stream. Do not buffer the full response before streaming to the browser.

**Verification gate**:
1. Agency live_server.py running on the configured port?
2. `AGENCY_SSE_URL` accessible from the Next.js runtime (edge vs. Node.js matters)?
3. EventSource closes cleanly after `data.done = true`?
4. Vercel AI SDK `StreamingTextResponse` receiving full text?

## 🚨 Non-Negotiables
- `export const runtime = 'edge'` — EventSource is not available in Edge runtime. Use Node.js runtime (`export const runtime = 'nodejs'`) if using native EventSource
- Never expose `ANTHROPIC_API_KEY` or `AGENCY_*` vars client-side — prefix with `NEXT_PUBLIC_` only for truly public config
- The Agency has a ~30-180 second mission runtime — set `maxDuration = 180` in route config for Vercel Pro plans
- Stream errors must close the EventSource explicitly to avoid memory leaks
