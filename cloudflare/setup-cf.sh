#!/usr/bin/env bash
# setup-cf.sh — One command provisions and deploys The Agency on Cloudflare
# Usage: ANTHROPIC_API_KEY="sk-ant-..." bash setup-cf.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; GOLD='\033[0;33m'; NC='\033[0m'

echo -e "${GOLD}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  The Agency — Cloudflare Deployment                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 0. Check dependencies
command -v wrangler >/dev/null 2>&1 || { echo -e "${RED}Error: wrangler not found. Run: npm install -g wrangler${NC}"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo -e "${RED}Error: node not found.${NC}"; exit 1; }

# 1. Install npm packages
echo -e "${GOLD}[1/5] Installing packages...${NC}"
npm install

# 2. Create KV namespace
echo -e "${GOLD}[2/5] Creating KV namespace: agency-kv...${NC}"
KV_OUTPUT=$(wrangler kv namespace create agency-kv 2>&1)
KV_ID=$(echo "$KV_OUTPUT" | grep -oP '"id": "\K[^"]+' | head -1)
if [ -z "$KV_ID" ]; then
  echo -e "${RED}Could not parse KV ID. Output: $KV_OUTPUT${NC}"
  echo "Please manually set the KV ID in wrangler.jsonc"
  KV_ID="REPLACE_WITH_KV_ID"
fi
echo -e "${GREEN}  KV ID: $KV_ID${NC}"

# 3. Create D1 database
echo -e "${GOLD}[3/5] Creating D1 database: agency-traces...${NC}"
D1_OUTPUT=$(wrangler d1 create agency-traces 2>&1)
D1_ID=$(echo "$D1_OUTPUT" | grep -oP '"database_id": "\K[^"]+' | head -1)
if [ -z "$D1_ID" ]; then
  echo -e "${RED}Could not parse D1 ID. Output: $D1_OUTPUT${NC}"
  echo "Please manually set the D1 ID in wrangler.jsonc"
  D1_ID="REPLACE_WITH_D1_ID"
fi
echo -e "${GREEN}  D1 ID: $D1_ID${NC}"

# 4. Patch wrangler.jsonc with real IDs
sed -i "s/REPLACE_WITH_KV_ID/$KV_ID/g"  wrangler.jsonc
sed -i "s/REPLACE_WITH_D1_ID/$D1_ID/g" wrangler.jsonc
echo -e "${GREEN}  wrangler.jsonc updated with real IDs${NC}"

# 5. Apply D1 schema
echo -e "${GOLD}[4/5] Applying D1 schema...${NC}"
wrangler d1 execute agency-traces --file=schema.sql --remote

# 6. Set Anthropic API key secret
echo -e "${GOLD}[5/5] Setting ANTHROPIC_API_KEY secret...${NC}"
if [ -n "$ANTHROPIC_API_KEY" ]; then
  echo "$ANTHROPIC_API_KEY" | wrangler secret put ANTHROPIC_API_KEY
  echo -e "${GREEN}  Secret set.${NC}"
else
  echo -e "${RED}  ANTHROPIC_API_KEY not set in environment.${NC}"
  echo "  Run: echo 'sk-ant-...' | wrangler secret put ANTHROPIC_API_KEY"
fi

# 7. Deploy
echo -e "${GOLD}Deploying to Cloudflare Workers...${NC}"
wrangler deploy

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  ✅ Deployed! The Agency is live on Cloudflare Edge.     ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Open the URL printed above in your browser.             ║"
echo "║  The swarm visualization loads automatically.            ║"
echo "║                                                          ║"
echo "║  Architecture:                                           ║"
echo "║    MissionRoom   — Durable Object (SQLite + WebSockets)  ║"
echo "║    MissionWorkflow — Cloudflare Workflows (durable exec) ║"
echo "║    AGENCY_KV     — Titans memory ledger                  ║"
echo "║    AGENCY_DB     — D1 observability traces               ║"
echo "║    Claude 4.6    — 7 specialist agents + Core            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
