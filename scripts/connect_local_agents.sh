#!/bin/bash
# Wire your local Claude Code + Codex CLI to a running Lets backend so
# their MCP tool calls land in the topic stream visible at /app/.
#
# Reads the human name from $1 (defaults to your $USER) and:
#   1. ensures a session-bypass row for that human exists in the local DB
#   2. mints two agent-bound bearer tokens (claude:<device>, codex:<device>)
#   3. writes a .mcp.json into ~/.mcp.lets/<human>/ pointing at the backend
#   4. prints the instructions you need to paste into your CC/Codex config.
#
# This script is for local dev only. Production tokens come from the web
# Settings → Agent Tokens page after GitHub OAuth login.
set -euo pipefail

HUMAN="${1:-${USER:-jacky}}"
HOST="${LETS_HOST:-http://127.0.0.1:8000}"
DB_PATH="${LETS_DB_PATH:-$(pwd)/lets.db}"
DEVICE="${LETS_DEVICE:-$(hostname -s 2>/dev/null || echo local)}"

if [ ! -f "$DB_PATH" ]; then
  echo "no DB at $DB_PATH — run uvicorn first or set LETS_DB_PATH"
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

CC_LABEL="cc-$DEVICE"
CX_LABEL="codex-$DEVICE"

OUT=$(LETS_DB_PATH="$DB_PATH" .venv/bin/python <<PY
from app.db import init_db
from app.identity import ensure_human, ensure_agent_instance
from app.auth import issue_token
import json
init_db()
hid = ensure_human("$HUMAN")
cc_aid = ensure_agent_instance("claude", hid, "$CC_LABEL")
cx_aid = ensure_agent_instance("codex", hid, "$CX_LABEL")
cc_tok, _ = issue_token(human_id=hid, agent_instance_id=cc_aid, label="$CC_LABEL")
cx_tok, _ = issue_token(human_id=hid, agent_instance_id=cx_aid, label="$CX_LABEL")
print(json.dumps({"human_id": hid, "cc": cc_tok, "codex": cx_tok}))
PY
)

CC_TOK=$(echo "$OUT" | .venv/bin/python -c 'import sys,json;print(json.load(sys.stdin)["cc"])')
CX_TOK=$(echo "$OUT" | .venv/bin/python -c 'import sys,json;print(json.load(sys.stdin)["codex"])')

OUTDIR="$HOME/.mcp.lets/$HUMAN"
mkdir -p "$OUTDIR"

cat > "$OUTDIR/cc.mcp.json" <<JSON
{
  "mcpServers": {
    "lets": {
      "type": "http",
      "url": "$HOST/mcp/",
      "headers": { "Authorization": "Bearer $CC_TOK" }
    }
  }
}
JSON

cat > "$OUTDIR/codex.mcp.json" <<JSON
{
  "mcpServers": {
    "lets": {
      "type": "http",
      "url": "$HOST/mcp/",
      "headers": { "Authorization": "Bearer $CX_TOK" }
    }
  }
}
JSON

cat <<EOF
✓ Two agent-bound tokens issued for human "$HUMAN".

Files written:
  $OUTDIR/cc.mcp.json     — Claude Code (claude:$CC_LABEL)
  $OUTDIR/codex.mcp.json  — Codex CLI    (codex:$CX_LABEL)

To wire your local Claude Code:
  1. Open a NEW terminal, cd into the project directory you want CC to
     work in (or anywhere — Lets is global to that CC session).
  2. Copy the MCP config:
       mkdir -p .claude && cp $OUTDIR/cc.mcp.json .mcp.json
  3. Start CC normally:    claude
  4. In CC, ask:           "Use the lets MCP to call whoami"
     CC will report back as claude:$CC_LABEL — that means it's connected.
  5. Now ask CC to read or post to a topic:
       "Use lets to read_topic with topic_id=1, then post a chat saying hi"
     You'll see that chat appear in the Lets web UI at $HOST/app/

To wire your local Codex CLI:
  Identical, but copy codex.mcp.json instead, and start \`codex\` instead.

Refresh the Lets web UI sidebar after CC makes its first MCP call —
"在线 Agent" should show CC:$CC_LABEL with last-seen time.

EOF
