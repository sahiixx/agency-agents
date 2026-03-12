#!/usr/bin/env bash
# setup.sh — One-command setup for The Agency
# Usage: bash setup.sh
# After setup: export ANTHROPIC_API_KEY='sk-ant-...' && python3 agency.py --list-agents

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo ""
echo "============================================================"
echo "  The Agency — Setup"
echo "============================================================"

# Python version check
PY=$(python3 --version 2>&1)
echo "  Python: $PY"
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"; then
    echo "  ERROR: Python 3.11+ required"
    exit 1
fi

# Install deepagents SDK
echo ""
echo "  [1/3] Installing deepagents SDK..."
pip install -e deepagents/libs/deepagents --quiet --break-system-packages 2>&1 | tail -1

# Install Python dependencies
echo "  [2/3] Installing dependencies..."
pip install langchain-anthropic anthropic langchain langchain-core --quiet --break-system-packages 2>&1 | tail -1

# Verify imports
echo "  [3/3] Verifying imports..."
python3 -c "
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_anthropic import ChatAnthropic
print('  All imports OK')
"

echo ""
echo "============================================================"
echo "  Setup complete."
echo ""
echo "  Next: export ANTHROPIC_API_KEY='sk-ant-...'"
echo "  Then: python3 agency.py --list-agents"
echo "        python3 agency.py --mission 'Build a REST API for user auth'"
echo "============================================================"
echo ""
