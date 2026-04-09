# Agency Dashboard

Next.js 15 dashboard for **The Agency** — the unified UI for all 152 agents.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home — links to all sections |
| `/dashboard` | Live stats, mission launcher, agent graph |
| `/chat` | Chat interface connected to Agency A2A server (port 8100) |
| `/agents` | Browse all 152 agents and presets *(coming soon)* |
| `/memory` | Titans memory ledger *(coming soon)* |

## Setup

```bash
cd dashboard
npm install
npm run dev        # → http://localhost:3000
```

## Production build

```bash
npm run build
npm start
```

## Deploy to Cloudflare Pages

```bash
npx wrangler pages deploy .next --project-name agency-dashboard
```

Or follow `integrations/cloudflare-deployment-templates.md` for full Workers + Pages setup.

## Environment Variables

Create `.env.local`:

```env
# Agency A2A server (default: http://localhost:8100)
AGENCY_A2A_URL=http://localhost:8100
```

## Connect to Agency

Start the Agency A2A server:

```bash
python3 agency.py --serve --ui nextjs
```

Or launch the dashboard separately from the Python backend:

```bash
# Terminal 1 — Agency backend
python3 agency.py --serve

# Terminal 2 — Dashboard
cd dashboard && npm run dev
```

## Architecture

```
dashboard/              ← Next.js 15 app
  src/app/
    page.tsx            ← Home
    dashboard/page.tsx  ← Mission control
    chat/page.tsx       ← Chat UI → A2A JSON-RPC
  next.config.js        ← /api/agency/* proxied to Agency A2A (port 8100)
```

## Desktop Wrapper (openclaw)

To run as a desktop app:

1. Install [openclaw](https://github.com/sahiixx/openclaw) (Electron wrapper)
2. Set `AGENCY_DASHBOARD_URL=http://localhost:3000`
3. `npx openclaw --url http://localhost:3000`
