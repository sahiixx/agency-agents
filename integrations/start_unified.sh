#!/usr/bin/env bash
# start_unified.sh — Start the AI Tools knowledge server and the agency together.
#
# Usage:
#   bash integrations/start_unified.sh --mission "Compare Cursor and Windsurf"
#   bash integrations/start_unified.sh --preset analysis --mission "Best tools for RAG?"
#
# The knowledge server (system-prompts-and-models-of-ai-tools) must be a sibling
# directory of agency-agents, or set SYSTEM_PROMPTS_REPO to its path.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENCY_ROOT="$(dirname "$SCRIPT_DIR")"
KNOWLEDGE_REPO="${SYSTEM_PROMPTS_REPO:-$(dirname "$AGENCY_ROOT")/system-prompts-and-models-of-ai-tools}"

if [ ! -d "$KNOWLEDGE_REPO" ]; then
    echo "ERROR: Knowledge repo not found at: $KNOWLEDGE_REPO"
    echo "  Clone it: git clone https://github.com/sahiixx/system-prompts-and-models-of-ai-tools \\" 
    echo "    $(dirname "$AGENCY_ROOT")/system-prompts-and-models-of-ai-tools"
    echo "  Or set: export SYSTEM_PROMPTS_REPO=/path/to/system-prompts-and-models-of-ai-tools"
    exit 1
fi

KB_PORT="${KNOWLEDGE_SERVER_PORT:-8200}"

echo "[unified] Starting AI Tools Knowledge Base server on port $KB_PORT..."
cd "$KNOWLEDGE_REPO"
python3 integrations/claude_query_server.py --port "$KB_PORT" &
KB_PID=$!

# Wait briefly for server to start
sleep 1

# Verify server is up
if ! curl -sf "http://localhost:${KB_PORT}/health" > /dev/null 2>&1; then
    echo "[unified] Warning: knowledge server may not be ready yet (continuing anyway)"
fi

export KNOWLEDGE_SERVER_URL="http://localhost:${KB_PORT}"
echo "[unified] Knowledge server PID=$KB_PID | KNOWLEDGE_SERVER_URL=$KNOWLEDGE_SERVER_URL"
echo "[unified] Starting agency..."
echo ""

cd "$AGENCY_ROOT"

# Run agency, kill knowledge server on exit
trap "echo ''; echo '[unified] Shutting down knowledge server (PID=$KB_PID)...'; kill $KB_PID 2>/dev/null" EXIT

python3 agency.py "$@"
