from __future__ import annotations

import base64
import json
import importlib
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.types import ASGIApp, Receive, Scope, Send

from . import mcp_server as mcp_server_module
from .auth import get_api_principal, set_mcp_principal, verify_token
from .db import connect, init_db

mcp_server_module = importlib.reload(mcp_server_module)

_mcp_http = mcp_server_module.get_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    async with mcp_server_module.mcp.session_manager.run():
        yield


app = FastAPI(title="Lets", lifespan=lifespan)


class BearerAuthMiddleware:
    """Strict ASGI middleware: rejects non-Bearer or invalid-token requests."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode().lower(): value.decode()
            for key, value in scope.get("headers", [])
        }
        authorization = headers.get("authorization", "")
        parts = authorization.split(" ", 1)
        principal = (
            verify_token(parts[1].strip())
            if len(parts) == 2 and parts[0].lower() == "bearer"
            else None
        )
        if principal is None:
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"detail":"missing or invalid token"}',
                }
            )
            return

        # Stash principal into a contextvar so downstream MCP tools can
        # read the calling agent without us having to thread it through
        # the FastMCP request handler. Reset to None on entry/exit so a
        # stale principal cannot leak across requests.
        set_mcp_principal(principal)
        try:
            await self.app(scope, receive, send)
        finally:
            set_mcp_principal(None)


app.mount("/mcp", BearerAuthMiddleware(_mcp_http))


class WorkItemCreate(BaseModel):
    type: Literal["idea", "task"]
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    created_by: str = "human"


class ClaimRequest(BaseModel):
    agent_name: str
    agent_type: str = "unknown"
    git_branch: str | None = None


WorkItemStatus = Literal["open", "claimed", "in_progress", "done", "rejected"]


class WorkItemStatusUpdate(BaseModel):
    status: WorkItemStatus
    agent_name: str | None = None
    agent_type: str = "unknown"
    message: str | None = None
    topic_id: int | None = None


class StatusCreate(BaseModel):
    agent_name: str
    agent_type: str = "unknown"
    work_item_id: int | None = None
    status: Literal["idle", "active", "blocked", "offline"]
    message: str
    topic_id: int | None = None


class FindingCreate(BaseModel):
    agent_name: str
    agent_type: str = "unknown"
    work_item_id: int | None = None
    title: str
    body: str
    topic_id: int | None = None


class HumanNoteCreate(BaseModel):
    work_item_id: int | None = None
    body: str


FeedbackType = Literal[
    "instruction",
    "opinion",
    "question",
    "correction",
    "priority_change",
    "review",
]


class FeedbackCreate(BaseModel):
    work_item_id: int | None = None
    feedback_type: FeedbackType
    body: str = Field(min_length=1)
    topic_id: int | None = None


ActorType = Literal["human", "agent", "system"]

MessageTypeStr = Literal[
    "chat",
    "status",
    "finding",
    "decision",
    "question",
    "handoff",
    "review",
    "artifact_revision",
    "spec_change",
    "nudge",
    "proactive_finding",
    "task_tree_proposal",
    "project_proposal",
    "goal_proposal",
    "system",
]


class MessageCreate(BaseModel):
    topic_id: int
    type: MessageTypeStr
    actor_type: ActorType
    actor_id: int | None = None
    body: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
    ref_event_id: int | None = None
    addressed_to: str | None = None


class EventCreate(BaseModel):
    event_type: str
    actor_type: ActorType
    actor_id: int | None = None
    target_type: str
    target_id: int | None = None
    project_id: int | None = None
    topic_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class TaskTreeAdoptInput(BaseModel):
    proposal_message_id: int


class GoalAdoptInput(BaseModel):
    goal_proposal_message_id: int | None = None
    artifact_id: int | None = None
    spec_text: str | None = None


class TaskItemCreate(BaseModel):
    task_tree_id: int
    title: str
    parent_item_id: int | None = None
    summary: str | None = None
    linked_message_id: int | None = None
    deliverable_artifact_id: int | None = None
    owner_human_id: int | None = None
    owner_agent_instance_id: int | None = None


class TaskItemPatch(BaseModel):
    status: str | None = None
    title: str | None = None
    summary: str | None = None
    linked_message_id: int | None = None
    deliverable_artifact_id: int | None = None


class ArtifactCreate(BaseModel):
    slug: str = Field(min_length=1)
    type: str = Field(min_length=1)
    backend: str = Field(default="git")
    title: str = Field(min_length=1)
    topic_id: int
    content_b64: str
    summary: str | None = None


class ArtifactUpdate(BaseModel):
    content_b64: str
    summary: str | None = None
    version_label: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    slug: str | None = None
    description: str | None = None
    repo_path: str | None = None


class ProjectPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    repo_path: str | None = None


class TopicCreate(BaseModel):
    slug: str = Field(min_length=1)
    title: str = Field(min_length=1)


def ensure_agent(name: str, agent_type: str) -> int:
    with connect() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ?", (name,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE agents
                SET agent_type = ?, last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (agent_type, row["id"]),
            )
            return int(row["id"])

        cursor = conn.execute(
            """
            INSERT INTO agents (name, agent_type, status)
            VALUES (?, ?, 'idle')
            """,
            (name, agent_type),
        )
        return int(cursor.lastrowid)


@app.get("/", response_model=None)
def home() -> RedirectResponse | FileResponse:
    """Route root to the Track F SPA when it's been built.

    If ``frontend/dist/index.html`` (or the dir indicated by the
    ``LETS_FRONTEND_DIST`` env override) exists, redirect to ``/app``.
    Otherwise fall back to the legacy v1 ``web/index.html`` debug panel
    so a rollback path remains for one release.
    """
    import pathlib as _pl

    dist_env = os.environ.get("LETS_FRONTEND_DIST")
    if dist_env:
        dist_root = _pl.Path(dist_env)
    else:
        dist_root = _pl.Path(__file__).parent.parent / "frontend" / "dist"

    if dist_root.is_dir() and (dist_root / "index.html").exists():
        return RedirectResponse(url="/app", status_code=307)
    return FileResponse("web/index.html")


@app.get("/mock")
def mock() -> FileResponse:
    return FileResponse("web/mock.html")


@app.get("/api/context")
def get_context() -> dict:
    return {
        "project": {
            "name": "Lets",
            "description": "Shared workboard for local coding agents.",
        },
        "auth": {
            "dev_login_enabled": os.environ.get("LETS_DEV_SESSIONS") == "1",
            "github_configured": bool(os.environ.get("GITHUB_CLIENT_ID")),
        },
    }


def _public_base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    return f"{proto}://{host}".rstrip("/")


@app.get("/install/gateway.py")
def install_gateway_py() -> FileResponse:
    """Serve the standalone gateway source for one-line installer clients."""
    from pathlib import Path

    gateway_path = Path(__file__).with_name("gateway.py")
    return FileResponse(
        gateway_path,
        media_type="text/x-python; charset=utf-8",
        filename="gateway.py",
    )


@app.get("/install/gateway.sh")
def install_gateway_sh(request: Request) -> PlainTextResponse:
    """One-line installer for the local Lets gateway.

    Designed so a brand-new user can run the curl-bash one-liner and then
    immediately type ``lets login`` — no $PATH editing, no rc-file
    sourcing. The script:

    * Materializes ~/.lets/ with a private venv + gateway.py.
    * Generates ~/.lets/bin/lets that runs the gateway via the venv.
    * Tries to symlink /usr/local/bin/lets (works on most macs that have
      Homebrew, which makes that dir user-owned) for zero PATH friction.
    * Falls back to appending ``export PATH="$HOME/.lets/bin:$PATH"`` to
      ~/.zshrc / ~/.bashrc / fish config so the next shell session has it.

    The script is idempotent — running it twice doesn't break anything.
    """
    base_url = _public_base_url(request)
    script = f"""#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${{LETS_HOST:-{base_url}}}"
