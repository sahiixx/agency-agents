#!/usr/bin/env bash
# Install Weave as a git merge driver for this repo

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
WEAVE_PY="$REPO_ROOT/agency-agents/weave/weave.py"

if [ ! -f "$WEAVE_PY" ]; then
    echo "weave.py not found at $WEAVE_PY"
    exit 1
fi

python3 "$WEAVE_PY" --base /dev/null --ours /dev/null --theirs /dev/null --merged /dev/null --install
echo "✅ Weave merge driver installed. AI agent conflicts will now be auto-resolved."
