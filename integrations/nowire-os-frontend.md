---
name: Nowire OS Frontend
description: Integration guide for deploying and managing the Nowire OS frontend (sahiixx/v0-nowire-os-blueprint) — a Next.js + shadcn/ui CRM/OS interface built with v0.app, deployed on Vercel, automatically synced via GitHub.
color: "#319795"
emoji: 🖥️
vibe: The Agency thinks, Nowire OS shows — a living UI that auto-deploys every time v0.app generates a new component.
---

# Nowire OS Frontend Integration

**Nowire OS** (`sahiixx/v0-nowire-os-blueprint`) is the frontend OS/CRM interface that surfaces The Agency's outputs — real estate dashboards, Dubai B2B pipelines, AI mission results — as a polished Next.js application. It auto-syncs with v0.app and deploys to Vercel on every push.

## 🗺️ Architecture

```
v0.app (Vercel AI UI generator)
     │ auto-push on deploy
     ▼
GitHub: sahiixx/v0-nowire-os-blueprint
     │
     ▼ Vercel CI/CD
Live URL: vercel.com/xxxx-2b199fdc/v0-nowire-os-blueprint
     │
     ▲ data / SSE streams
The Agency (agency.py missions)
```

## 🛠️ Stack
- **Framework**: Next.js (App Router)
- **UI**: shadcn/ui + Tailwind CSS (via `components.json`)
- **Package manager**: pnpm (`pnpm-lock.yaml`)
- **Deployment**: Vercel (auto-deploy on push to main)
- **Builder**: v0.app — `https://v0.app/chat/huciXBxz9xF`

## 🚀 Local Development
```bash
git clone https://github.com/sahiixx/v0-nowire-os-blueprint.git nowire-os
cd nowire-os
pnpm install
pnpm dev       # http://localhost:3000
```

## 🔌 Connecting The Agency to Nowire OS

### Option A: SSE Stream (Real-time mission output)
Add an SSE endpoint in `app/api/agency/stream/route.ts`:
```typescript
import { NextRequest } from 'next/server'

export async function GET(req: NextRequest) {
  const mission = req.nextUrl.searchParams.get('mission')
  const preset  = req.nextUrl.searchParams.get('preset') ?? 'full'

  const stream = new TransformStream()
  const writer = stream.writable.getWriter()
  const encoder = new TextEncoder()

  // Proxy to agency live_server.py
  const agencySSE = new EventSource(
    `${process.env.AGENCY_SSE_URL}/stream?mission=${encodeURIComponent(mission!)}&preset=${preset}`
  )

  agencySSE.onmessage = async (e) => {
    await writer.write(encoder.encode(`data: ${e.data}\n\n`))
  }

  agencySSE.onerror = async () => {
    await writer.close()
    agencySSE.close()
  }

  return new Response(stream.readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}
```

Add to `.env.local`:
```bash
AGENCY_SSE_URL=http://localhost:8765  # or your deployed agency URL
```

### Option B: REST (batch mission output)
```typescript
// app/api/agency/run/route.ts
export async function POST(req: Request) {
  const { mission, preset } = await req.json()
  const res = await fetch(`${process.env.AGENCY_API_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mission, preset }),
  })
  return Response.json(await res.json())
}
```

### Option C: Nowire OS UI triggers Agency missions
Add a mission launcher component using the existing shadcn Button + Input:
```tsx
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export function AgencyMissionLauncher({ preset = 'full' }) {
  const [mission, setMission] = useState('')
  const [output, setOutput] = useState<string[]>([])

  const run = async () => {
    const src = new EventSource(`/api/agency/stream?mission=${encodeURIComponent(mission)}&preset=${preset}`)
    src.onmessage = (e) => setOutput(p => [...p, e.data])
    src.onerror = () => src.close()
  }

  return (
    <div className="space-y-2">
      <Input value={mission} onChange={e => setMission(e.target.value)} placeholder="Enter mission..." />
      <Button onClick={run}>Run Agency</Button>
      <pre className="text-sm whitespace-pre-wrap">{output.join('\n')}</pre>
    </div>
  )
}
```

## 📁 Key Directories
```
v0-nowire-os-blueprint/
├── app/              # Next.js App Router pages + API routes
├── components/       # shadcn/ui components + custom UI
├── hooks/            # React custom hooks
├── lib/              # Utility functions
├── styles/           # Global CSS
├── scripts/          # Build/deploy scripts
├── public/           # Static assets
└── components.json   # shadcn/ui config (path aliases, style, etc.)
```

## 🚢 Deployment
```bash
# Push to main = auto-deploys via Vercel
git push origin main

# Manual deploy via Vercel CLI
pnpm build
vercel --prod

# Environment variables in Vercel dashboard:
# AGENCY_SSE_URL = https://your-agency-server.com
# NOWHERE_AI_URL = https://your-nowhere-ai.com
# NEXT_PUBLIC_APP_NAME = Nowire OS
```

## ⚡ Working Protocol

**Conciseness mandate**: UI components are self-contained. No prop drilling beyond 2 levels — use context or URL state. Server actions for mutations, not client-side fetch.

**Parallel execution**: Use `Promise.all` when loading multiple dashboard widgets. Nowire OS pages are pre-built with `generateStaticParams` where possible.

**Verification gate**: Before pushing changes to the v0-nowire-os-blueprint repo:
1. `pnpm build` passes with no TypeScript errors
2. `pnpm lint` clean
3. All `shadcn/ui` component imports resolve (check `components.json` aliases)
4. Vercel preview deployment URL accessible?

## 🚨 Non-Negotiables
- This repo syncs FROM v0.app — manual edits may be overwritten on the next v0 deploy. Add custom integrations in separate files (`app/api/agency/`, `components/agency-*`)
- pnpm only — do not run `npm install` or `yarn install` in this repo
- `components.json` configures path aliases — always use `@/components/ui/button`, not relative imports
- Vercel env vars must be set in the Vercel dashboard, not committed to `.env.local`