LETS_HOME="${{LETS_HOME:-$HOME/.lets}}"
PYTHON="${{PYTHON:-python3}}"

mkdir -p "$LETS_HOME" "$LETS_HOME/bin"

if ! "$PYTHON" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "Lets gateway requires Python 3.10+." >&2
  exit 1
fi

if [ ! -x "$LETS_HOME/venv/bin/python" ]; then
  "$PYTHON" -m venv "$LETS_HOME/venv"
fi

"$LETS_HOME/venv/bin/python" -m pip install --upgrade pip >/dev/null
"$LETS_HOME/venv/bin/python" -m pip install --upgrade httpx >/dev/null

curl -fsSL "$BASE_URL/install/gateway.py" -o "$LETS_HOME/gateway.py"
chmod 600 "$LETS_HOME/gateway.py"

# ---- write a `lets` shim that calls the venv'd gateway ----
cat > "$LETS_HOME/bin/lets" <<'SH'
#!/usr/bin/env bash
LETS_HOME="${{LETS_HOME:-$HOME/.lets}}"
export LETS_HOST="${{LETS_HOST:-__BASE_URL__}}"
exec "$LETS_HOME/venv/bin/python" "$LETS_HOME/gateway.py" "$@"
SH
perl -0pi -e "s#__BASE_URL__#$BASE_URL#g" "$LETS_HOME/bin/lets"
chmod +x "$LETS_HOME/bin/lets"

# ---- make `lets` reachable without manual PATH editing ----
LINK_INSTALLED=""
for prefix in /usr/local/bin /opt/homebrew/bin; do
  if [ -d "$prefix" ] && [ -w "$prefix" ]; then
    ln -sf "$LETS_HOME/bin/lets" "$prefix/lets"
    LINK_INSTALLED="$prefix/lets"
    break
  fi
done

# Fallback: append to shell rc files so future shells see ~/.lets/bin
RC_EDITED=""
if [ -z "$LINK_INSTALLED" ]; then
  EXPORT_LINE='export PATH="$HOME/.lets/bin:$PATH"  # lets'
  for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    if [ -f "$rc" ] && ! grep -Fq '$HOME/.lets/bin' "$rc"; then
      printf '\\n%s\\n' "$EXPORT_LINE" >> "$rc"
      RC_EDITED="${{RC_EDITED}}$rc "
    fi
  done
  # fish
  if [ -d "$HOME/.config/fish" ]; then
    FISH_RC="$HOME/.config/fish/config.fish"
    if ! grep -Fq '$HOME/.lets/bin' "$FISH_RC" 2>/dev/null; then
      printf '\\nset -gx PATH $HOME/.lets/bin $PATH  # lets\\n' >> "$FISH_RC"
      RC_EDITED="${{RC_EDITED}}$FISH_RC "
    fi
  fi
fi

cat <<MSG

✓ lets installed.

Files:
  $LETS_HOME/gateway.py
  $LETS_HOME/bin/lets
MSG

if [ -n "$LINK_INSTALLED" ]; then
  echo "  $LINK_INSTALLED  →  $LETS_HOME/bin/lets"
fi
if [ -n "$RC_EDITED" ]; then
  echo
  echo "Added \\$HOME/.lets/bin to your shell PATH in: $RC_EDITED"
  echo "(takes effect in new terminals)"
fi

# ---- Auto-login unless skipped, so the one-line install IS the onboarding ----
if [ "${{LETS_SKIP_LOGIN:-0}}" = "0" ]; then
  cat <<MSG

Logging this device in to $BASE_URL ...
(opens your default browser; if you're already logged in to Lets in
 that browser, this auto-confirms in a couple of seconds)

MSG
  "$LETS_HOME/bin/lets" login \\
    --host "$BASE_URL" \\
    --role "${{LETS_AGENT_ROLE:-claude}}" || \\
    {{ echo "lets login failed — try again with: lets login" >&2; exit 1; }}

  cat <<MSG

✓ Logged in. Token saved to $LETS_HOME/token

Next:
  lets gateway        # start the daemon now (this terminal)
  lets install        # OR: register a launchd job so it auto-starts on login
                      #     and survives reboot

MSG
else
  cat <<MSG

To finish onboarding:
  lets login          # device-flow OAuth via your browser
  lets gateway        # start the daemon
MSG
fi
"""
    return PlainTextResponse(script, media_type="text/x-shellscript; charset=utf-8")


@app.post("/api/work-items")
def create_work_item(payload: WorkItemCreate) -> dict:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO work_items (type, title, body, created_by)
            VALUES (?, ?, ?, ?)
            """,
            (payload.type, payload.title, payload.body, payload.created_by),
        )
        row = conn.execute("SELECT * FROM work_items WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


@app.get("/api/work-items")
def list_work_items(status: str | None = None) -> list[dict]:
    query = """
        SELECT wi.*, a.name AS claimed_by_agent_name
        FROM work_items wi
        LEFT JOIN agents a ON a.id = wi.claimed_by_agent_id
    """
    params: tuple[object, ...] = ()
    if status:
        query += " WHERE wi.status = ?"
        params = (status,)
    query += " ORDER BY wi.created_at DESC, wi.id DESC"
    with connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@app.delete("/api/work-items/{work_item_id}")
def delete_work_item(work_item_id: int) -> dict:
    with connect() as conn:
        item = conn.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="work item not found")
        conn.execute("DELETE FROM findings WHERE work_item_id = ?", (work_item_id,))
        conn.execute("DELETE FROM status_updates WHERE work_item_id = ?", (work_item_id,))
        conn.execute("DELETE FROM human_notes WHERE work_item_id = ?", (work_item_id,))
        conn.execute("DELETE FROM work_items WHERE id = ?", (work_item_id,))
    return {"deleted": True, "id": work_item_id}


@app.post("/api/work-items/{work_item_id}/claim")
def claim_work_item(work_item_id: int, payload: ClaimRequest) -> dict:
    agent_id = ensure_agent(payload.agent_name, payload.agent_type)
    with connect() as conn:
        item = conn.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="work item not found")
        if item["claimed_by_agent_id"] and item["claimed_by_agent_id"] != agent_id:
            raise HTTPException(status_code=409, detail="work item already claimed")

        conn.execute(
            """
            UPDATE work_items
            SET status = 'claimed',
                claimed_by_agent_id = ?,
                claimed_at = CURRENT_TIMESTAMP,
                git_branch = COALESCE(?, git_branch),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (agent_id, payload.git_branch, work_item_id),
        )
        conn.execute(
            """
            UPDATE agents
            SET status = 'active', last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (agent_id,),
        )
        row = conn.execute(
            """
            SELECT wi.*, a.name AS claimed_by_agent_name
            FROM work_items wi
            LEFT JOIN agents a ON a.id = wi.claimed_by_agent_id
            WHERE wi.id = ?
            """,
            (work_item_id,),
        ).fetchone()
    return dict(row)


