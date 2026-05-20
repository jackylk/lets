#!/bin/bash
# Run two Lets gateway processes side-by-side: one bound to your local
# Claude Code (claude --print) and one bound to local Codex (codex exec).
#
# Reads tokens from ~/.mcp.lets/<human>/{cc,codex}.mcp.json (produced by
# scripts/connect_local_agents.sh). Logs each gateway to
# /tmp/lets-gateway-*.log. Press Ctrl-C to stop both cleanly.
set -euo pipefail

HUMAN="${1:-${USER:-jacky}}"
TOKDIR="$HOME/.mcp.lets/$HUMAN"

if [ ! -f "$TOKDIR/cc.mcp.json" ] || [ ! -f "$TOKDIR/codex.mcp.json" ]; then
  echo "missing $TOKDIR/cc.mcp.json or codex.mcp.json"
  echo "run: ./scripts/connect_local_agents.sh $HUMAN  first"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

read_tok() {
  .venv/bin/python -c "import json,sys; print(json.load(open('$1'))['mcpServers']['lets']['headers']['Authorization'].split()[1])"
}
CC_TOK=$(read_tok "$TOKDIR/cc.mcp.json")
CX_TOK=$(read_tok "$TOKDIR/codex.mcp.json")

LETS_TOKEN="$CC_TOK" PYTHONUNBUFFERED=1 \
  .venv/bin/python -m app.gateway > /tmp/lets-gateway-cc.log 2>&1 &
CC_PID=$!

LETS_TOKEN="$CX_TOK" PYTHONUNBUFFERED=1 \
  .venv/bin/python -m app.gateway > /tmp/lets-gateway-codex.log 2>&1 &
CX_PID=$!

cleanup() {
  echo
  echo "stopping gateways…"
  kill "$CC_PID" "$CX_PID" 2>/dev/null || true
  wait "$CC_PID" "$CX_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "✓ CC gateway PID=$CC_PID  log=/tmp/lets-gateway-cc.log"
echo "✓ Codex gateway PID=$CX_PID  log=/tmp/lets-gateway-codex.log"
echo "(streaming both logs; Ctrl-C to stop)"
echo "---"
tail -F /tmp/lets-gateway-cc.log /tmp/lets-gateway-codex.log
