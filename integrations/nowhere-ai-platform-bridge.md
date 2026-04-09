---
name: NOWHERE.AI Platform Bridge
description: Integration guide and MCP tool reference for the NOWHERE.AI platform (sahiixx/Fixfizx) — a production FastAPI + React + MongoDB platform for Dubai/UAE digital services, with 5 AI agents, multi-tenancy, Stripe, Twilio, and SendGrid.
color: "#d53f8c"
emoji: 🌐
vibe: The Agency's business agents powered by a live UAE production platform — AED payments, SMS, voice AI, and bilingual content out of the box.
---

# NOWHERE.AI Platform Bridge

**NOWHERE.AI** (`sahiixx/Fixfizx`) is a production-grade, AI-powered digital services platform for the Dubai/UAE market. It exposes REST APIs for the same 5 agent functions that The Agency runs as `.md` files — connecting The Agency's AI reasoning to a live platform with MongoDB persistence, Stripe AED payments, Twilio SMS, and SendGrid email.

## 🗺️ Architecture

```
The Agency (agency.py)
  biz-sales | biz-mkt | biz-content | biz-analytics | biz-ops
       │
       ▼ MCP tools: qualify_lead_nowhere / dubai_market_analysis / create_campaign_nowhere
       │
       ▼ HTTP → NOWHERE.AI Platform API (FastAPI, port 8001)
       │
       ├── /api/agents/sales/*       → MongoDB leads collection
       ├── /api/agents/marketing/*   → Campaign management
       ├── /api/agents/content/*     → Content generation (GPT-4o / Claude)
       ├── /api/ai/advanced/*        → Dubai market analytics
       ├── /api/integrations/*       → Stripe, Twilio, SendGrid
       └── /api/security/*           → JWT auth, RBAC
       │
       ▼ React Frontend (port 3000)
  Dashboard → Analytics → AI Solver → Chatbot → Services → Pricing
```

## 🚀 Platform Setup

```bash
git clone https://github.com/sahiixx/Fixfizx.git nowhere-ai
cd nowhere-ai

# Backend
cd backend
pip install -r requirements.txt --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
cp .env.example .env
# Edit .env with your API keys (see below)
python database_indexes.py
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend
cd ../frontend
yarn install && yarn start
```

### Key Environment Variables
```bash
MONGO_URL=mongodb://localhost:27017
DATABASE_NAME=nowhereai
JWT_SECRET=your-strong-secret-key

# AI Models (all optional — falls back gracefully)
EMERGENT_LLM_KEY=your-emergent-key      # Universal AI model access
OPENAI_API_KEY=sk-...                   # GPT-4o, DALL-E, Whisper
ANTHROPIC_API_KEY=sk-ant-...            # Claude 3.5 Sonnet 2025

# Integrations (all optional)
STRIPE_SECRET_KEY=sk_test_xxx           # AED payments
TWILIO_ACCOUNT_SID=xxx                  # SMS OTP
TWILIO_AUTH_TOKEN=xxx
SENDGRID_API_KEY=xxx                    # Transactional email

# Feature flags
FEATURE_AI_ADVANCED=true
FEATURE_VOICE_AI=true
FEATURE_VISION_AI=true
```

Set in Agency's `.env`:
```bash
NOWHERE_AI_URL=http://localhost:8001
NOWHERE_AI_JWT=<JWT from POST /api/security/auth/login>
```

## 📡 Key API Endpoints

### AI Agents
| Endpoint | Method | MCP Tool | Description |
|----------|--------|----------|-------------|
| `/api/agents/sales/qualify-lead` | POST | `qualify_lead_nowhere` | Score and qualify a B2B lead |
| `/api/agents/marketing/create-campaign` | POST | `create_campaign_nowhere` | Generate a multi-channel campaign |
| `/api/agents/content/generate` | POST | `generate_content_nowhere` | AI content (EN + AR) |
| `/api/agents/operations/automate-workflow` | POST | — | Automate an ops workflow |
| `/api/agents/status` | GET | — | All 5 agents health check |

### Dubai Market Intelligence
| Endpoint | Method | MCP Tool | Description |
|----------|--------|----------|-------------|
| `/api/ai/advanced/dubai-market-analysis` | POST | `analyze_dubai_market` | UAE B2B market intelligence |
| `/api/ai/advanced/enhanced-chat` | POST | — | Bilingual AI chat (EN/AR) |
| `/api/ai/advanced/models` | GET | — | Available AI models list |

