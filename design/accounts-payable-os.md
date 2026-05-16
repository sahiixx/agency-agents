# Accounts Payable Agent OS (APOS)

> Autonomous payment runtime for the Agency. Zero duplicate payments. 100% audit coverage. Sub-2-minute execution.

---

## 1. Architecture Overview

APOS is a modular, event-driven operating system that runs the Accounts Payable Agent. It abstracts payment rails, enforces financial guardrails, and guarantees idempotency across all disbursements.

```
┌──────────────────────────────────────────────┐
│               Agency Bus (MQ)                 │
└──────────────┬───────────────────────────────┘
               │ events / tool calls
┌──────────────▼───────────────────────────────┐
│              APOS Kernel                      │
│  ┌─────────┐ ┌─────────┐ ┌───────────────┐  │
│  │ Idempotency│ │Policy   │ │   Auditor    │  │
│  │  Engine   │ │Engine   │ │   Ledger     │  │
│  └─────────┘ └─────────┘ └───────────────┘  │
└──────┬──────────────┬──────────────┬────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────┐
│   Vendor    │ │  Payment   │ │ Scheduler  │
│  Registry   │ │   Rails    │ │  (Cron)    │
└─────────────┘ └────────────┘ └────────────┘
```

---

## 2. Kernel Modules

### 2.1 Idempotency Engine
- **Fingerprint**: `hash(vendor_id + invoice_ref + amount + currency)`
- **Store**: SQLite `payments` table with unique constraint on fingerprint.
- **Behavior**:
  - Reject duplicate within 72h window with reference to original `payment_id`.
  - Allow re-attempt after 72h only if prior status = `failed` and human flag is cleared.

### 2.2 Policy Engine
- **Authorization Tiers**:
  - `TIER_1`: ≤ $500 — autonomous.
  - `TIER_2`: $500–$5,000 — require dual-agent sign-off (e.g., Project Manager + AP Agent).
  - `TIER_3`: > $5,000 — human approval required.
- **Velocity Limits**: Max $20,000 / 24h autonomous; hard stop then escalate.
- **Vendor Check**: Must exist in `vendor_registry` with `approved = true`.

### 2.3 Auditor Ledger
- **Immutable log**: Append-only JSONL (`data/audit.jsonl` or append-only DB).
- **Fields**:
  - `event_type`: `payment_initiated | payment_sent | payment_confirmed | payment_failed | escalated`
  - `timestamp`, `payment_id`, `invoice_ref`, `amount`, `currency`, `rail`, `status`, `agent_requester`, `memo`
- **Retention**: 7 years (compliance). Cold archive to S3/R2 after 1 year.

---

## 3. Subsystems

### 3.1 Vendor Registry
```sql
CREATE TABLE vendor_registry (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT,
  approved BOOLEAN DEFAULT false,
  preferred_rail TEXT CHECK(preferred_rail IN ('ach','wire','crypto_btc','crypto_eth','usdc','usdt','stripe')),
  address_ach TEXT,
  address_crypto TEXT,
  stripe_account_id TEXT,
  po_required BOOLEAN DEFAULT false,
  metadata JSON
);
```
- Onboarding: Agents submit vendor; human approves via dashboard or CLI.
- Preferred rail auto-selected at runtime; fallback chain defined per vendor.

### 3.2 Payment Rails Adapter
Unified interface: `rail.send(payload) -> {tx_id, status, fee, settled_at}`

| Adapter | Idempotency Key | Timeout | Retry Strategy |
|---------|-----------------|---------|----------------|
| ACH | `invoice_ref` + `vendor_id` | 3 days | No auto-retry; escalate on return |
| Wire | `invoice_ref` + `timestamp_day` | Same day | 1 retry after 4h |
| USDC / USDT | `invoice_ref` | 60s | 3 retries, 10s backoff |
| BTC / ETH | `invoice_ref` | 10m | 2 retries, 30s backoff |
| Stripe | `invoice_ref` | 30s | 3 retries, exponential |

All adapters emit `payment_sent` and `payment_confirmed` / `payment_failed` events.

### 3.3 Scheduler (Cron Engine)
- Reads `recurring_bills` table where `next_due <= NOW()`.
- Runs every hour.
- For each bill:
  1. Check idempotency.
  2. Check policy tier.
  3. Execute via preferred rail.
  4. Update `next_due` = `+ interval` on confirmation.
  5. On failure, pause recurrence and escalate.

