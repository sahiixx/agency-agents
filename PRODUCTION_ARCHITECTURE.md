# Production Architecture (canonical)

This repository is the **primary execution platform** for SAHIIXX production agents.

Full contracts and revenue path: **[sahiixx-production-hardening](https://github.com/sahiixx/sahiixx-production-hardening)**.

## Production path

```text
Cloudflare ingress
  → FirstCall API (idempotency + auth)
  → sahiixx-bus (durable events)
  → agency-agents + agentic-harness (bounded workflows)
  → Human approval / CRM
  → Revenue ledger (deals + commission)
  → Metrics / ROI dashboard
```

## Non-negotiable rules

1. **One platform** — this repo + agentic-harness is the only production orchestrator.
2. **One event contract** — [event-envelope.json](https://github.com/sahiixx/sahiixx-production-hardening/blob/main/contracts/event-envelope.json).
3. **One memory policy** — verified CRM facts cannot be overwritten by model hypotheses.
4. **One revenue owner** — FirstCall owns lead → deal → commission state.
5. **Adapters only** — friday-os, hermes, openclaw, n8n never own business state.
6. **Human gates** — outreach and irreversible revenue mutations require approval.
7. **Proof over vanity** — cohort conversion and cost, not raw lead counts.

## Runnable revenue service

See `service/` in the hardening pack for a durable lead → commission API with cohort ROI metrics (`GET /v1/metrics`).

## Stubs to port

- `stubs/python/event_envelope.py`
- `stubs/python/model_router.py`
- `stubs/python/lead_ingestion.py`
