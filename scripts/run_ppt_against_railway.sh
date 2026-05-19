#!/bin/bash
# Run the PPT scenario against Railway. Requires 2 agent tokens minted
# via the Web UI Settings → Agent Tokens page after GitHub OAuth login.
#
# Usage:
#   LETS_CC_TOKEN=lets_xxx LETS_CODEX_TOKEN=lets_yyy ./scripts/run_ppt_against_railway.sh
#
# The CC token doubles as the human Bearer for the briefing post; actor_id
# is derived from whoami so all three messages attribute to the same human.

set -eu

HOST="${LETS_HOST:-https://lets.up.railway.app}"

if [ -z "${LETS_CC_TOKEN:-}" ] || [ -z "${LETS_CODEX_TOKEN:-}" ]; then
  echo "Set LETS_CC_TOKEN and LETS_CODEX_TOKEN (mint via Settings → Agent Tokens)"
  exit 1
fi

echo "Probing $HOST ..."
CODE=$(curl -s --noproxy '*' -o /dev/null -w "%{http_code}" "$HOST/api/context")
if [ "$CODE" != "200" ]; then
  echo "Backend not ready: $HOST/api/context returned $CODE"
  exit 2
fi
echo "Backend healthy."

cd "$(dirname "$0")/.."
exec env \
  LETS_HOST="$HOST" \
  LETS_HUMAN_TOKEN="$LETS_CC_TOKEN" \
  LETS_CC_TOKEN="$LETS_CC_TOKEN" \
  LETS_CODEX_TOKEN="$LETS_CODEX_TOKEN" \
  .venv/bin/python scripts/ppt_scenario.py
