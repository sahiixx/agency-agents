#!/usr/bin/env bash
# push.sh — One command to push all Claude changes to GitHub
# Usage: ./push.sh
# Or with token: GITHUB_TOKEN=ghp_xxx ./push.sh

set -e

REPO="https://github.com/sahiixx/agency-agents"

echo ""
echo "🧠 The Agency — Push to GitHub"
echo "────────────────────────────────"

# Check if token provided
if [ -n "$GITHUB_TOKEN" ]; then
  REMOTE="https://${GITHUB_TOKEN}@github.com/sahiixx/agency-agents.git"
  git remote set-url origin "$REMOTE"
  echo "✅ Using provided GITHUB_TOKEN"
else
  echo "ℹ️  No GITHUB_TOKEN set — using default credentials"
  echo "   To push with a token: GITHUB_TOKEN=ghp_xxx ./push.sh"
fi

echo ""
echo "📊 Status:"
git log --oneline -3
echo ""

echo "🚀 Pushing to main..."
git push origin main

echo ""
echo "✅ Done! View at: $REPO"