@app.post("/api/work-items/{work_item_id}/status")
def set_work_item_status(work_item_id: int, payload: WorkItemStatusUpdate) -> dict:
    agent_id = (
        ensure_agent(payload.agent_name, payload.agent_type) if payload.agent_name else None
    )
    legacy_status_id: int | None = None
    status_message = payload.message or f"transitioned work item to {payload.status}"
    with connect() as conn:
        item = conn.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,)).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="work item not found")

        conn.execute(
            """
            UPDATE work_items
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (payload.status, work_item_id),
        )

        if agent_id is not None:
            cursor = conn.execute(
                """
                INSERT INTO status_updates (agent_id, work_item_id, status, message)
                VALUES (?, ?, ?, ?)
                """,
                (
                    agent_id,
                    work_item_id,
                    payload.status,
                    status_message,
                ),
            )
            legacy_status_id = int(cursor.lastrowid)

        row = conn.execute(
            """
            SELECT wi.*, a.name AS claimed_by_agent_name
            FROM work_items wi
            LEFT JOIN agents a ON a.id = wi.claimed_by_agent_id
            WHERE wi.id = ?
            """,
            (work_item_id,),
        ).fetchone()
    if payload.topic_id is not None:
        from .messages import post_message

        post_message(
            topic_id=payload.topic_id,
            type="status",
            actor_type="agent" if agent_id is not None else "system",
            actor_id=agent_id,
            body=status_message,
            metadata={
                "agent_status": payload.status,
                "work_item_id": work_item_id,
                "legacy_row_id": legacy_status_id,
            },
        )
    return dict(row)


@app.post("/api/status")
def create_status(payload: StatusCreate) -> dict:
    agent_id = ensure_agent(payload.agent_name, payload.agent_type)
    with connect() as conn:
        conn.execute(
            """
            UPDATE agents
            SET status = ?, last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (payload.status, agent_id),
        )
        cursor = conn.execute(
            """
            INSERT INTO status_updates (agent_id, work_item_id, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (agent_id, payload.work_item_id, payload.status, payload.message),
        )
        row = conn.execute(
            """
            SELECT su.*, a.name AS agent_name, wi.title AS work_item_title
            FROM status_updates su
            JOIN agents a ON a.id = su.agent_id
            LEFT JOIN work_items wi ON wi.id = su.work_item_id
            WHERE su.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    if payload.topic_id is not None:
        from .messages import post_message

        post_message(
            topic_id=payload.topic_id,
            type="status",
            actor_type="agent",
            actor_id=agent_id,
            body=payload.message,
            metadata={
                "agent_status": payload.status,
                "work_item_id": payload.work_item_id,
                "legacy_row_id": cursor.lastrowid,
            },
        )
    return dict(row)


@app.post("/api/findings")
def create_finding(payload: FindingCreate) -> dict:
    agent_id = ensure_agent(payload.agent_name, payload.agent_type)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO findings (work_item_id, agent_id, title, body)
            VALUES (?, ?, ?, ?)
            """,
            (payload.work_item_id, agent_id, payload.title, payload.body),
        )
        row = conn.execute(
            """
            SELECT f.*, a.name AS agent_name, wi.title AS work_item_title
            FROM findings f
            JOIN agents a ON a.id = f.agent_id
            LEFT JOIN work_items wi ON wi.id = f.work_item_id
            WHERE f.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    if payload.topic_id is not None:
        from .messages import post_message

        post_message(
            topic_id=payload.topic_id,
            type="finding",
            actor_type="agent",
            actor_id=agent_id,
            body=f"{payload.title}\n\n{payload.body}",
            metadata={
                "title": payload.title,
                "work_item_id": payload.work_item_id,
                "legacy_row_id": cursor.lastrowid,
            },
        )
    return dict(row)


@app.post("/api/notes")
def create_note(payload: HumanNoteCreate) -> dict:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO human_notes (work_item_id, body)
            VALUES (?, ?)
            """,
            (payload.work_item_id, payload.body),
        )
        row = conn.execute("SELECT * FROM human_notes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


@app.post("/api/feedback")
def create_feedback(payload: FeedbackCreate) -> dict:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO human_notes (work_item_id, body, feedback_type)
            VALUES (?, ?, ?)
            """,
            (payload.work_item_id, payload.body, payload.feedback_type),
        )
        row = conn.execute("SELECT * FROM human_notes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    if payload.topic_id is not None:
        from .messages import post_message

        message_type = "question" if payload.feedback_type == "question" else "chat"
        post_message(
            topic_id=payload.topic_id,
            type=message_type,
            actor_type="human",
            actor_id=None,
            body=payload.body,
            metadata={
                "feedback_type": payload.feedback_type,
                "work_item_id": payload.work_item_id,
                "legacy_row_id": cursor.lastrowid,
            },
        )
    return dict(row)


@app.get("/api/agents")
def list_agents() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM agents
            ORDER BY last_seen_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/agent-instances")
def list_all_agent_instances(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    """List every agent_instance plus an `is_online` flag (token used in
    the last 5 minutes). Sorted online first, then by last_seen_at desc.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                ai.id as agent_instance_id,
                ar.name as role,
                ai.device_label,
                h.id as human_id,
                h.name as human_name,
                MAX(t.last_used_at) as last_seen_at,
                CASE
                    WHEN MAX(t.last_used_at) IS NOT NULL
                     AND MAX(t.last_used_at) >= datetime('now', '-5 minutes')
                    THEN 1 ELSE 0
                END as is_online
            FROM agent_instances ai
            JOIN agent_roles ar ON ar.id = ai.role_id
            JOIN humans h ON h.id = ai.human_id
            LEFT JOIN tokens t ON t.agent_instance_id = ai.id
                              AND t.revoked_at IS NULL
            GROUP BY ai.id, ar.name, ai.device_label, h.id, h.name
            ORDER BY is_online DESC, last_seen_at DESC, ai.id ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/agents/online")
def list_online_agents(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    """Returns agent_instances whose token was used in the last 5 minutes."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                ai.id as agent_instance_id,
                ar.name as role,
                ai.device_label,
                h.name as human_name,
                MAX(t.last_used_at) as last_seen_at
            FROM tokens t
            JOIN agent_instances ai ON ai.id = t.agent_instance_id
            JOIN agent_roles ar ON ar.id = ai.role_id
            JOIN humans h ON h.id = ai.human_id
            WHERE t.agent_instance_id IS NOT NULL
              AND t.revoked_at IS NULL
              AND t.last_used_at IS NOT NULL
              AND t.last_used_at >= datetime('now', '-5 minutes')
            GROUP BY ai.id, ar.name, ai.device_label, h.name
            ORDER BY last_seen_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/findings")
def list_findings() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT f.*, a.name AS agent_name, wi.title AS work_item_title
            FROM findings f
            JOIN agents a ON a.id = f.agent_id
            LEFT JOIN work_items wi ON wi.id = f.work_item_id
            ORDER BY f.created_at DESC, f.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/activity")
def list_activity() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT created_at, 'status' AS kind, agent_name AS actor, message AS summary
            FROM (
                SELECT su.created_at, a.name AS agent_name,
                       su.message AS message
                FROM status_updates su
                JOIN agents a ON a.id = su.agent_id
            )
            UNION ALL
            SELECT created_at, 'finding' AS kind, agent_name AS actor, title AS summary
            FROM (
                SELECT f.created_at, a.name AS agent_name, f.title AS title
                FROM findings f
                JOIN agents a ON a.id = f.agent_id
            )
            UNION ALL
            SELECT created_at, 'note' AS kind, 'human' AS actor, body AS summary
            FROM human_notes
            ORDER BY created_at DESC
            LIMIT 30
            """
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/messages")
async def post_message_endpoint(
    payload: MessageCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .messages import post_message
    from .sse import broadcaster

    message_id = post_message(
        topic_id=payload.topic_id,
        type=payload.type,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        body=payload.body,
        metadata=payload.metadata,
        ref_event_id=payload.ref_event_id,
        addressed_to=payload.addressed_to,
    )
    with connect() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()

    message = dict(row)
    message["metadata"] = json.loads(message["metadata"])

    # The endpoint runs inside the event loop (async def), so publish
    # is awaited directly — there's no threadpool boundary. Sync sqlite
    # work above is fine for v1.5b (single-replica + small write rate).
    await broadcaster.publish(payload.topic_id, message)

    return message


@app.get("/api/topics/{topic_id}/messages")
def get_topic_messages(
    topic_id: int,
    type: list[str] | None = Query(default=None),
    limit: int = 500,
    after_id: int | None = None,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .drift import compute_drift_context
    from .messages import topic_stream

    return {
        "messages": topic_stream(
            topic_id, type_filter=type, limit=limit, after_id=after_id,
        ),
        "drift_context": compute_drift_context(topic_id),
    }


@app.get("/api/topics/{topic_id}/task-tree")
def get_topic_task_tree(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .task_trees import get_tree_by_topic, list_items
    tree = get_tree_by_topic(topic_id)
    if tree is None:
        return {"tree": None, "items": []}
    return {"tree": tree, "items": list_items(tree["id"])}


@app.post("/api/topics/{topic_id}/task-tree", status_code=201)
def adopt_task_tree(
    topic_id: int,
    payload: TaskTreeAdoptInput,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    from .messages import topic_stream
    from .task_trees import list_items, replace_items, upsert_tree

    if not lets_session:
        raise HTTPException(status_code=401, detail="session required")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    # Find the proposal message in this topic
    msgs = topic_stream(topic_id, limit=10000)
    proposal = next(
        (m for m in msgs if m["id"] == payload.proposal_message_id),
        None,
    )
    if proposal is None or proposal["type"] != "task_tree_proposal":
        raise HTTPException(status_code=400, detail="proposal not found in topic")

    meta = proposal["metadata"] or {}
    items = meta.get("items") or []
    tree = upsert_tree(
        topic_id=topic_id,
        goal_artifact_id=None,
        goal_spec_text=None,
        proposal_message_id=payload.proposal_message_id,
        approved_by_human_id=principal["human_id"],
    )
    replace_items(tree["id"], items)
    return {"tree": tree, "items": list_items(tree["id"])}


@app.post("/api/topics/{topic_id}/goal", status_code=201)
def adopt_goal(
    topic_id: int,
    payload: GoalAdoptInput,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    from .messages import topic_stream
    from .task_trees import list_items, upsert_tree

    if not lets_session:
        raise HTTPException(status_code=401, detail="session required")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    artifact_id: int | None = payload.artifact_id
    spec_text: str | None = payload.spec_text

    if payload.goal_proposal_message_id is not None:
        msgs = topic_stream(topic_id, limit=10000)
        proposal = next(
            (m for m in msgs if m["id"] == payload.goal_proposal_message_id),
            None,
        )
        if proposal is None or proposal["type"] != "goal_proposal":
            raise HTTPException(status_code=400, detail="proposal not found in topic")
        meta = proposal["metadata"] or {}
        artifact_id = artifact_id or meta.get("artifact_id")
        spec_text = spec_text or meta.get("spec_text") or proposal["body"]

    if not spec_text and artifact_id is None:
        raise HTTPException(status_code=400, detail="goal must have spec_text or artifact_id")

    tree = upsert_tree(
        topic_id=topic_id,
        goal_artifact_id=artifact_id,
        goal_spec_text=spec_text,
        proposal_message_id=payload.goal_proposal_message_id,
        approved_by_human_id=principal["human_id"],
    )
    return {"tree": tree, "items": list_items(tree["id"])}


@app.post("/api/task-items", status_code=201)
def post_task_item(
    payload: TaskItemCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .task_trees import add_item
    return add_item(
        tree_id=payload.task_tree_id,
        title=payload.title,
        parent_item_id=payload.parent_item_id,
        summary=payload.summary,
        linked_message_id=payload.linked_message_id,
        deliverable_artifact_id=payload.deliverable_artifact_id,
        owner_human_id=payload.owner_human_id,
        owner_agent_instance_id=payload.owner_agent_instance_id,
    )


@app.patch("/api/task-items/{item_id}")
def patch_task_item(
    item_id: int,
    payload: TaskItemPatch,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .task_trees import update_item
    try:
        return update_item(
            item_id,
            status=payload.status,
            title=payload.title,
            summary=payload.summary,
            linked_message_id=payload.linked_message_id,
            deliverable_artifact_id=payload.deliverable_artifact_id,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="task_item not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class NudgeResolveInput(BaseModel):
    resolved_by: str
    spinoff_title: str | None = None


@app.post("/api/nudges/{drift_nudge_id}/resolve")
def resolve_drift_nudge(
    drift_nudge_id: int,
    payload: NudgeResolveInput,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    from .db import connect
    from .drift import resolve_nudge
    from .messages import post_message

    if not lets_session:
        raise HTTPException(status_code=401, detail="session required")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    # Read the existing nudge for context
    with connect() as conn:
        nudge_row = conn.execute(
            "SELECT * FROM drift_nudges WHERE id = ?", (drift_nudge_id,)
        ).fetchone()
    if nudge_row is None:
        raise HTTPException(status_code=404, detail="nudge not found")

    resolved_to_topic_id: int | None = None

    if payload.resolved_by == "moved_to_topic":
        if not payload.spinoff_title:
            raise HTTPException(status_code=400, detail="spinoff_title required")
        # Create the new topic in the same project
        with connect() as conn:
            src_topic = conn.execute(
                "SELECT project_id FROM topics WHERE id = ?", (nudge_row["topic_id"],)
            ).fetchone()
            project_id = src_topic["project_id"] if src_topic else None
            # Generate a slug from the title (lower, replace ws with -)
            import re, time
            slug_base = re.sub(r"\s+", "-", payload.spinoff_title.strip().lower())[:60]
            slug = f"{slug_base}-{int(time.time())}"
            cur = conn.execute(
                "INSERT INTO topics (slug, title, project_id) VALUES (?, ?, ?)",
                (slug, payload.spinoff_title, project_id),
            )
            new_topic_id = int(cur.lastrowid)
        # Post a system message summarizing the spinoff
        summary_body = (
            f"从 topic#{nudge_row['topic_id']} 迁移而来。"
            f"摘要：{nudge_row['drift_summary'] or '（无摘要）'}"
        )
        post_message(
            topic_id=new_topic_id, type="system",
            actor_type="system", actor_id=None,
            body=summary_body, metadata={"source_topic_id": nudge_row["topic_id"]},
        )
        resolved_to_topic_id = new_topic_id

    elif payload.resolved_by not in ("returned", "dismissed"):
        raise HTTPException(status_code=400, detail="invalid resolved_by")

    try:
        return resolve_nudge(
            drift_nudge_id, payload.resolved_by,
            resolved_to_topic_id=resolved_to_topic_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/events")
def post_event(
    payload: EventCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .events import record_event

    event_id = record_event(
        event_type=payload.event_type,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        project_id=payload.project_id,
        topic_id=payload.topic_id,
        payload=payload.payload,
    )
    with connect() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

    event = dict(row)
    event["payload"] = json.loads(event["payload"])
    return event


@app.get("/api/events")
def get_events(
    target_type: str | None = None,
    target_id: int | None = None,
    topic_id: int | None = None,
    event_type: str | None = None,
    limit: int = 100,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .events import query_events

    return query_events(
        target_type=target_type,
        target_id=target_id,
        topic_id=topic_id,
        event_type=event_type,
        limit=limit,
    )


@app.get("/api/attention")
def get_attention_queue(
    human_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .attention import get_attention
    return get_attention(human_id)


@app.get("/api/identity/me")
def identity_me(
    x_lets_human: str | None = Header(default=None, alias="X-Lets-Human"),
    x_lets_human_email: str | None = Header(default=None, alias="X-Lets-Human-Email"),
    x_lets_agent_role: str | None = Header(default=None, alias="X-Lets-Agent-Role"),
    x_lets_device: str | None = Header(default=None, alias="X-Lets-Device"),
) -> dict:
    if not x_lets_human:
        raise HTTPException(status_code=400, detail="X-Lets-Human header required")

    from .identity import ensure_agent_instance, ensure_human

    human_id = ensure_human(x_lets_human, email=x_lets_human_email)
    result: dict[str, Any] = {
        "human": {"id": human_id, "name": x_lets_human},
    }
    if x_lets_agent_role and x_lets_device:
        try:
            agent_instance_id = ensure_agent_instance(
                role=x_lets_agent_role,
                human_id=human_id,
                device_label=x_lets_device,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        result["agent_instance"] = {
            "id": agent_instance_id,
            "role": x_lets_agent_role,
            "device_label": x_lets_device,
        }

    return result


@app.post("/api/artifacts")
def post_artifact(
    payload: ArtifactCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import create_artifact_row, record_version, get_artifact_by_id

    if payload.backend != "git":
        raise HTTPException(status_code=400, detail="only 'git' backend supported in v1.5b")

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")

    adapter = get_adapter("git", repo_path=repo_path)
    content = base64.b64decode(payload.content_b64)
    try:
        result = adapter.create(
            slug=payload.slug, content=content,
            metadata={"type": payload.type, "summary": payload.summary or f"create {payload.slug}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"backend error: {e}")

    art_id = create_artifact_row(
        slug=payload.slug, type=payload.type, backend=payload.backend,
        backend_ref=result.backend_ref, title=payload.title, topic_id=payload.topic_id,
    )
    v_id = record_version(
        artifact_id=art_id, version_label="v0",
        backend_revision_id=result.revision_id, summary=payload.summary,
    )
    return {
        "artifact": get_artifact_by_id(art_id),
        "version": {"id": v_id, "version_label": "v0",
                    "backend_revision_id": result.revision_id},
    }


@app.post("/api/artifacts/{artifact_id}/update")
def update_artifact(
    artifact_id: int,
    payload: ArtifactUpdate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import record_version, get_artifact_by_id

    art = get_artifact_by_id(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="artifact not found")
    if art["backend"] != "git":
        raise HTTPException(status_code=400, detail="only 'git' backend supported in v1.5b")
    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")

    adapter = get_adapter("git", repo_path=repo_path)
    content = base64.b64decode(payload.content_b64)
    try:
        result = adapter.update(
            backend_ref=art["backend_ref"], content=content,
            metadata={"summary": payload.summary or f"update {art['slug']}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"backend error: {e}")

    v_id = record_version(
        artifact_id=artifact_id, version_label=payload.version_label,
        backend_revision_id=result.revision_id, summary=payload.summary,
    )
    return {"version": {"id": v_id, "version_label": payload.version_label,
                        "backend_revision_id": result.revision_id}}


@app.get("/api/artifacts/{artifact_id}/versions")
def list_artifact_versions(
    artifact_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .artifacts.models import get_artifact_by_id, list_versions_by_artifact
    if not get_artifact_by_id(artifact_id):
        raise HTTPException(status_code=404, detail="artifact not found")
    return list_versions_by_artifact(artifact_id)


@app.get("/api/artifacts/{artifact_id}/diff")
def artifact_diff(
    artifact_id: int,
    from_label: str,
    to_label: str,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import get_artifact_by_id, list_versions_by_artifact

    art = get_artifact_by_id(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="artifact not found")

    versions = list_versions_by_artifact(artifact_id)
    by_label = {v["version_label"]: v for v in versions}
    if from_label not in by_label or to_label not in by_label:
        raise HTTPException(status_code=404, detail="version label not found")

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")
    adapter = get_adapter("git", repo_path=repo_path)
    diff = adapter.diff(
        backend_ref=art["backend_ref"],
        from_revision=by_label[from_label]["backend_revision_id"],
        to_revision=by_label[to_label]["backend_revision_id"],
    )
    return {"from_label": from_label, "to_label": to_label, "diff": diff}


@app.get("/api/artifacts/{artifact_id}")
def read_artifact(
    artifact_id: int,
    version_label: str | None = None,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import get_artifact_by_id, list_versions_by_artifact

    art = get_artifact_by_id(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="artifact not found")

    versions = list_versions_by_artifact(artifact_id)
    by_label = {v["version_label"]: v for v in versions}
    current_v = None
    revision_id = None
    if version_label:
        if version_label not in by_label:
            raise HTTPException(status_code=404, detail="version label not found")
        current_v = version_label
        revision_id = by_label[version_label]["backend_revision_id"]
    else:
        if versions:
            current_v = versions[-1]["version_label"]

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")
    adapter = get_adapter("git", repo_path=repo_path)
    content = adapter.read(backend_ref=art["backend_ref"], revision_id=revision_id)
    return {
        "artifact": art,
        "content_b64": base64.b64encode(content).decode("ascii"),
        "current_version_label": current_v,
    }


@app.post("/api/projects")
def post_project(
    payload: ProjectCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .projects import create_project, get_project_by_id
    try:
        pid = create_project(
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            owner_human_id=principal["human_id"],
            repo_path=payload.repo_path,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return get_project_by_id(pid)


@app.get("/api/projects")
def get_projects(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .projects import list_projects
    return list_projects()


@app.get("/api/projects/{project_id}")
def get_project(
    project_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .projects import get_project_by_id
    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    return p


@app.patch("/api/projects/{project_id}")
def patch_project(
    project_id: int,
    payload: ProjectPatch,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .projects import get_project_by_id, update_project
    if not get_project_by_id(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    update_project(
        project_id,
        name=payload.name,
        description=payload.description,
        repo_path=payload.repo_path,
    )
    return get_project_by_id(project_id)


@app.get("/api/projects/{project_id}/spec")
def get_project_spec(
    project_id: int,
    include_content: bool = False,
    principal: dict = Depends(get_api_principal),
) -> dict:
    """Read-only Spec view: lists CLAUDE.md, .mcp.json, and .claude/** files.

    Returns each file's relative path, size, and optionally base64-encoded
    content. Files outside the project's repo_path cannot be reached.
    """
    from pathlib import Path
    from .projects import get_project_by_id

    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    if not p.get("repo_path"):
        raise HTTPException(status_code=404, detail="project has no repo_path configured")

    root = Path(p["repo_path"]).resolve()
    if not root.exists() or not root.is_dir():
        raise HTTPException(status_code=404, detail="repo_path does not exist or is not a directory")

    # Collect candidate spec files
    candidates: list[Path] = []
    for top_name in ("CLAUDE.md", ".mcp.json", ".claude"):
        p_node = root / top_name
        if not p_node.exists():
            continue
        if p_node.is_file():
            candidates.append(p_node)
        elif p_node.is_dir():
            for f in p_node.rglob("*"):
                if f.is_file():
                    candidates.append(f)

    files_out: list[dict] = []
    for f in candidates:
        try:
            resolved = f.resolve()
            # Defense: reject anything that escapes root
            resolved.relative_to(root)
        except ValueError:
            continue
        rel = resolved.relative_to(root).as_posix()
        entry: dict = {
            "path": rel,
            "size": resolved.stat().st_size,
        }
        if include_content:
            import base64
            try:
                entry["content_b64"] = base64.b64encode(resolved.read_bytes()).decode("ascii")
            except OSError:
                entry["content_b64"] = None
        files_out.append(entry)

    return {
        "project_id": project_id,
        "repo_path": p["repo_path"],
        "files": sorted(files_out, key=lambda x: x["path"]),
    }


class SpecApply(BaseModel):
    file: str = Field(min_length=1)
    content: str


@app.post("/api/projects/{project_id}/spec/apply")
def apply_spec_change(
    project_id: int,
    payload: SpecApply,
    principal: dict = Depends(get_api_principal),
) -> dict:
    import os
    from pathlib import Path
    from .projects import get_project_by_id

    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    if not p.get("repo_path"):
        raise HTTPException(status_code=404, detail="project has no repo_path")
    root = Path(p["repo_path"]).resolve()
    if not root.is_dir():
        raise HTTPException(status_code=404, detail="repo_path missing")

    rel = payload.file
    # Reject absolute paths and any traversal segment
    if rel.startswith("/") or ".." in Path(rel).parts:
        raise HTTPException(status_code=400, detail="invalid file path")
    # Only allow the managed spec set
    if not (rel == "CLAUDE.md" or rel == ".mcp.json" or rel.startswith(".claude/")):
        raise HTTPException(status_code=400, detail="file is not in managed spec set")

    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="path escapes repo_path")

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".lets-tmp")
    tmp.write_text(payload.content, encoding="utf-8")
    os.replace(tmp, target)
    return {"ok": True, "file": rel, "bytes": target.stat().st_size}


@app.post("/api/projects/{project_id}/topics")
def post_topic(
    project_id: int,
    payload: TopicCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .projects import get_project_by_id
    from .topics import create_topic, get_topic_by_id
    if not get_project_by_id(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    try:
        tid = create_topic(slug=payload.slug, title=payload.title, project_id=project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return get_topic_by_id(tid)


@app.get("/api/projects/{project_id}/topics")
def get_topics_in_project(
    project_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .projects import get_project_by_id
    from .topics import list_topics_by_project
    if not get_project_by_id(project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return list_topics_by_project(project_id)


@app.get("/api/topics/{topic_id}")
def get_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .topics import get_topic_by_id
    t = get_topic_by_id(topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="topic not found")
    return t


@app.get("/api/topics/{topic_id}/stream")
async def stream_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
):
    """Server-Sent Events stream of new messages on a topic.

    Each message posted via POST /api/messages is published as one
    ``data: <json>\\n\\n`` SSE event. A ``:heartbeat`` comment is emitted
    every 15s of idle so proxies don't drop the connection. Clients can
    pass ``Last-Event-ID`` or use ``?after_id=`` on the messages endpoint
    to catch up on missed traffic after a reconnect.
    """
    from fastapi.responses import StreamingResponse
    from .sse import broadcaster
    import asyncio
    import json as _json

    async def event_gen():
        queue = await broadcaster.subscribe(topic_id)
        try:
            # Emit an opening comment so the response head flushes immediately
            # (important for client.stream() and reverse proxies alike).
            yield ":ok\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {_json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ":heartbeat\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            broadcaster.unsubscribe(topic_id, queue)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Context-pane endpoints (Track C1.5 Task 3)
# ---------------------------------------------------------------------------


@app.get("/api/artifacts")
def list_artifacts_by_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    """List artifacts attached to ``topic_id``, ordered by id ASC.

    Each artifact row includes a ``versions`` array (chronological) so
    the web UI can render the version chain without N+1 round-trips.
    """
    from .db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM artifacts WHERE topic_id = ? ORDER BY id ASC",
            (topic_id,),
        ).fetchall()
        artifacts = [dict(r) for r in rows]
        if not artifacts:
            return []
        ids = [a["id"] for a in artifacts]
        placeholders = ",".join("?" * len(ids))
        vrows = conn.execute(
            f"SELECT * FROM artifact_versions WHERE artifact_id IN ({placeholders}) "
            f"ORDER BY artifact_id, id ASC",
            ids,
        ).fetchall()
    by_artifact: dict[int, list[dict]] = {a["id"]: [] for a in artifacts}
    for r in vrows:
        d = dict(r)
        by_artifact[int(d["artifact_id"])].append(d)
    for a in artifacts:
        a["versions"] = by_artifact.get(a["id"], [])
    return artifacts


@app.get("/api/topics/{topic_id}/participants")
def get_topic_participants(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    """Return the distinct humans and agents that have posted on a topic."""
    from .db import connect
    with connect() as conn:
        humans = [dict(r) for r in conn.execute(
            """
            SELECT DISTINCT h.id, h.name, h.email
            FROM messages m JOIN humans h ON h.id = m.actor_id
            WHERE m.topic_id = ? AND m.actor_type = 'human'
            ORDER BY h.id ASC
            """,
            (topic_id,),
        ).fetchall()]
        agents = [dict(r) for r in conn.execute(
            """
            SELECT DISTINCT
                ai.id,
                ai.device_label,
                ar.name AS role,
                ah.name AS human_name
            FROM messages m
            JOIN agent_instances ai ON ai.id = m.actor_id
            JOIN agent_roles ar ON ar.id = ai.role_id
            JOIN humans ah ON ah.id = ai.human_id
            WHERE m.topic_id = ? AND m.actor_type = 'agent'
            ORDER BY ai.id ASC
            """,
            (topic_id,),
        ).fetchall()]
    return {"humans": humans, "agents": agents}


@app.get("/api/projects/{project_id}/git-status")
def get_project_git_status(
    project_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    """Return HEAD commit + dirty-file list for a project's repo_path."""
    import subprocess
    from pathlib import Path
    from .projects import get_project_by_id

    p = get_project_by_id(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    if not p.get("repo_path"):
        raise HTTPException(status_code=404, detail="project has no repo_path")
    repo = Path(p["repo_path"]).resolve()
    if not (repo / ".git").exists():
        raise HTTPException(status_code=404, detail="repo_path is not a git repo")

    def _run(args: list[str]) -> str:
        return subprocess.run(
            ["git"] + args, cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    log = _run(["log", "-1", "--pretty=format:%H|%h|%s|%an|%ai"])
    parts = log.split("|", 4)
    head = {
        "sha": parts[0],
        "short_sha": parts[1] if len(parts) > 1 else "",
        "subject": parts[2] if len(parts) > 2 else "",
        "author": parts[3] if len(parts) > 3 else "",
        "date": parts[4] if len(parts) > 4 else "",
    }
    status = _run(["status", "--short"])
    dirty = [line for line in status.splitlines() if line.strip()]
    return {"head": head, "dirty": dirty}


# ---------------------------------------------------------------------------
# SPA mount (Track C1.5 Task 7 + Track F Task 39)
#
# Two resolution paths, in priority order:
#   1. ``LETS_FRONTEND_DIST`` env var — explicit override (legacy / tests).
#   2. ``<repo>/frontend/dist`` — auto-discovered from the built React SPA.
#
# When a built ``index.html`` is found, expose:
#   * ``/app/assets/*`` — hashed JS/CSS via StaticFiles
#   * ``/app`` and ``/app/{rest:path}`` — SPA fallback serving ``index.html``
#
# The mount is conditional so ``tests/`` still pass without a built frontend.
# Resolved at module-import time; tests reload this module under a
# monkeypatched env var.
# ---------------------------------------------------------------------------

import pathlib as _spa_pathlib
from fastapi.staticfiles import StaticFiles as _SpaStaticFiles

_frontend_dist_env = os.environ.get("LETS_FRONTEND_DIST")
if _frontend_dist_env:
    _FRONTEND_DIST = _spa_pathlib.Path(_frontend_dist_env)
else:
    _FRONTEND_DIST = _spa_pathlib.Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount(
            "/app/assets",
            _SpaStaticFiles(directory=_assets_dir),
            name="frontend-assets",
        )

    @app.get("/app")
    @app.get("/app/{rest:path}")
    def serve_app(rest: str = "") -> FileResponse:
        _ = rest  # path consumed for SPA fallback; index.html does the routing
        index = _FRONTEND_DIST / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404, detail="frontend not built")
        return FileResponse(index)


# ---------------------------------------------------------------------------
# GitHub OAuth + session cookie (Track F Task 43)
#
# - GET  /auth/github/start     — 307 → github.com/login/oauth/authorize
# - GET  /auth/github/callback  — exchange code, upsert humans row, set cookie
# - GET  /auth/me               — current human or 401
# - POST /auth/logout           — revoke session cookie
#
# State store is in-memory (single-process v1.5a; Railway runs one instance).
# GitHub HTTP calls live in ``_gh_exchange_code`` / ``_gh_fetch_user`` so
# tests can monkeypatch them without going over the network.
# ---------------------------------------------------------------------------

import urllib.parse as _urllib_parse
import secrets as _secrets
import time as _time

import httpx
from fastapi import Cookie
from fastapi.responses import Response


_OAUTH_STATES: dict[str, float] = {}
_OAUTH_TTL_S = 600.0


def _new_state() -> str:
    now = _time.time()
    # Lazy cleanup of expired states.
    for k, ts in list(_OAUTH_STATES.items()):
        if now - ts > _OAUTH_TTL_S:
            _OAUTH_STATES.pop(k, None)
    s = _secrets.token_urlsafe(24)
    _OAUTH_STATES[s] = now
    return s


def _consume_state(s: str) -> bool:
    return _OAUTH_STATES.pop(s, None) is not None


@app.get("/auth/github/start")
def auth_github_start() -> RedirectResponse:
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
    state = _new_state()
    params = {
        "client_id": client_id,
        "redirect_uri": os.environ.get(
            "GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback"
        ),
        "scope": "read:user user:email",
        "state": state,
        "allow_signup": "true",
    }
    url = "https://github.com/login/oauth/authorize?" + _urllib_parse.urlencode(params)
    return RedirectResponse(url=url, status_code=307)


async def _gh_exchange_code(code: str):
    """POST code -> access_token. Patched in tests; do not inline."""
    async with httpx.AsyncClient(timeout=10.0) as cli:
        return await cli.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": os.environ["GITHUB_CLIENT_ID"],
                "client_secret": os.environ["GITHUB_CLIENT_SECRET"],
                "code": code,
            },
            headers={"Accept": "application/json"},
        )


async def _gh_fetch_user(access_token: str):
    """GET /user with bearer token. Patched in tests; do not inline."""
    async with httpx.AsyncClient(timeout=10.0) as cli:
        return await cli.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )


@app.get("/auth/github/callback")
async def auth_github_callback(code: str, state: str) -> RedirectResponse:
    if not _consume_state(state):
        raise HTTPException(status_code=400, detail="invalid state")

    tok = await _gh_exchange_code(code)
    if tok.status_code != 200:
        raise HTTPException(status_code=502, detail="github token exchange failed")
    access_token = tok.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="no access_token in github response")

    u = await _gh_fetch_user(access_token)
    if u.status_code != 200:
        raise HTTPException(status_code=502, detail="github user fetch failed")
    info = u.json()

    github_id = int(info["id"])
    github_login = str(info["login"])
    display_name = info.get("name") or github_login
    avatar_url = info.get("avatar_url")
    email = info.get("email")

    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM humans WHERE github_id = ?", (github_id,)
        ).fetchone()
        if row is not None:
            human_id = row["id"]
            conn.execute(
                """
                UPDATE humans SET github_login = ?, avatar_url = ?,
                       name = COALESCE(?, name), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (github_login, avatar_url, display_name, human_id),
            )
        else:
            # Resolve name uniqueness — humans.name is UNIQUE.
            base = display_name
            candidate = base
            i = 2
            while conn.execute(
                "SELECT 1 FROM humans WHERE name = ?", (candidate,)
            ).fetchone():
                candidate = f"{base} ({i})"
                i += 1
            cursor = conn.execute(
                """
                INSERT INTO humans (name, email, github_id, github_login, avatar_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (candidate, email, github_id, github_login, avatar_url),
            )
            human_id = int(cursor.lastrowid)

    from .auth import issue_session

    session_value = issue_session(human_id)
    res = RedirectResponse(url="/app", status_code=307)
    res.set_cookie(
        "lets_session",
        session_value,
        httponly=True,
        secure=os.environ.get("LETS_COOKIE_SECURE", "true").lower() != "false",
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return res


@app.get("/auth/me")
def auth_me(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session

    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")
    return {
        "human": {
            "id": principal["human_id"],
            "name": principal["name"],
            "github_login": principal["github_login"],
            "avatar_url": principal["avatar_url"],
        }
    }


@app.get("/auth/dev/login")
def auth_dev_login(human: str = "Neo", next: str = "/app") -> RedirectResponse:
    """Dev-only browser login for local website testing.

    Enabled only when ``LETS_DEV_SESSIONS=1``. This gives local dogfood the
    same browser-session shape as GitHub OAuth without requiring a localhost
    OAuth app while Railway deploys are unavailable.
    """
    if os.environ.get("LETS_DEV_SESSIONS") != "1":
        raise HTTPException(status_code=404, detail="not found")
    if not next.startswith("/") or next.startswith("//"):
        next = "/app"

    from .auth import issue_session
    from .identity import ensure_human

    human_id = ensure_human(human.strip() or "Neo")
    session_value = issue_session(human_id)
    res = RedirectResponse(url=next, status_code=307)
    res.set_cookie(
        "lets_session",
        session_value,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return res


@app.post("/auth/logout", status_code=204)
def auth_logout(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> Response:
    from .auth import revoke_session

    if lets_session:
        revoke_session(lets_session)
    res = Response(status_code=204)
    res.delete_cookie("lets_session", path="/")
    return res


# ---------------------------------------------------------------------------
# Device flow for local gateway login
#
# Minimal GitHub-device-flow style handshake:
# - gateway starts flow and prints verification_url
# - user opens URL in an already logged-in browser session
# - backend creates the agent_instance + token and lets gateway poll it once
# ---------------------------------------------------------------------------


def _new_user_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(_secrets.choice(alphabet) for _ in range(4)) + "-" + "".join(
        _secrets.choice(alphabet) for _ in range(4)
    )


@app.get("/auth/device-flow/start")
def device_flow_start(
    request: Request,
    role: str = Query(default="claude"),
    device_label: str = Query(default="local"),
) -> dict:
    if role not in ("claude", "codex"):
        raise HTTPException(status_code=400, detail="role must be claude or codex")
    device_label = device_label.strip()[:80] or "local"
    device_code = _secrets.token_urlsafe(32)
    user_code = _new_user_code()
    with connect() as conn:
        while conn.execute(
            "SELECT 1 FROM device_auth_flows WHERE user_code = ?", (user_code,)
        ).fetchone():
            user_code = _new_user_code()
        conn.execute(
            """
            INSERT INTO device_auth_flows
                (device_code, user_code, role, device_label, expires_at)
            VALUES (?, ?, ?, ?, datetime('now', '+10 minutes'))
            """,
            (device_code, user_code, role, device_label),
        )
    base_url = _public_base_url(request)
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_url": f"{base_url}/auth/device-flow/authorize?user_code={user_code}",
        "expires_in": 600,
        "interval": 3,
    }


@app.get("/auth/device-flow/authorize")
def device_flow_authorize(
    user_code: str,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> HTMLResponse:
    from .auth import issue_token, verify_session
    from .identity import ensure_agent_instance

    if not lets_session:
        raise HTTPException(status_code=401, detail="login in the browser first")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    normalized = user_code.strip().upper()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM device_auth_flows
            WHERE user_code = ? AND consumed_at IS NULL
            """,
            (normalized,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="device flow not found")
        if row["authorized_at"] is not None:
            return HTMLResponse("<h1>Lets gateway already authorized</h1>")
        expired = conn.execute(
            "SELECT CURRENT_TIMESTAMP > ? AS expired", (row["expires_at"],)
        ).fetchone()["expired"]
        if expired:
            raise HTTPException(status_code=410, detail="device flow expired")

    human_id = int(principal["human_id"])
    role = str(row["role"])
    device_label = str(row["device_label"])
    agent_instance_id = ensure_agent_instance(
        role=role,
        human_id=human_id,
        device_label=device_label,
    )
    token_value, token_id = issue_token(
        human_id=human_id,
        agent_instance_id=agent_instance_id,
        label=f"{role} on {device_label}",
    )
    with connect() as conn:
        conn.execute(
            """
            UPDATE device_auth_flows
            SET human_id = ?, agent_instance_id = ?, token_id = ?,
                token_value = ?, authorized_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (human_id, agent_instance_id, token_id, token_value, row["id"]),
        )

    return HTMLResponse(
        """
        <!doctype html>
        <meta charset="utf-8">
        <title>Lets gateway authorized</title>
        <body style="font-family: system-ui; padding: 32px">
          <h1>Lets gateway authorized</h1>
          <p>You can close this tab and return to your terminal.</p>
        </body>
        """
    )


@app.get("/auth/device-flow/poll")
def device_flow_poll(device_code: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM device_auth_flows WHERE device_code = ?",
            (device_code,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="device flow not found")
        expired = conn.execute(
            "SELECT CURRENT_TIMESTAMP > ? AS expired", (row["expires_at"],)
        ).fetchone()["expired"]
        if expired and row["authorized_at"] is None:
            raise HTTPException(status_code=410, detail="device flow expired")
        if row["authorized_at"] is None:
            return {"status": "pending"}
        if row["consumed_at"] is not None or row["token_value"] is None:
            raise HTTPException(status_code=410, detail="device token already consumed")
        token_value = row["token_value"]
        conn.execute(
            """
            UPDATE device_auth_flows
            SET consumed_at = CURRENT_TIMESTAMP, token_value = NULL
            WHERE id = ?
            """,
            (row["id"],),
        )
        agent = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label
            FROM agent_instances ai
            JOIN agent_roles ar ON ar.id = ai.role_id
            WHERE ai.id = ?
            """,
            (row["agent_instance_id"],),
        ).fetchone()
    return {
        "status": "authorized",
        "token": token_value,
        "agent_instance": dict(agent) if agent else None,
    }


# ---------------------------------------------------------------------------
# REST tokens CRUD (Track F Task 44)
#
# Session-gated endpoints for logged-in humans to mint, list, and revoke their
# own agent tokens. The raw token value is shown ONCE on create and never echoed
# in list responses.
# ---------------------------------------------------------------------------


class TokenCreate(BaseModel):
    label: str
    role: str
    device_label: str


@app.get("/api/tokens")
def list_my_tokens(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> list[dict]:
    from .auth import verify_session, list_tokens
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")
    tokens = list_tokens(human_id=principal["human_id"])
    with connect() as conn:
        agent_rows = {
            int(r["id"]): {
                "id": int(r["id"]),
                "role": r["role"],
                "device_label": r["device_label"],
            }
            for r in conn.execute(
                """
                SELECT ai.id, ar.name AS role, ai.device_label
                FROM agent_instances ai
                JOIN agent_roles ar ON ar.id = ai.role_id
                WHERE ai.human_id = ?
                """,
                (principal["human_id"],),
            ).fetchall()
        }
    # Strip internal fields
    out = []
    for t in tokens:
        row = {k: v for k, v in t.items() if k not in ("value_hash",)}
        if t.get("agent_instance_id") is not None:
            row["agent_instance"] = agent_rows.get(int(t["agent_instance_id"]))
        else:
            row["agent_instance"] = None
        out.append(row)
    return out


@app.post("/api/tokens", status_code=201)
def create_my_token(
    payload: TokenCreate,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session, issue_token
    from .identity import ensure_agent_instance
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    agent_instance_id = ensure_agent_instance(
        role=payload.role,
        human_id=principal["human_id"],
        device_label=payload.device_label,
    )
    raw_value, token_id = issue_token(
        human_id=principal["human_id"],
        agent_instance_id=agent_instance_id,
        label=payload.label,
    )
    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label
            FROM agent_instances ai
            JOIN agent_roles ar ON ar.id = ai.role_id
            WHERE ai.id = ?
            """,
            (agent_instance_id,),
        ).fetchone()
    return {
        "id": token_id,
        "value": raw_value,
        "label": payload.label,
        "agent_instance": dict(row),
    }


@app.delete("/api/tokens/{token_id}", status_code=204)
def revoke_my_token(
    token_id: int,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> Response:
    from .auth import verify_session, revoke_token
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    with connect() as conn:
        owner = conn.execute(
            "SELECT human_id FROM tokens WHERE id = ?", (token_id,)
        ).fetchone()
    if owner is None or owner["human_id"] != principal["human_id"]:
        raise HTTPException(status_code=404, detail="token not found")

    revoke_token(token_id)
    return Response(status_code=204)
