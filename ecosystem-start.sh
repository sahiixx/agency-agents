#!/usr/bin/env bash
# ecosystem-start.sh — Start all SAHIIXX ecosystem services
# Usage: bash ecosystem-start.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "=========================================="
echo "  SAHIIXX Ecosystem — Start"
echo "=========================================="
echo ""

# 1. Check Ollama
echo "[1/5] Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ✓ Ollama running (port 11434)"
else
    echo "  ⚠ Ollama not running. Starting..."
    ollama serve &
    sleep 3
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✓ Ollama started"
    else
        echo "  ✗ Could not start Ollama"
    fi
fi

# 2. Start sahiixx-bus (orchestration bus)
echo ""
echo "[2/5] Starting sahiixx-bus..."
if [ -d "$HOME/sahiixx-bus" ]; then
    cd "$HOME/sahiixx-bus"
    if [ -f ".test-venv/bin/uvicorn" ]; then
        nohup .test-venv/bin/uvicorn sahiixx_bus.server:app --host 0.0.0.0 --port 8090 > /tmp/sahiixx-bus.log 2>&1 &
        BUS_PID=$!
        echo "  ✓ sahiixx-bus started (PID: $BUS_PID, port 8090)"
    else
        echo "  ✗ .test-venv not found — run setup first"
    fi
else
    echo "  ✗ sahiixx-bus not found at ~/sahiixx-bus"
fi
cd "$REPO_DIR"

# 3. Start sovereign-swarm servers
echo ""
echo "[3/5] Starting sovereign-swarm services..."
if [ -d "$HOME/sovereign-swarm-v2" ]; then
    cd "$HOME/sovereign-swarm-v2"
    nohup python3 -c "
import asyncio
from sovereign_swarm.protocols.a2a import A2ACardServer
from sovereign_swarm.protocols.webhook_server import WebhookServer

async def start():
    a2a = A2ACardServer(port=18797)
    webhook = WebhookServer(port=18793)
    await asyncio.gather(a2a.start(), webhook.start())

asyncio.run(start())
" > /tmp/sovereign-swarm.log 2>&1 &
    SWARM_PID=$!
    echo "  ✓ sovereign-swarm servers started (PID: $SWARM_PID, ports 18797/18793)"
else
    echo "  ✗ sovereign-swarm-v2 not found"
fi
cd "$REPO_DIR"

# 4. Check agency-agents
echo ""
echo "[4/5] Agency-agents..."
if [ -f "$REPO_DIR/agency.py" ]; then
    echo "  ✓ agency-agents ready ($(ls -d $REPO_DIR/specialized/*.md 2>/dev/null | wc -l) specialist agents)"
else
    echo "  ✗ agency.py not found"
fi

# 5. Summary
echo ""
echo "[5/5] Ecosystem status summary"
echo "=========================================="
echo ""
# Quick health checks
for name in "Ollama:11434" "sahiixx-bus:8090"; do
    port="${name##*:}"
    service="${name%:*}"
    if curl -s "http://localhost:$port/" > /dev/null 2>&1; then
        echo "  ✓ $service (port $port)"
    else
        echo "  ○ $service (port $port)"
    fi
done

echo ""
echo "=========================================="
echo "  Ecosystem started."
echo ""
echo "  Logs:"
echo "    sahiixx-bus:       tail -f /tmp/sahiixx-bus.log"
echo "    sovereign-swarm:   tail -f /tmp/sovereign-swarm.log"
echo ""
echo "  Commands:"
echo "    python3 ecosystem.py --status"
echo "    python3 ecosystem.py --bridge"
echo "    python3 ecosystem.py --mission '...'"
echo "=========================================="