### 3.4 Escalation Router
- **Channels**: Slack / Discord webhook, email, dashboard alert.
- **Payload**:
  ```json
  {
    "severity": "hold | review | urgent",
    "reason": "Exceeded spend limit | Rail failure | Vendor unapproved | Amount mismatch",
    "payment_id": null,
    "invoice_ref": "INV-2024-0142",
    "amount": 1200.00,
    "requested_by": "contracts-agent"
  }
  ```
- SLA: Escalation event logged and notified within 60s of detection.

---

## 4. Data Model

```sql
-- Core Payments
CREATE TABLE payments (
  id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
  fingerprint TEXT UNIQUE NOT NULL,
  invoice_ref TEXT NOT NULL,
  vendor_id TEXT NOT NULL REFERENCES vendor_registry(id),
  amount_cents INTEGER NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  rail TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','sent','confirmed','failed','cancelled')),
  tx_id TEXT,
  fee_cents INTEGER,
  requested_by TEXT,
  memo TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Recurring Bills
CREATE TABLE recurring_bills (
  id TEXT PRIMARY KEY,
  vendor_id TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,
  currency TEXT,
  description TEXT,
  interval_days INTEGER NOT NULL,
  next_due DATE NOT NULL,
  active BOOLEAN DEFAULT true
);

-- Escalations
CREATE TABLE escalations (
  id TEXT PRIMARY KEY,
  payment_id TEXT REFERENCES payments(id),
  reason TEXT NOT NULL,
  severity TEXT NOT NULL,
  resolved BOOLEAN DEFAULT false,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. API & Tool Interfaces

### 5.1 Incoming Tool Calls (from other agents)
```typescript
// Initiate a payment
POST /ap/pay
Body: {
  invoice_ref: string,
  vendor_id: string,
  amount: number,
  currency: string,
  memo?: string,
  requested_by: string
}

// Check status
GET /ap/status/:invoice_ref

// Register vendor (pending approval)
POST /ap/vendors
Body: { name, email, preferred_rail, address_ach?, address_crypto?, stripe_account_id? }

// Generate AP report
GET /ap/report?from=YYYY-MM-DD&to=YYYY-MM-DD
```

### 5.2 Outbound Events (to Agency Bus)
```json
{ "topic": "ap.payment.confirmed", "payload": { "payment_id", "invoice_ref", "amount", "vendor_id" } }
{ "topic": "ap.payment.failed", "payload": { "payment_id", "reason", "escalation_id" } }
{ "topic": "ap.escalated", "payload": { "escalation_id", "severity", "reason" } }
```

---

## 6. Security & Compliance

- **Key Storage**: Crypto private keys and API secrets in 1Password / HashiCorp Vault; never in repo.
- **Address Verification**: For any new crypto address, require out-of-band verification (signed message or human confirmation).
- **Spend Limits**: Enforced in code + at rail API level where possible (e.g., Stripe restrictions).
- **Audit**: Ledger hash-chained monthly (`hash(prev_month_hash + current_month_jsonl_hash)`).
- **Compliance**: SOC 2 Type II ready — all access logged, least privilege enforced, quarterly access review.

---

## 7. Failure Modes

| Scenario | Response |
|----------|----------|
| Duplicate request | Return existing `payment_id`; no new tx |
| Rail timeout | Mark `pending`; retry per adapter policy |
| Rail final failure | Escalate; do NOT auto-switch rails without human sign-off |
| Amount ≠ PO | Hold; escalate with diff |
| Unauthorized vendor | Reject; log; notify Compliance Agent |
| Velocity breach | Hard stop; queue remaining payments; escalate |

---

## 8. Deployment Model

- **Runtime**: Python 3.11+ async daemon (`aposd`) or serverless (Cloudflare Workers / AWS Lambda).
- **State**: SQLite locally; Postgres in production.
- **Bus**: Redis Pub/Sub or NATS for Agency events.
- **Dashboard**: Read-only view into `payments` + `escalations` via existing Agency dashboard.

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Duplicate payments | 0 |
| Autonomous execution (≤$500) | < 2 min |
| Audit coverage | 100% |
| Escalation latency | < 60 s |
| Rail failure recovery | 95% within 1 retry |

---

*APOS — built so money never moves without a paper trail, and never moves twice.*