### Enterprise
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/security/auth/login` | POST | JWT login (RBAC) |
| `/api/security/users/create` | POST | Create RBAC user |
| `/api/white-label/create-tenant` | POST | Multi-tenant provisioning |
| `/api/performance/summary` | GET | Platform performance metrics |
| `/api/integrations/payments/create-session` | POST | Stripe AED checkout |
| `/api/integrations/sms/send-otp` | POST | Twilio OTP |
| `/api/integrations/voice-ai/session` | POST | Voice AI (WebRTC) session |
| `/api/integrations/vision-ai/analyze` | POST | GPT-4o Vision analysis |

## 🔌 How The Agency's biz-* Agents Use The Platform

### Sales Agent + qualify_lead_nowhere
```python
# The biz-sales agent calls this after its own scoring
lead_result = await qualify_lead_nowhere({
    "company": "Acme FZCO",
    "contact": "Mohammed Al Rashid",
    "email": "m.rashid@acmefzco.ae",
    "budget_aed": 180000,
    "service_interest": "AI automation",
    "source": "LinkedIn"
})
# Returns: { score: 87, tier: "A", recommendation: "Immediate follow-up", next_action: "..." }
```

### Marketing Agent + create_campaign_nowhere
```python
campaign = await create_campaign_nowhere({
    "target_industry": "Real Estate",
    "target_geography": "Dubai",
    "budget_aed": 45000,
    "duration_days": 90,
    "channels": ["LinkedIn", "Google", "Meta"],
    "language": "bilingual"
})
# Returns: campaign brief, ad copy variants (EN + AR), budget allocation, KPI targets
```

### Analytics Agent + analyze_dubai_market
```python
intel = await analyze_dubai_market({
    "sector": "B2B SaaS",
    "query": "AI automation demand trends Q1 2026",
    "include_competitors": True
})
# Returns: market size, growth rate, top competitors, opportunity segments, AED revenue projections
```

## 🏗️ Project Structure Reference
```
Fixfizx/
├── backend/
│   ├── agents/
│   │   ├── agent_orchestrator.py    # Inter-agent communication
│   │   ├── sales_agent.py           # Lead qualification API
│   │   ├── marketing_agent.py       # Campaign management API
│   │   ├── content_agent.py         # EN + AR content generation
│   │   ├── analytics_agent.py       # KPIs and forecasting
│   │   └── operations_agent.py      # Workflow automation
│   ├── core/
│   │   ├── security_manager.py      # JWT + RBAC
│   │   ├── performance_optimizer.py # Caching, indexes
│   │   └── white_label_manager.py   # Multi-tenancy
│   ├── integrations/
│   │   ├── stripe_integration.py    # AED payments
│   │   ├── twilio_integration.py    # SMS OTP
│   │   └── sendgrid_integration.py  # Email
│   └── server.py                    # FastAPI app entry
└── frontend/                        # React 18 + Tailwind + Radix UI
```

## ⚡ Working Protocol

**Conciseness mandate**: API payloads as JSON snippets. Response fields in tables. No prose descriptions of what an endpoint does — show the request/response.

**Parallel execution**: When the `biz-*` preset runs, all 5 agent API calls can be made in parallel — they hit independent endpoints. Lead qualification, campaign creation, and market analysis do not share state.

**Verification gate**: Before any platform API call:
1. Platform healthy? `GET /api/health` → `{ "status": "healthy" }`
2. JWT valid? Tokens expire after 24h — re-auth if needed
3. MongoDB connected? Health endpoint reports `"database": "connected"`
4. Agent operational? `GET /api/agents/status` shows all 5 agents `"active"`

## 🚨 Non-Negotiables
- JWT tokens expire in 24h — cache the token, refresh before calling APIs
- Arabic content requires `"language": "ar"` or `"bilingual"` in the request payload
- Stripe in test mode: use `sk_test_*` keys — never commit production keys
- `white_label_manager.py` has known async issues (see `IMPLEMENTATION_PLAN.md`) — avoid `create_tenant` in production until patched
- Database indexes MUST be run before first use: `python database_indexes.py`
