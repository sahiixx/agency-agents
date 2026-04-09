---
name: n8n Agency Bus
description: Integration guide for using n8n as the event/trigger bus for The Agency. Documents webhook triggers, preset mappings, and environment setup for automating agency missions from any n8n workflow.
color: "#ea4b71"
emoji: ⚡
vibe: n8n fires the trigger, The Agency does the thinking — one webhook, infinite automation.
---

# n8n Agency Bus

**n8n** is The Agency's event and trigger bus. Any n8n workflow can launch a full multi-agent
mission via a single webhook call — no code changes needed.

## Architecture

```
n8n Workflow Trigger
      │
      ▼ POST /webhook/agency
┌─────────────────────────────────────────────┐
│  Agency Webhook Receiver (n8n_trigger tool) │
│                                             │
│  workflow_tag → preset routing:             │
│    "email"   → --preset full                │
│    "slack"   → --preset moltbot             │
│    "crm"     → --preset dubai               │
│    "report"  → --preset research            │
│    "security"→ --preset security            │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
              Agency Mission Pipeline
              (Claude + selected agents)
                       │
                       ▼
              Results → n8n response
              (JSON with mission output)
```

## Quick Start

### 1. Start n8n

```bash
# Docker
docker run -it --rm -p 5678:5678 n8nio/n8n

# Or npm
npm install -g n8n && n8n start
```

### 2. Set environment variables

```env
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your-n8n-api-key          # from n8n Settings → API
N8N_WEBHOOK_PATH=/webhook/agency       # path of your webhook node
```

### 3. Create the Agency webhook workflow in n8n

1. **New workflow** → add a **Webhook** node
2. Set method: `POST`, path: `/webhook/agency`
3. Add an **HTTP Request** node pointing to `python3 agency.py` (or the Agency REST wrapper)
4. Return the response to Webhook

Or import one of the ready-made workflows below.

## Preset ↔ workflow_tag Mapping

| `workflow_tag` | Agency Preset | Description |
|----------------|---------------|-------------|
| `email`        | `full`        | General mission triggered by email |
| `slack`        | `moltbot`     | Slack message → mission → Slack reply |
| `crm`          | `dubai`       | CRM lead update → Dubai B2B analysis |
| `report`       | `research`    | Scheduled report generation |
| `security`     | `security`    | Security alert → audit swarm |
| `saas`         | `saas`        | SaaS pipeline (landing page, copy, QA) |
| `realestate`   | `realestate`  | Property listing → full RE pipeline |
| `intel`        | `intel`       | Competitive intelligence sweep |
| `trust`        | `trust`       | Entity trust check (UAE vetting) |
| `docs`         | `docs`        | Generate Mintlify docs from output |
| `evolve`       | *(special)*   | Trigger evolution_scheduler.py |

## Using the `n8n_trigger` MCP Tool

From within any Agency mission, agents can fire sub-workflows:

```python
# Called by an agent during a mission
n8n_trigger.invoke({
    "workflow_tag": "slack",
    "payload": json.dumps({"message": "Mission complete!", "channel": "#agents"})
})
```

## Top 20 Workflow Mappings (from ultimate-n8n-ai-workflows)

| Workflow | n8n Tag | Agency Preset |
|----------|---------|---------------|
| Weekly sales email digest | `email-weekly` | `research` |
| CRM lead enrichment | `crm-enrich` | `dubai` |
| Slack standup summary | `slack-standup` | `full` |
| GitHub PR review notification | `github-pr` | `security` |
| LinkedIn lead scrape → qualify | `linkedin-leads` | `realestate` |
| Google Analytics anomaly alert | `ga-anomaly` | `research` |
| Competitor price monitoring | `competitor-price` | `intel` |
| Invoice approval workflow | `invoice-approve` | `full` |
| Content calendar auto-fill | `content-calendar` | `saas` |
| Customer support triage | `support-triage` | `full` |
| Security incident escalation | `sec-incident` | `security` |
| New signup onboarding email | `signup-onboard` | `saas` |
| Product feedback analysis | `feedback-analyze` | `research` |
| KPI dashboard refresh | `kpi-refresh` | `research` |
| Contract renewal reminder | `contract-renew` | `trust` |
| Property listing alert | `property-alert` | `realestate` |
| Competitor blog monitor | `blog-monitor` | `intel` |
| Team mood/sentiment survey | `team-sentiment` | `full` |
| API error alert → debug | `api-error` | `security` |
| Agent evolution scheduler | `evolve` | *(special)* |

## Calling Agency from n8n HTTP Request Node

```
Method:  POST
URL:     http://your-agency-host/api/mission
Headers: Content-Type: application/json
Body:
{
  "mission":      "{{ $json.body.mission }}",
  "preset":       "{{ $json.body.workflow_tag }}",
  "provider":     "anthropic"
}
```

## Environment Reference

```env
N8N_BASE_URL=http://localhost:5678         # n8n instance
N8N_API_KEY=                               # n8n API key (optional)
N8N_WEBHOOK_PATH=/webhook/agency           # default webhook path
```

## Related

- `providers/n8n_provider.py` — n8n as a LLM provider (`--provider n8n`)
- `mcp_tools.py: n8n_trigger` — MCP tool for agents to fire n8n workflows
- `integrations/moltworker-gateway-bridge.md` — Moltbot (Telegram/Discord/Slack delivery)
- `integrations/nowhere-ai-platform-bridge.md` — NOWHERE.AI B2B platform integration
