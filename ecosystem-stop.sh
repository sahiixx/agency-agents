#!/usr/bin/env bash
# ecosystem-stop.sh — Stop all SAHIIXX ecosystem services
# Usage: bash ecosystem-stop.sh

echo ""
echo "=========================================="
echo "  SAHIIXX Ecosystem — Stop"
echo "=========================================="
echo ""

# Kill by port
for port in 8090 18797 18793; do
    pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -n "$pid" ]; then
        kill "$pid" 2>/dev/null
        echo "  ✗ Stopped service on port $port (PID: $pid)"
    else
        echo "  ○ No service on port $port"
    fi
done

echo ""
echo "=========================================="
echo "  All services stopped."
echo "=========================================="
echo ""
