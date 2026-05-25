from __future__ import annotations

import base64
import hashlib
import html
import json
import importlib
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.types import ASGIApp, Receive, Scope, Send

from . import mcp_server as mcp_server_module
from .auth import get_api_principal, set_mcp_principal, verify_token
from .db import connect, init_db, IntegrityError

mcp_server_module = importlib.reload(mcp_server_module)

_mcp_http = mcp_server_module.get_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    async with mcp_server_module.mcp.session_manager.run():
        yield


app = FastAPI(title="Let's", lifespan=lifespan)
DEFAULT_CLAUDE_MODEL = "claude-opus-4-7"
DEFAULT_CODEX_MODEL = "gpt-5.5"
SUPPORTED_AGENT_ROLES = {"claude", "codex", "cc-deepseek", "cc-doubao"}
PUBLIC_TOPIC_TITLE = "全员话题"


def _default_model_for_agent_role(role: str) -> str | None:
    if role == "claude":
        return DEFAULT_CLAUDE_MODEL
    if role == "codex":
        return DEFAULT_CODEX_MODEL
    return None


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
    "annotation",
]


class MessageCreate(BaseModel):
    topic_id: int
    type: MessageTypeStr
    actor_type: ActorType
    actor_id: int | None = None
    # Most messages need a body, but annotations carrying only a vote
    # (metadata.score = ±1) legitimately have no body. The handler enforces
    # the non-empty rule for everything except `annotation` so the v1
    # frontend ScoreRow / NodeFeedbackPanel calls succeed.
    body: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    ref_event_id: int | None = None
    addressed_to: str | None = None


class MessageEdit(BaseModel):
    body: str = Field(min_length=1)


class MessageDelete(BaseModel):
    reason: str | None = None


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


def _uploads_root() -> Path:
    return Path(os.environ.get("LETS_UPLOAD_DIR", "/data/lets-uploads")).expanduser().resolve()


def _max_attachment_bytes() -> int:
    raw = os.environ.get("LETS_MAX_ATTACHMENT_BYTES", str(25 * 1024 * 1024))
    try:
        return max(1, int(raw))
    except ValueError:
        return 25 * 1024 * 1024


def _safe_attachment_filename(filename: str | None) -> str:
    name = os.path.basename((filename or "").replace("\x00", "")).strip()
    return (name or "attachment")[:255]


def _attachment_storage_key(workspace_id: int | None, topic_id: int, attachment_id: int) -> str:
    workspace_part = str(workspace_id) if workspace_id is not None else "none"
    return f"workspaces/{workspace_part}/topics/{topic_id}/attachments/{attachment_id}/original"


def _attachment_path(storage_key: str) -> Path:
    root = _uploads_root()
    path = (root / storage_key).resolve()
    if path != root and root not in path.parents:
        raise HTTPException(status_code=400, detail="invalid attachment storage key")
    return path


def _attachment_out(row: dict) -> dict:
    out = dict(row)
    out["download_url"] = f"/api/attachments/{out['id']}/download"
    return out


class ArtifactUpdate(BaseModel):
    content_b64: str
    summary: str | None = None
    version_label: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    slug: str | None = None
    description: str | None = None
    repo_path: str | None = None


class TopicCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    mode: str = Field(default="exploratory")
    visibility: Literal["private", "public"] = "private"
    agent_intervention_mode: Literal["auto", "mentions", "silent"] = "auto"
    shared_context_mode: Literal["topic_only", "topic_with_files"] = "topic_with_files"


class TopicUpdate(BaseModel):
    workspace_id: int | None = None
    title: str | None = None
    agent_intervention_mode: Literal["auto", "mentions", "silent"] | None = None
    shared_context_mode: Literal["topic_only", "topic_with_files"] | None = None


class TopicParticipantCreate(BaseModel):
    participant_type: Literal["human", "agent"]
    participant_id: int
    role: Literal["owner", "member"] = "member"


class TopicShareCreate(BaseModel):
    reuse_existing: bool = True


def _ensure_onboarded(human_id: int) -> None:
    """Create '我的工作区' + public all-member topic on first login if absent."""
    from .workspaces import list_workspaces_for_human, create_workspace
    if list_workspaces_for_human(human_id):
        return
    ws = create_workspace(name="我的工作区", owner_human_id=human_id)
    with connect() as conn:
        _ensure_workspace_public_topic(conn, int(ws["id"]), human_id)


def _ensure_workspace_public_topic(conn, workspace_id: int, added_by_human_id: int | None) -> int:
    """Create/reuse the workspace public topic and sync workspace roster into it."""
    row = conn.execute(
        """
        SELECT id
        FROM topics
        WHERE workspace_id = ?
          AND visibility = 'public'
          AND deleted_at IS NULL
        ORDER BY created_at ASC, id ASC
        LIMIT 1
        """,
        (workspace_id,),
    ).fetchone()
    if row is None:
        base_slug = f"all-hands-{workspace_id}"
        slug = base_slug
        while conn.execute("SELECT 1 FROM topics WHERE slug = ?", (slug,)).fetchone():
            slug = f"{base_slug}-{secrets.token_hex(3)}"
        row = conn.execute(
            """
            INSERT INTO topics (slug, title, workspace_id, mode, visibility)
            VALUES (?, ?, ?, 'exploratory', 'public')
            RETURNING id
            """,
            (slug, PUBLIC_TOPIC_TITLE, workspace_id),
        ).fetchone()

    topic_id = int(row["id"])
    conn.execute(
        """
        INSERT INTO topic_participants
            (topic_id, participant_type, participant_id, role, added_by_human_id)
        SELECT ?, 'human', wm.human_id,
               CASE WHEN wm.role = 'owner' THEN 'owner' ELSE 'member' END,
               COALESCE(?, wm.human_id)
        FROM workspace_members wm
        WHERE wm.workspace_id = ?
        ON CONFLICT DO NOTHING
        RETURNING topic_id
        """,
        (topic_id, added_by_human_id, workspace_id),
    )
    conn.execute(
        """
        INSERT INTO topic_participants
            (topic_id, participant_type, participant_id, role, added_by_human_id)
        SELECT ?, 'agent', wam.agent_instance_id, 'member', wam.joined_by_human_id
        FROM workspace_agent_members wam
        JOIN agent_instances ai ON ai.id = wam.agent_instance_id
        WHERE wam.workspace_id = ?
          AND ai.deleted_at IS NULL
        ON CONFLICT DO NOTHING
        RETURNING topic_id
        """,
        (topic_id, workspace_id),
    )
    return topic_id


def _add_human_to_workspace_public_topics(
    conn,
    workspace_id: int,
    human_id: int,
    *,
    role: str = "member",
    added_by_human_id: int | None = None,
) -> None:
    _ensure_workspace_public_topic(conn, workspace_id, added_by_human_id)
    conn.execute(
        """
        INSERT INTO topic_participants
            (topic_id, participant_type, participant_id, role, added_by_human_id)
        SELECT id, 'human', ?, ?, COALESCE(?, ?)
        FROM topics
        WHERE workspace_id = ?
          AND visibility = 'public'
          AND deleted_at IS NULL
        ON CONFLICT (topic_id, participant_type, participant_id)
        DO UPDATE SET role = CASE
            WHEN topic_participants.role = 'owner' THEN 'owner'
            ELSE EXCLUDED.role
        END
        RETURNING topic_id
        """,
        (human_id, role, added_by_human_id, human_id, workspace_id),
    )


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
    """Serve the React SPA at root when it's been built.

    If ``frontend/dist/index.html`` (or the dir indicated by the
    ``LETS_FRONTEND_DIST`` env override) exists, serve it directly so the
    public home route can render before authentication.
    Otherwise fall back to the legacy v1 ``web/index.html`` debug panel
    so a rollback path remains for one release.
    """
    import pathlib as _pl

    dist_env = os.environ.get("LETS_FRONTEND_DIST")
    if dist_env:
        dist_root = _pl.Path(dist_env)
    else:
        dist_root = _pl.Path(__file__).parent.parent / "frontend" / "dist"

    index = dist_root / "index.html"
    if dist_root.is_dir() and index.exists():
        return FileResponse(index)
    return FileResponse("web/index.html")


@app.get("/mock")
def mock() -> FileResponse:
    return FileResponse("web/mock.html")


@app.get("/api/context")
def get_context() -> dict:
    return {
        "project": {
            "name": "Let's",
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


@app.get("/install")
def install_alias(request: Request) -> PlainTextResponse:
    """Short alias so the curl-bash one-liner can be `curl … /install | bash`,
    matching the Bun/Deno/uv convention."""
    return install_gateway_sh(request)


@app.get("/install/gateway.sh")
def install_gateway_sh(request: Request) -> PlainTextResponse:
    """One-line installer for the local Let's gateway.

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
  echo "Let's gateway requires Python 3.10+." >&2
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

cat <<MSG

Next, choose which local agent to connect:
  lets add claude     # if this computer has Claude Code
  lets add codex      # if this computer has Codex CLI
  lets add cc-deepseek # if this shell has a cc-deepseek command
  lets add cc-doubao   # if this shell has a cc-doubao command
MSG
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
                ai.model,
                ai.display_name,
                ai.paused_at,
                ai.deleted_at,
                h.id as human_id,
                h.name as human_name,
                MAX(t.last_used_at) as last_seen_at,
                CASE
                    WHEN MAX(t.last_used_at) IS NOT NULL
                     AND MAX(t.last_used_at) >= datetime('now', '-5 minutes')
                    THEN 1 ELSE 0
                END as is_online
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            LEFT JOIN tokens t ON t.agent_instance_id = ai.id
                              AND t.revoked_at IS NULL
            WHERE ai.deleted_at IS NULL
            GROUP BY ai.id, ar.name, ai.device_label, ai.model,
                     ai.display_name, ai.paused_at, ai.deleted_at, h.id, h.name
            ORDER BY is_online DESC, last_seen_at DESC, ai.id ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/agents/mine")
def list_my_agent_instances(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    human_id = int(principal["human_id"])
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                ai.id AS agent_instance_id,
                ar.name AS role,
                ai.device_label,
                ai.model,
                ai.display_name,
                ai.paused_at,
                ai.deleted_at,
                h.id AS human_id,
                h.name AS human_name,
                MAX(t.last_used_at) AS last_seen_at,
                CASE
                    WHEN MAX(t.last_used_at) IS NOT NULL
                     AND MAX(t.last_used_at) >= datetime('now', '-5 minutes')
                    THEN 1 ELSE 0
                END AS is_online,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'id', w.id,
                            'slug', w.slug,
                            'name', w.name,
                            'joined_at', wam.joined_at
                        )
                        ORDER BY wam.joined_at
                    ) FILTER (WHERE w.id IS NOT NULL),
                    '[]'::json
                ) AS workspaces
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            LEFT JOIN tokens t ON t.agent_instance_id = ai.id
                              AND t.revoked_at IS NULL
            LEFT JOIN workspace_agent_members wam ON wam.agent_instance_id = ai.id
            LEFT JOIN workspaces w ON w.id = wam.workspace_id
            WHERE ai.owner_human_id = ?
            GROUP BY ai.id, ar.name, ai.device_label, ai.model,
                     ai.display_name, ai.paused_at, ai.deleted_at, h.id, h.name
            ORDER BY ai.deleted_at ASC NULLS FIRST, is_online DESC, last_seen_at DESC, ai.id ASC
            """,
            (human_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def _require_agent_owner(conn, agent_instance_id: int, human_id: int) -> dict:
    row = conn.execute(
        """
        SELECT ai.id, ai.owner_human_id, ai.deleted_at
        FROM agent_instances ai
        WHERE ai.id = ?
        """,
        (agent_instance_id,),
    ).fetchone()
    if row is None or int(row["owner_human_id"]) != human_id:
        raise HTTPException(status_code=404, detail="agent not found")
    return dict(row)


def _remove_agent_instance_for_owner(conn, agent_instance_id: int, human_id: int) -> None:
    _require_agent_owner(conn, agent_instance_id, human_id)
    conn.execute(
        "UPDATE agent_instances SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (agent_instance_id,),
    )
    conn.execute(
        """
        UPDATE device_auth_flows
        SET token_id = NULL, token_value = NULL
        WHERE token_id IN (
            SELECT id FROM tokens
            WHERE agent_instance_id = ? AND human_id = ?
        )
        """,
        (agent_instance_id, human_id),
    )
    conn.execute(
        "DELETE FROM tokens WHERE agent_instance_id = ? AND human_id = ?",
        (agent_instance_id, human_id),
    )
    conn.execute(
        "DELETE FROM workspace_agent_members WHERE agent_instance_id = ?",
        (agent_instance_id,),
    )
    conn.execute(
        """
        DELETE FROM topic_participants
        WHERE participant_type = 'agent' AND participant_id = ?
        """,
        (agent_instance_id,),
    )


@app.post("/api/agents/{agent_instance_id}/pause")
def pause_agent_instance(
    agent_instance_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        _require_agent_owner(conn, agent_instance_id, human_id)
        conn.execute(
            "UPDATE agent_instances SET paused_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (agent_instance_id,),
        )
    return {"ok": True}


@app.post("/api/agents/{agent_instance_id}/resume")
def resume_agent_instance(
    agent_instance_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        _require_agent_owner(conn, agent_instance_id, human_id)
        conn.execute(
            "UPDATE agent_instances SET paused_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (agent_instance_id,),
        )
    return {"ok": True}


@app.delete("/api/agents/{agent_instance_id}")
def delete_agent_instance(
    agent_instance_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        _remove_agent_instance_for_owner(conn, agent_instance_id, human_id)
    return {"ok": True}


@app.get("/api/agents/me/memberships")
def list_current_agent_memberships(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    agent_id = principal.get("agent_instance_id")
    if agent_id is None:
        raise HTTPException(status_code=400, detail="agent token required")
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT w.id, w.slug, w.name, wam.joined_at
            FROM workspace_agent_members wam
            JOIN workspaces w ON w.id = wam.workspace_id
            JOIN agent_instances ai ON ai.id = wam.agent_instance_id
            WHERE wam.agent_instance_id = ?
              AND ai.paused_at IS NULL
              AND ai.deleted_at IS NULL
              AND w.deleted_at IS NULL
            ORDER BY wam.joined_at ASC
            """,
            (int(agent_id),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_agent_instance_detail(
    agent_instance_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.id AS agent_instance_id, ar.name AS role, ai.device_label,
                   ai.model, ai.display_name, ai.paused_at, ai.deleted_at,
                   ai.created_at, ai.owner_human_id AS human_id, h.name AS human_name,
                   MAX(t.last_used_at) AS last_seen_at
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            LEFT JOIN tokens t ON t.agent_instance_id = ai.id AND t.revoked_at IS NULL
            WHERE ai.id = ?
            GROUP BY ai.id, ar.name, h.id, h.name
            """,
            (agent_instance_id,),
        ).fetchone()
        if row is None or int(row["human_id"]) != human_id:
            raise HTTPException(status_code=404, detail="agent not found")
        workspaces = conn.execute(
            """
            SELECT w.id, w.slug, w.name, wam.joined_at
            FROM workspace_agent_members wam
            JOIN workspaces w ON w.id = wam.workspace_id
            WHERE wam.agent_instance_id = ?
            ORDER BY wam.joined_at ASC
            """,
            (agent_instance_id,),
        ).fetchall()
        stats = conn.execute(
            """
            SELECT COUNT(*) AS message_count,
                   COUNT(DISTINCT topic_id) AS topic_count,
                   COALESCE(SUM((metadata::jsonb #>> '{usage,input_tokens}')::bigint), 0) AS input_tokens,
                   COALESCE(SUM((metadata::jsonb #>> '{usage,output_tokens}')::bigint), 0) AS output_tokens
            FROM messages
            WHERE actor_type = 'agent' AND actor_id = ?
            """,
            (agent_instance_id,),
        ).fetchone()
        recent_topics = conn.execute(
            """
            SELECT t.id, t.slug, t.title, MAX(m.created_at) AS last_message_at,
                   COUNT(*) AS message_count
            FROM messages m
            JOIN topics t ON t.id = m.topic_id
            WHERE m.actor_type = 'agent' AND m.actor_id = ?
            GROUP BY t.id, t.slug, t.title
            ORDER BY last_message_at DESC
            LIMIT 8
            """,
            (agent_instance_id,),
        ).fetchall()
    out = dict(row)
    out["workspaces"] = [dict(r) for r in workspaces]
    out["stats"] = dict(stats) if stats else {}
    out["recent_topics"] = [dict(r) for r in recent_topics]
    out["usage_started_at"] = "2026-05-22"
    out["quota"] = None
    return out


@app.patch("/api/agent-instances/{agent_instance_id}")
def update_agent_instance(
    agent_instance_id: int,
    payload: AgentModelUpdate,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session

    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    model = payload.model.strip() if payload.model is not None else None
    display_name = payload.display_name.strip() if payload.display_name is not None else None
    if model is None and display_name is None:
        raise HTTPException(status_code=400, detail="nothing to update")
    if model is not None and not model:
        raise HTTPException(status_code=400, detail="model required")
    if model is not None and any(ch.isspace() for ch in model):
        raise HTTPException(status_code=400, detail="model cannot contain whitespace")
    if display_name is not None and not display_name:
        raise HTTPException(status_code=400, detail="display_name required")

    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model, ai.owner_human_id
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            WHERE ai.id = ?
            """,
            (agent_instance_id,),
        ).fetchone()
        if row is None or int(row["owner_human_id"]) != int(principal["human_id"]):
            raise HTTPException(status_code=404, detail="agent not found")
        updates: list[str] = []
        params: list[Any] = []
        if model is not None:
            updates.append("model = ?")
            params.append(model)
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        params.append(agent_instance_id)
        conn.execute(
            f"""
            UPDATE agent_instances
            SET {", ".join(updates)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            params,
        )
        updated = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model, ai.display_name
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            WHERE ai.id = ?
            """,
            (agent_instance_id,),
        ).fetchone()
    return dict(updated)


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
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            WHERE t.agent_instance_id IS NOT NULL
              AND t.revoked_at IS NULL
              AND ai.paused_at IS NULL
              AND ai.deleted_at IS NULL
              AND t.last_used_at IS NOT NULL
              AND t.last_used_at >= datetime('now', '-5 minutes')
            GROUP BY ai.id, ar.name, ai.device_label, h.name
            ORDER BY last_seen_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


app.add_api_route(
    "/api/agents/{agent_instance_id}",
    get_agent_instance_detail,
    methods=["GET"],
)


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


_GENERIC_TOPIC_TITLES = {"新话题", "主频道", "新对话", "general", "untitled", "new", "topic"}

_HEALTH_WAKE_RE = re.compile(
    r"("
    r"肚子疼|肚子痛|腹痛|胃痛|胃疼|头疼|头痛|发烧|发热|咳嗽|胸痛|胸闷|"
    r"拉肚子|腹泻|呕吐|恶心|过敏|皮疹|流血|出血|摔伤|扭伤|烫伤|"
    r"吃药|用药|止痛药|退烧药|药量|剂量|去医院|急诊|看医生"
    r")",
    re.IGNORECASE,
)


def _maybe_rename_topic_from_first_chat(topic_id: int, body: str) -> str | None:
    """If the topic is still on its auto-created generic name ("新话题" etc.)
    and the current message body is a real user chat, derive a short title
    from the body and persist it. Returns the new title if it was changed,
    else None."""
    if not body:
        return None
    from .topic_intent import summarize_topic_intent
    snippet = summarize_topic_intent(body)
    if not snippet:
        return None

    with connect() as conn:
        row = conn.execute(
            "SELECT title FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if row is None:
            return None
        current = (row["title"] or "").strip()
        if current.lower() not in _GENERIC_TOPIC_TITLES:
            return None
        conn.execute(
            "UPDATE topics SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (snippet, topic_id),
        )
    return snippet


def _topic_human_count_for_auto_address(topic_id: int, actor_id: int) -> int:
    """Return the human conversation size used for default agent addressing."""
    with connect() as conn:
        topic = conn.execute(
            "SELECT workspace_id FROM topics WHERE id = ?",
            (topic_id,),
        ).fetchone()
        if topic is None:
            return 0
        workspace_id = topic["workspace_id"]
        if workspace_id is not None:
            row = conn.execute(
                """
                SELECT COUNT(DISTINCT human_id) AS n
                FROM (
                    SELECT participant_id AS human_id
                    FROM topic_participants
                    WHERE topic_id = ? AND participant_type = 'human'
                    UNION
                    SELECT actor_id AS human_id
                    FROM messages
                    WHERE topic_id = ? AND actor_type = 'human' AND actor_id IS NOT NULL
                    UNION
                    SELECT ? AS human_id
                ) humans
                """,
                (topic_id, topic_id, actor_id),
            ).fetchone()
            return int(row["n"] or 0) if row else 0
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT human_id) AS n
            FROM (
                SELECT ? AS human_id
                UNION
                SELECT actor_id AS human_id
                FROM messages
                WHERE topic_id = ? AND actor_type = 'human'
            ) humans
            """,
            (actor_id, topic_id),
        ).fetchone()
        return int(row["n"] or 0) if row else 0


def _default_addressee_for(topic_id: int, actor_id: int | None) -> str | None:
    """Default-address only in the DM-like case: one human + one online agent.

    Multi-human topics keep human-to-human conversation primary. The gateway
    can still join proactively on stronger discussion signals.
    """
    if actor_id is None:
        return None
    if _topic_human_count_for_auto_address(topic_id, actor_id) != 1:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT ai.id) AS n, MIN(ai.id) AS agent_instance_id
            FROM tokens t
            JOIN agent_instances ai ON ai.id = t.agent_instance_id
            JOIN topic_participants tp
              ON tp.topic_id = ?
             AND tp.participant_type = 'agent'
             AND tp.participant_id = ai.id
            WHERE ai.owner_human_id = ?
              AND ai.paused_at IS NULL
              AND ai.deleted_at IS NULL
              AND t.revoked_at IS NULL
              AND t.last_used_at IS NOT NULL
              AND t.last_used_at >= datetime('now', '-5 minutes')
            """,
            (topic_id, actor_id),
        ).fetchone()
    if row is None or row["n"] != 1:
        return None
    return f"agent:{int(row['agent_instance_id'])}"


def _health_addressee_for(topic_id: int, actor_id: int | None, body: str) -> str | None:
    """Wake the only online workspace agent for obvious health/help requests.

    The normal rule keeps multi-human topics quiet. Health and medication
    questions are different: the first message should bring the agent in if
    there is a single unambiguous online helper in the current workspace.
    """
    if actor_id is None or not _HEALTH_WAKE_RE.search(body or ""):
        return None
    with connect() as conn:
        topic = conn.execute(
            "SELECT workspace_id FROM topics WHERE id = ?",
            (topic_id,),
        ).fetchone()
        workspace_id = topic["workspace_id"] if topic else None
        if workspace_id is not None:
            row = conn.execute(
                """
                SELECT COUNT(DISTINCT ai.id) AS n, MIN(ai.id) AS agent_instance_id
                FROM workspace_agent_members wam
                JOIN agent_instances ai ON ai.id = wam.agent_instance_id
                JOIN topic_participants tp
                  ON tp.topic_id = ?
                 AND tp.participant_type = 'agent'
                 AND tp.participant_id = ai.id
                JOIN tokens t ON t.agent_instance_id = ai.id
                WHERE wam.workspace_id = ?
                  AND ai.paused_at IS NULL
                  AND ai.deleted_at IS NULL
                  AND t.revoked_at IS NULL
                  AND t.last_used_at IS NOT NULL
                  AND t.last_used_at >= datetime('now', '-5 minutes')
                """,
                (topic_id, workspace_id),
            ).fetchone()
            if row is not None and row["n"] == 1:
                return f"agent:{int(row['agent_instance_id'])}"
    return _default_addressee_for(topic_id, actor_id)


@app.post("/api/messages")
async def post_message_endpoint(
    payload: MessageCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .messages import post_message
    from .sse import broadcaster

    _require_topic_actor(payload.topic_id, principal)

    # Body-required-unless-annotation: keep the old guarantee for all
    # "real" message types so legacy callers don't regress, but allow
    # empty body for annotations (vote-only annotations carry no text).
    if payload.type != "annotation" and not (payload.body or "").strip():
        raise HTTPException(
            status_code=422,
            detail=[{"type": "string_too_short", "loc": ["body", "body"],
                     "msg": "String should have at least 1 character",
                     "input": payload.body, "ctx": {"min_length": 1}}],
        )

    addressed_to = payload.addressed_to
    # Auto-address rule: in a one-human + one-online-agent topic, treat plain
    # chat like a DM so the agent replies one question at a time. Multi-human
    # topics keep human-to-human chat primary, except obvious health/help
    # requests where a single online workspace agent should join immediately.
    if (
        not addressed_to
        and payload.actor_type == "human"
        and payload.type == "chat"
    ):
        with connect() as conn:
            topic_settings = conn.execute(
                "SELECT agent_intervention_mode FROM topics WHERE id = ?",
                (payload.topic_id,),
            ).fetchone()
        intervention_mode = (
            topic_settings["agent_intervention_mode"] if topic_settings else "auto"
        )
        if intervention_mode == "auto":
            addressed_to = _health_addressee_for(
                payload.topic_id, payload.actor_id, payload.body
            ) or _default_addressee_for(payload.topic_id, payload.actor_id)

    # First-chat-renames-topic: replace the auto-created "新话题" with a
    # short snippet of the first human message so the sidebar + header
    # immediately reflect what the topic is actually about.
    if payload.actor_type == "human" and payload.type == "chat":
        _maybe_rename_topic_from_first_chat(payload.topic_id, payload.body)

    if payload.actor_type in ("human", "agent") and payload.actor_id is not None:
        with connect() as conn:
            _add_topic_participant(
                conn,
                payload.topic_id,
                payload.actor_type,
                int(payload.actor_id),
                role="member",
                added_by_human_id=int(principal["human_id"]) if principal.get("human_id") else None,
            )

    message_id = post_message(
        topic_id=payload.topic_id,
        type=payload.type,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        body=payload.body,
        metadata=payload.metadata,
        ref_event_id=payload.ref_event_id,
        addressed_to=addressed_to,
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


@app.patch("/api/messages/{message_id}")
def edit_message_endpoint(
    message_id: int,
    payload: MessageEdit,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .messages import edit_message

    ctx = _message_action_context(message_id, principal)
    if ctx["deleted_at"] is not None:
        raise HTTPException(status_code=409, detail="message is deleted")
    if not ctx["can_edit"]:
        raise HTTPException(status_code=403, detail="cannot edit this message")
    if ctx["type"] in {"system", "status"}:
        raise HTTPException(status_code=400, detail="message type cannot be edited")

    message = edit_message(
        message_id,
        payload.body.strip(),
        edited_by_human_id=int(principal["human_id"]),
    )
    message["edited_after_agent_read"] = bool(ctx["read_by_agent"])
    return message


@app.post("/api/messages/{message_id}/retract")
def retract_message_endpoint(
    message_id: int,
    payload: MessageDelete | None = None,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .messages import mark_message_deleted

    ctx = _message_action_context(message_id, principal)
    if ctx["deleted_at"] is not None:
        raise HTTPException(status_code=409, detail="message is already deleted")
    if not ctx["is_own"]:
        raise HTTPException(status_code=403, detail="cannot retract this message")
    with connect() as conn:
        row = conn.execute(
            "SELECT created_at >= datetime('now', '-5 minutes') AS ok FROM messages WHERE id = ?",
            (message_id,),
        ).fetchone()
    if row is None or not row["ok"]:
        raise HTTPException(status_code=409, detail="retract window expired")
    return mark_message_deleted(
        message_id,
        deleted_by_human_id=int(principal["human_id"]),
        kind="retracted",
        reason=(payload.reason if payload else None),
    )


@app.delete("/api/messages/{message_id}")
def delete_message_endpoint(
    message_id: int,
    payload: MessageDelete | None = None,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .messages import mark_message_deleted

    ctx = _message_action_context(message_id, principal)
    if not ctx["can_delete"]:
        raise HTTPException(status_code=403, detail="cannot delete this message")
    return mark_message_deleted(
        message_id,
        deleted_by_human_id=int(principal["human_id"]),
        kind="deleted",
        reason=(payload.reason if payload else None),
    )


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

    _require_topic_member(topic_id, int(principal["human_id"]))

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
    _require_topic_member(topic_id, int(principal["human_id"]))
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

    _require_topic_member(topic_id, int(principal["human_id"]))

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

    _require_topic_member(topic_id, int(principal["human_id"]))

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
        # Create the new topic in the same workspace
        with connect() as conn:
            src_topic = conn.execute(
                "SELECT workspace_id FROM topics WHERE id = ?", (nudge_row["topic_id"],)
            ).fetchone()
            workspace_id = src_topic["workspace_id"] if src_topic else None
            # Generate a slug from the title (lower, replace ws with -)
            import re, time
            slug_base = re.sub(r"\s+", "-", payload.spinoff_title.strip().lower())[:60]
            slug = f"{slug_base}-{int(time.time())}"
            cur = conn.execute(
                "INSERT INTO topics (slug, title, workspace_id) VALUES (?, ?, ?)",
                (slug, payload.spinoff_title, workspace_id),
            )
            new_topic_id = int(cur.lastrowid)
            _add_topic_participant(
                conn,
                new_topic_id,
                "human",
                int(principal["human_id"]),
                role="owner",
                added_by_human_id=int(principal["human_id"]),
            )
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
        from .workspaces import list_workspaces_for_human, create_workspace as _cw
        _idme_mine = list_workspaces_for_human(human_id)
        if _idme_mine:
            _idme_ws_id = _idme_mine[0]["id"]
        else:
            _idme_ws = _cw(name="我的工作区", owner_human_id=human_id)
            _idme_ws_id = _idme_ws["id"]
        try:
            agent_instance_id = ensure_agent_instance(
                role=x_lets_agent_role,
                human_id=human_id,
                device_label=x_lets_device,
                workspace_id=int(_idme_ws_id),
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

    _require_topic_member(payload.topic_id, int(principal["human_id"]))

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


@app.post("/api/topics/{topic_id}/attachments")
async def upload_topic_attachment(
    topic_id: int,
    request: Request,
    filename: str = Query(default="attachment"),
    kind: Literal["file", "image"] | None = Query(default=None),
    message_id: int | None = Query(default=None),
    content_type: str | None = Header(default=None, alias="Content-Type"),
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    workspace_id = _require_topic_member(topic_id, human_id)
    workspace_ref = workspace_id if workspace_id else None
    if message_id is not None:
        with connect() as conn:
            msg = conn.execute(
                "SELECT 1 FROM messages WHERE id = ? AND topic_id = ?",
                (message_id, topic_id),
            ).fetchone()
        if msg is None:
            raise HTTPException(status_code=400, detail="message does not belong to topic")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="empty attachment")
    max_bytes = _max_attachment_bytes()
    if len(body) > max_bytes:
        raise HTTPException(status_code=413, detail=f"attachment exceeds {max_bytes} bytes")

    mime_type = (content_type or "application/octet-stream").split(";", 1)[0].strip()
    inferred_kind = "image" if mime_type.startswith("image/") else "file"
    attachment_kind = kind or inferred_kind
    safe_name = _safe_attachment_filename(filename)
    digest = hashlib.sha256(body).hexdigest()

    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO attachments
                (workspace_id, topic_id, message_id, uploaded_by_human_id, kind,
                 filename, mime_type, byte_size, sha256, storage_backend, storage_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (
                workspace_ref,
                topic_id,
                message_id,
                human_id,
                attachment_kind,
                safe_name,
                mime_type,
                len(body),
                digest,
                "local_volume",
                "",
            ),
        ).fetchone()
        attachment_id = int(row["id"])
        storage_key = _attachment_storage_key(workspace_ref, topic_id, attachment_id)
        conn.execute(
            "UPDATE attachments SET storage_key = ? WHERE id = ?",
            (storage_key, attachment_id),
        )
        row = dict(row)
        row["storage_key"] = storage_key

    try:
        path = _attachment_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    except OSError as exc:
        with connect() as conn:
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        raise HTTPException(status_code=500, detail=f"failed to store attachment: {exc}") from exc

    return _attachment_out(row)


@app.get("/api/topics/{topic_id}/attachments")
def list_topic_attachments(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    _require_topic_member(topic_id, int(principal["human_id"]))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM attachments
            WHERE topic_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (topic_id,),
        ).fetchall()
    return [_attachment_out(dict(row)) for row in rows]


@app.get("/api/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    principal: dict = Depends(get_api_principal),
) -> FileResponse:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM attachments WHERE id = ?",
            (attachment_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="attachment not found")
    data = dict(row)
    _require_topic_member(int(data["topic_id"]), int(principal["human_id"]))
    path = _attachment_path(str(data["storage_key"]))
    if not path.exists():
        raise HTTPException(status_code=404, detail="attachment file missing")
    return FileResponse(
        path,
        media_type=data.get("mime_type") or "application/octet-stream",
        filename=str(data["filename"]),
    )


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


@app.get("/api/workspaces")
def list_workspaces(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import list_workspaces_for_human
    return list_workspaces_for_human(int(principal["human_id"]))


@app.post("/api/workspaces")
def create_workspace_endpoint(
    payload: WorkspaceCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import create_workspace
    human_id = int(principal["human_id"])
    ws = create_workspace(name=payload.name, owner_human_id=human_id)
    with connect() as conn:
        _ensure_workspace_public_topic(conn, int(ws["id"]), human_id)
    ws["my_role"] = "owner"
    return ws


@app.get("/api/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_member
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        row = conn.execute(
            "SELECT id, slug, name, description, owner_human_id, is_private, "
            "created_at, updated_at FROM workspaces WHERE id = ? AND deleted_at IS NULL",
            (workspace_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    return dict(row)


@app.patch("/api/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        conn.execute(
            "UPDATE workspaces SET name = ?, updated_at = NOW() WHERE id = ?",
            (payload.name, workspace_id),
        )
        row = conn.execute(
            "SELECT id, slug, name, description FROM workspaces WHERE id = ?",
            (workspace_id,),
        ).fetchone()
    return dict(row)


@app.delete("/api/workspaces/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        my_count = conn.execute(
            """
            SELECT COUNT(*) AS n FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE wm.human_id = ? AND w.deleted_at IS NULL
            """,
            (principal["human_id"],),
        ).fetchone()["n"]
        if int(my_count) <= 1:
            raise HTTPException(
                status_code=400,
                detail="cannot delete your last workspace",
            )
        conn.execute(
            "UPDATE workspaces SET deleted_at = NOW() WHERE id = ?",
            (workspace_id,),
        )
    return {"ok": True}


@app.get("/api/workspaces/{workspace_id}/members")
def list_workspace_members(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import require_workspace_member
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        human_rows = conn.execute(
            """
            SELECT h.id, h.name, h.email, h.avatar_url, wm.role, wm.joined_at,
                   MAX(s.last_used_at) AS last_seen_at,
                   CASE
                     WHEN MAX(s.last_used_at) IS NOT NULL
                      AND MAX(s.last_used_at) >= datetime('now', '-5 minutes')
                     THEN 1 ELSE 0
                   END AS is_online
            FROM workspace_members wm
            JOIN humans h ON h.id = wm.human_id
            LEFT JOIN sessions s ON s.human_id = h.id AND s.revoked_at IS NULL
            WHERE wm.workspace_id = ?
            GROUP BY h.id, h.name, h.email, h.avatar_url, wm.role, wm.joined_at
            ORDER BY wm.joined_at ASC
            """,
            (workspace_id,),
        ).fetchall()
        agent_rows = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model,
                   ai.display_name, ai.paused_at, ai.deleted_at,
                   ai.owner_human_id AS owner_human_id,
                   h.name AS owner_name,
                   wam.joined_at,
                   MAX(t.last_used_at) AS last_seen_at,
                   CASE
                     WHEN MAX(t.last_used_at) IS NOT NULL
                      AND MAX(t.last_used_at) >= datetime('now', '-5 minutes')
                     THEN 1 ELSE 0
                   END AS is_online
            FROM workspace_agent_members wam
            JOIN agent_instances ai ON ai.id = wam.agent_instance_id
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            LEFT JOIN tokens t ON t.agent_instance_id = ai.id AND t.revoked_at IS NULL
            WHERE wam.workspace_id = ?
              AND ai.deleted_at IS NULL
            GROUP BY ai.id, ar.name, ai.device_label, ai.model,
                     ai.display_name, ai.paused_at, ai.deleted_at,
                     ai.owner_human_id, h.name, wam.joined_at
            ORDER BY wam.joined_at ASC
            """,
            (workspace_id,),
        ).fetchall()
    humans = [{**dict(r), "kind": "human"} for r in human_rows]
    agents = [{**dict(r), "kind": "agent"} for r in agent_rows]
    return humans + agents


@app.delete("/api/workspaces/{workspace_id}/agent-members/{agent_instance_id}")
def remove_workspace_agent_member(
    workspace_id: int,
    agent_instance_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.owner_human_id, wm.role AS caller_workspace_role
            FROM agent_instances ai
            LEFT JOIN workspace_members wm
              ON wm.workspace_id = ? AND wm.human_id = ?
            WHERE ai.id = ?
            """,
            (workspace_id, human_id, agent_instance_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="agent not found")
        if int(row["owner_human_id"]) != human_id and row["caller_workspace_role"] != "owner":
            raise HTTPException(status_code=403, detail="not allowed")
        conn.execute(
            """
            DELETE FROM workspace_agent_members
            WHERE workspace_id = ? AND agent_instance_id = ?
            """,
            (workspace_id, agent_instance_id),
        )
        conn.execute(
            """
            DELETE FROM topic_participants
            WHERE participant_type = 'agent'
              AND participant_id = ?
              AND topic_id IN (
                SELECT id FROM topics
                WHERE workspace_id = ?
              )
            """,
            (agent_instance_id, workspace_id),
        )
    return {"ok": True}


@app.delete("/api/workspaces/{workspace_id}/members/{human_id}")
def remove_workspace_member(
    workspace_id: int,
    human_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        row = conn.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = ? AND human_id = ?",
            (workspace_id, human_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="member not found")
        if row["role"] == "owner":
            raise HTTPException(status_code=400, detail="cannot remove owner")
        conn.execute(
            "DELETE FROM workspace_members WHERE workspace_id = ? AND human_id = ?",
            (workspace_id, human_id),
        )
        conn.execute(
            """
            DELETE FROM topic_participants
            WHERE participant_type = 'human'
              AND participant_id = ?
              AND topic_id IN (
                SELECT id FROM topics
                WHERE workspace_id = ?
              )
            """,
            (human_id, workspace_id),
        )
    return {"ok": True}


@app.post("/api/workspaces/{workspace_id}/invites")
def create_workspace_invite(
    workspace_id: int,
    request: Request,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner, generate_invite_token
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    token = generate_invite_token()
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO workspace_invites (workspace_id, token, created_by_human_id)
            VALUES (?, ?, ?)
            RETURNING id, token, created_at
            """,
            (workspace_id, token, principal["human_id"]),
        ).fetchone()
    base_url = _public_base_url(request)
    return {
        "id": int(row["id"]),
        "token": row["token"],
        "join_url": f"{base_url}/join/{row['token']}",
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.get("/api/workspaces/{workspace_id}/invites")
def list_workspace_invites(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, token, created_by_human_id, used_count,
                   expires_at, max_uses, created_at
            FROM workspace_invites
            WHERE workspace_id = ?
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            """,
            (workspace_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.delete("/api/invites/{invite_id}")
def revoke_invite(
    invite_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    with connect() as conn:
        inv = conn.execute(
            "SELECT workspace_id FROM workspace_invites WHERE id = ?",
            (invite_id,),
        ).fetchone()
        if inv is None:
            raise HTTPException(status_code=404, detail="invite not found")
    require_workspace_owner(int(inv["workspace_id"]), int(principal["human_id"]))
    with connect() as conn:
        conn.execute(
            "UPDATE workspace_invites SET revoked_at = NOW() WHERE id = ?",
            (invite_id,),
        )
    return {"ok": True}


class GuestInviteAccept(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class CurrentUserUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=40)


def _unique_human_name(
    conn,
    display_name: str,
    *,
    exclude_human_id: int | None = None,
) -> str:
    base = " ".join(display_name.strip().split()) or "Guest"
    candidate = base
    i = 2
    while True:
        row = conn.execute(
            "SELECT id FROM humans WHERE name = ?",
            (candidate,),
        ).fetchone()
        if row is None or (
            exclude_human_id is not None and int(row["id"]) == exclude_human_id
        ):
            return candidate
        candidate = f"{base} ({i})"
        i += 1


@app.get("/join/{token}", response_model=None)
def join_by_token(token: str) -> RedirectResponse | FileResponse:
    """Magic-link landing.

    Serve the SPA without redirecting. `JoinTokenPage` needs the browser URL to
    remain `/join/:token`; redirecting through `/app` loses the token and sends
    signed-out invitees to the ordinary login page instead of guest join.
    """
    import pathlib as _pl

    dist_env = os.environ.get("LETS_FRONTEND_DIST")
    dist_root = (
        _pl.Path(dist_env)
        if dist_env
        else _pl.Path(__file__).parent.parent / "frontend" / "dist"
    )
    index = dist_root / "index.html"
    if index.exists():
        return FileResponse(index)
    return FileResponse("web/index.html")


@app.post("/api/invites/{token}/accept")
def accept_invite(
    token: str,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        inv = conn.execute(
            """
            SELECT id, workspace_id, max_uses, used_count, expires_at
            FROM workspace_invites
            WHERE token = ?
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
              AND (max_uses IS NULL OR used_count < max_uses)
            """,
            (token,),
        ).fetchone()
        if inv is None:
            raise HTTPException(status_code=404, detail="invite not valid")
        already = conn.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = ? AND human_id = ?
            """,
            (inv["workspace_id"], human_id),
        ).fetchone()
        if already is None:
            conn.execute(
                """
                INSERT INTO workspace_members (workspace_id, human_id, role)
                VALUES (?, ?, 'member') RETURNING workspace_id
                """,
                (inv["workspace_id"], human_id),
            )
            conn.execute(
                """
                UPDATE workspace_invites
                SET used_count = used_count + 1
                WHERE id = ?
                """,
                (inv["id"],),
            )
        _add_human_to_workspace_public_topics(
            conn,
            int(inv["workspace_id"]),
            human_id,
            role="member",
            added_by_human_id=human_id,
        )
    return {"workspace_id": int(inv["workspace_id"])}


@app.post("/api/invites/{token}/accept-guest")
def accept_invite_as_guest(token: str, payload: GuestInviteAccept) -> JSONResponse:
    from .auth import issue_session

    with connect() as conn:
        inv = conn.execute(
            """
            SELECT id, workspace_id, max_uses, used_count, expires_at
            FROM workspace_invites
            WHERE token = ?
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
              AND (max_uses IS NULL OR used_count < max_uses)
            """,
            (token,),
        ).fetchone()
        if inv is None:
            raise HTTPException(status_code=404, detail="invite not valid")

        guest_name = _unique_human_name(conn, payload.name)
        cursor = conn.execute(
            """
            INSERT INTO humans (name, is_guest)
            VALUES (?, TRUE)
            """,
            (guest_name,),
        )
        human_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, human_id, role)
            VALUES (?, ?, 'member')
            RETURNING workspace_id
            """,
            (inv["workspace_id"], human_id),
        )
        conn.execute(
            """
            UPDATE workspace_invites
            SET used_count = used_count + 1
            WHERE id = ?
            """,
            (inv["id"],),
        )
        _add_human_to_workspace_public_topics(
            conn,
            int(inv["workspace_id"]),
            human_id,
            role="member",
            added_by_human_id=human_id,
        )

    session_value = issue_session(human_id)
    res = JSONResponse(
        {
            "workspace_id": int(inv["workspace_id"]),
            "human": {"id": human_id, "name": guest_name, "is_guest": True},
        }
    )
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


@app.get("/api/workspaces/{workspace_id}/topics")
def list_topics_in_workspace(
    workspace_id: int,
    archived: bool = False,
    scope: Literal["mine", "all"] = "all",
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import require_workspace_member
    human_id = int(principal["human_id"])
    require_workspace_member(workspace_id, human_id)
    with connect() as conn:
        role_row = conn.execute(
            """
            SELECT role FROM workspace_members
            WHERE workspace_id = ? AND human_id = ?
            """,
            (workspace_id, human_id),
        ).fetchone()
    can_use_all_scope = role_row is not None and role_row["role"] == "owner" and scope == "all"
    scope_clause = ""
    params: list[object] = [workspace_id]
    if not can_use_all_scope:
        scope_clause = """
              AND (
                topics.visibility = 'public'
                OR EXISTS (
                SELECT 1
                FROM topic_participants tp
                WHERE tp.topic_id = topics.id
                  AND tp.participant_type = 'human'
                  AND tp.participant_id = ?
                )
              )
        """
        params.append(human_id)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, slug, title, workspace_id, mode, visibility,
                   agent_intervention_mode, shared_context_mode,
                   archived_at, created_at, updated_at
            FROM topics
            WHERE workspace_id = ?
              AND archived_at IS {archived_predicate}
              AND deleted_at IS NULL
              {scope_clause}
            ORDER BY updated_at DESC
            """.format(
                archived_predicate="NOT NULL" if archived else "NULL",
                scope_clause=scope_clause,
            ),
            params,
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/workspaces/{workspace_id}/topics")
def create_topic_in_workspace(
    workspace_id: int,
    payload: TopicCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_member
    if principal.get("is_guest"):
        raise HTTPException(status_code=403, detail="guest users cannot create topics")
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO topics
                    (slug, title, workspace_id, mode, visibility,
                     agent_intervention_mode, shared_context_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id, slug, title, workspace_id, mode, visibility,
                          agent_intervention_mode, shared_context_mode,
                          created_at, updated_at
                """,
                (
                    payload.slug,
                    payload.title,
                    workspace_id,
                    payload.mode,
                    payload.visibility,
                    payload.agent_intervention_mode,
                    payload.shared_context_mode,
                ),
            ).fetchone()
            _add_topic_participant(
                conn,
                int(row["id"]),
                "human",
                int(principal["human_id"]),
                role="owner",
                added_by_human_id=int(principal["human_id"]),
            )
        except IntegrityError as e:
            if "topics_slug_key" in str(e).lower() or "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail=f"slug in use: {payload.slug}")
            raise
    return dict(row)


def _require_topic_member(topic_id: int, human_id: int) -> int:
    """Return workspace_id; raise 403 if caller cannot access this topic."""
    from .workspaces import require_workspace_member
    with connect() as conn:
        row = conn.execute(
            """
            SELECT workspace_id, visibility
            FROM topics
            WHERE id = ? AND deleted_at IS NULL
            """,
            (topic_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    if row["workspace_id"] is None:
        return 0
    workspace_id = int(row["workspace_id"])
    require_workspace_member(workspace_id, human_id)
    if row["visibility"] == "public":
        return workspace_id
    with connect() as conn:
        workspace_role = conn.execute(
            """
            SELECT role FROM workspace_members
            WHERE workspace_id = ? AND human_id = ?
            """,
            (workspace_id, human_id),
        ).fetchone()
        if workspace_role is not None and workspace_role["role"] == "owner":
            return workspace_id
        participant = conn.execute(
            """
            SELECT 1 FROM topic_participants
            WHERE topic_id = ?
              AND participant_type = 'human'
              AND participant_id = ?
            """,
            (topic_id, human_id),
        ).fetchone()
    if participant is None:
        raise HTTPException(status_code=403, detail="not a topic participant")
    return workspace_id


def _topic_management_context(conn, topic_id: int, human_id: int) -> dict:
    row = conn.execute(
        """
        SELECT t.workspace_id,
               t.visibility,
               wm.role AS workspace_role,
               tp.role AS topic_role
        FROM topics t
        LEFT JOIN workspace_members wm
          ON wm.workspace_id = t.workspace_id
         AND wm.human_id = ?
        LEFT JOIN topic_participants tp
          ON tp.topic_id = t.id
         AND tp.participant_type = 'human'
         AND tp.participant_id = ?
        WHERE t.id = ? AND t.deleted_at IS NULL
        """,
        (human_id, human_id, topic_id),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    if row["workspace_id"] is not None and row["workspace_role"] is None:
        raise HTTPException(status_code=403, detail="not a workspace member")

    is_workspace_owner = row["workspace_role"] == "owner"
    is_topic_owner = row["topic_role"] == "owner"
    return {
        "workspace_id": int(row["workspace_id"]) if row["workspace_id"] is not None else 0,
        "visibility": row["visibility"],
        "can_manage": is_workspace_owner or is_topic_owner,
        "is_workspace_owner": is_workspace_owner,
        "is_topic_owner": is_topic_owner,
    }


def _require_topic_manager(topic_id: int, human_id: int) -> tuple[int, str]:
    with connect() as conn:
        context = _topic_management_context(conn, topic_id, human_id)
    if not context["can_manage"]:
        raise HTTPException(status_code=403, detail="not a topic manager")
    return int(context["workspace_id"]), str(context["visibility"])


def _require_workspace_actor(workspace_id: int, principal: dict) -> None:
    from .workspaces import require_workspace_member

    agent_id = principal.get("agent_instance_id")
    if agent_id is None:
        require_workspace_member(workspace_id, int(principal["human_id"]))
        return

    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.paused_at, ai.deleted_at
            FROM workspace_agent_members wam
            JOIN agent_instances ai ON ai.id = wam.agent_instance_id
            WHERE wam.workspace_id = ? AND wam.agent_instance_id = ?
            """,
            (workspace_id, int(agent_id)),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=403, detail="not a workspace actor")
    if row["paused_at"] is not None:
        raise HTTPException(status_code=401, detail="agent is paused")
    if row["deleted_at"] is not None:
        raise HTTPException(status_code=401, detail="agent is deleted")


def _participant_exists(conn, topic_id: int, participant_type: str, participant_id: int) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM topic_participants
        WHERE topic_id = ? AND participant_type = ? AND participant_id = ?
        """,
        (topic_id, participant_type, participant_id),
    ).fetchone()
    return row is not None


def _add_topic_participant(
    conn,
    topic_id: int,
    participant_type: str,
    participant_id: int,
    *,
    role: str = "member",
    added_by_human_id: int | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO topic_participants
            (topic_id, participant_type, participant_id, role, added_by_human_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (topic_id, participant_type, participant_id)
        DO UPDATE SET role = CASE
            WHEN topic_participants.role = 'owner' THEN 'owner'
            ELSE EXCLUDED.role
        END
        RETURNING topic_id
        """,
        (topic_id, participant_type, participant_id, role, added_by_human_id),
    )


def _validate_topic_participant(conn, workspace_id: int | None, payload: TopicParticipantCreate) -> None:
    if payload.participant_type == "human":
        if workspace_id is None:
            row = conn.execute("SELECT 1 FROM humans WHERE id = ?", (payload.participant_id,)).fetchone()
        else:
            row = conn.execute(
                """
                SELECT 1
                FROM workspace_members
                WHERE workspace_id = ? AND human_id = ?
                """,
                (workspace_id, payload.participant_id),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=400, detail="human is not in this workspace")
        return

    if workspace_id is None:
        row = conn.execute(
            "SELECT 1 FROM agent_instances WHERE id = ? AND deleted_at IS NULL",
            (payload.participant_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT 1
            FROM workspace_agent_members wam
            JOIN agent_instances ai ON ai.id = wam.agent_instance_id
            WHERE wam.workspace_id = ?
              AND wam.agent_instance_id = ?
              AND ai.deleted_at IS NULL
            """,
            (workspace_id, payload.participant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=400, detail="agent is not in this workspace")


def _require_topic_actor(topic_id: int, principal: dict) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT workspace_id, visibility
            FROM topics
            WHERE id = ? AND deleted_at IS NULL
            """,
            (topic_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    if row["workspace_id"] is None:
        return 0
    workspace_id = int(row["workspace_id"])
    agent_id = principal.get("agent_instance_id")
    if agent_id is None:
        return _require_topic_member(topic_id, int(principal["human_id"]))
    _require_workspace_actor(workspace_id, principal)
    with connect() as conn:
        if not _participant_exists(conn, topic_id, "agent", int(agent_id)):
            raise HTTPException(status_code=403, detail="agent is not a topic participant")
    return workspace_id


def _message_action_context(message_id: int, principal: dict) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        row = conn.execute(
            """
            SELECT m.*,
                   t.workspace_id,
                   wm.role AS workspace_role,
                   ai.owner_human_id AS agent_owner_human_id,
                   EXISTS (
                       SELECT 1 FROM messages later
                       WHERE later.topic_id = m.topic_id
                         AND later.actor_type = 'agent'
                         AND later.id > m.id
                         AND later.deleted_at IS NULL
                         AND jsonb_typeof(later.metadata::jsonb -> 'cites') = 'array'
                         AND later.metadata::jsonb -> 'cites' @> jsonb_build_array(m.id)
                   ) AS read_by_agent
            FROM messages m
            JOIN topics t ON t.id = m.topic_id
            LEFT JOIN workspace_members wm
              ON wm.workspace_id = t.workspace_id
             AND wm.human_id = ?
            LEFT JOIN agent_instances ai
              ON m.actor_type = 'agent'
             AND ai.id = m.actor_id
            WHERE m.id = ? AND t.deleted_at IS NULL
            """,
            (human_id, message_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="message not found")
    topic_id = int(row["topic_id"])
    _require_topic_member(topic_id, human_id)

    agent_id = principal.get("agent_instance_id")
    is_own = (
        (row["actor_type"] == "human" and row["actor_id"] is not None and int(row["actor_id"]) == human_id)
        or (
            row["actor_type"] == "agent"
            and agent_id is not None
            and row["actor_id"] is not None
            and int(row["actor_id"]) == int(agent_id)
        )
    )
    is_workspace_owner = row["workspace_role"] == "owner"
    is_agent_owner = (
        row["agent_owner_human_id"] is not None
        and int(row["agent_owner_human_id"]) == human_id
    )
    out = dict(row)
    out["is_own"] = is_own
    out["can_delete"] = is_own or is_workspace_owner or is_agent_owner
    out["can_edit"] = is_own and row["actor_type"] != "system"
    return out


@app.get("/api/topics/{topic_id}")
def get_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .topics import get_topic_by_id
    _require_topic_member(topic_id, int(principal["human_id"]))
    t = get_topic_by_id(topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="topic not found")
    return t


@app.get("/api/topics/{topic_id}/spec", response_class=PlainTextResponse)
def get_topic_spec(
    topic_id: int,
    limit: int = 500,
    principal: dict = Depends(get_api_principal),
) -> PlainTextResponse:
    """Render the topic's blackboard as a handoff spec (markdown).

    Same projection as `lets spec <id>` so CLI and UI always agree. The
    optional `--polish` / `--self-test` LLM steps live in the CLI only
    (they shell out to the user's local `claude` binary); we don't run
    them server-side so deployments stay free of API-key configuration.
    """
    from .messages import topic_stream
    from .topics import get_topic_by_id
    from .spec import render_spec_markdown

    _require_topic_member(topic_id, int(principal["human_id"]))
    if not get_topic_by_id(topic_id):
        raise HTTPException(status_code=404, detail="topic not found")
    msgs = topic_stream(topic_id, limit=limit, order="asc")
    body = render_spec_markdown(topic_id, msgs)
    return PlainTextResponse(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="topic-{topic_id}-spec.md"',
        },
    )


def _render_topic_spec(topic_id: int, limit: int = 500) -> str:
    from .messages import topic_stream
    from .spec import render_spec_markdown

    msgs = topic_stream(topic_id, limit=limit, order="asc")
    return render_spec_markdown(topic_id, msgs)


@app.post("/api/topics/{topic_id}/share")
def create_topic_share_link(
    topic_id: int,
    request: Request,
    payload: TopicShareCreate | None = None,
    principal: dict = Depends(get_api_principal),
) -> dict:
    """Create or reuse a public read-only design-spec link for this topic."""
    from .topics import get_topic_by_id

    human_id = int(principal["human_id"])
    _require_topic_member(topic_id, human_id)
    if not get_topic_by_id(topic_id):
        raise HTTPException(status_code=404, detail="topic not found")

    reuse = payload.reuse_existing if payload is not None else True
    with connect() as conn:
        row = None
        if reuse:
            row = conn.execute(
                """
                SELECT token
                FROM topic_share_links
                WHERE topic_id = ? AND revoked_at IS NULL
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (topic_id,),
            ).fetchone()
        if row is None:
            token = secrets.token_urlsafe(24)
            row = conn.execute(
                """
                INSERT INTO topic_share_links (topic_id, token, created_by_human_id)
                VALUES (?, ?, ?)
                RETURNING token
                """,
                (topic_id, token, human_id),
            ).fetchone()
    base_url = _public_base_url(request)
    token = row["token"]
    return {
        "token": token,
        "url": f"{base_url}/s/{token}",
        "markdown_url": f"{base_url}/s/{token}.md",
    }


def _topic_id_for_share_token(token: str) -> int:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT topic_id
            FROM topic_share_links
            WHERE token = ? AND revoked_at IS NULL
            """,
            (token,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="share link not found")
    return int(row["topic_id"])


@app.get("/s/{token}.md", response_class=PlainTextResponse)
def read_shared_topic_markdown(token: str) -> PlainTextResponse:
    topic_id = _topic_id_for_share_token(token)
    body = _render_topic_spec(topic_id)
    return PlainTextResponse(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'inline; filename="topic-{topic_id}-design.md"',
        },
    )


@app.get("/s/{token}", response_class=HTMLResponse)
def read_shared_topic_page(token: str) -> HTMLResponse:
    topic_id = _topic_id_for_share_token(token)
    body = _render_topic_spec(topic_id)
    escaped = html.escape(body)
    markdown_url = f"/s/{html.escape(token)}.md"
    return HTMLResponse(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Topic #{topic_id} design spec</title>
  <style>
    body {{ margin: 0; background: #f8f5ef; color: #24211d; font-family: ui-serif, Georgia, serif; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 40px 24px 80px; }}
    header {{ display: flex; justify-content: space-between; gap: 16px; align-items: baseline; border-bottom: 1px solid #ddd4c5; padding-bottom: 16px; margin-bottom: 28px; }}
    h1 {{ font-size: 28px; margin: 0; }}
    a {{ color: #6f3328; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; font: 15px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace; background: #fffdf8; border: 1px solid #ddd4c5; border-radius: 6px; padding: 20px; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Design Spec</h1>
      <a href="{markdown_url}">下载 Markdown</a>
    </header>
    <pre>{escaped}</pre>
  </main>
</body>
</html>"""
    )


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
    _require_topic_member(topic_id, int(principal["human_id"]))

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
    _require_topic_member(topic_id, int(principal["human_id"]))
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
    """Return explicit topic participants, with message actors as legacy fallback."""
    human_id = int(principal["human_id"])
    _require_topic_member(topic_id, human_id)
    from .db import connect
    with connect() as conn:
        context = _topic_management_context(conn, topic_id, human_id)
        humans = [dict(r) for r in conn.execute(
            """
            SELECT h.id, h.name, h.email, tp.role, tp.created_at
            FROM topic_participants tp
            JOIN humans h ON h.id = tp.participant_id
            WHERE tp.topic_id = ? AND tp.participant_type = 'human'
            UNION
            SELECT DISTINCT h.id, h.name, h.email, 'member' AS role, MIN(m.created_at) AS created_at
            FROM messages m
            JOIN humans h ON h.id = m.actor_id
            WHERE m.topic_id = ? AND m.actor_type = 'human'
              AND NOT EXISTS (
                SELECT 1 FROM topic_participants tp
                WHERE tp.topic_id = m.topic_id
                  AND tp.participant_type = 'human'
                  AND tp.participant_id = m.actor_id
              )
            GROUP BY h.id, h.name, h.email
            ORDER BY id ASC
            """,
            (topic_id, topic_id),
        ).fetchall()]
        agents = [dict(r) for r in conn.execute(
            """
            SELECT
                ai.id,
                ai.device_label,
                ai.display_name,
                ai.deleted_at,
                ar.name AS role,
                ah.name AS human_name,
                tp.role AS participant_role,
                tp.created_at,
                TRUE AS is_explicit
            FROM topic_participants tp
            JOIN agent_instances ai ON ai.id = tp.participant_id
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans ah ON ah.id = ai.owner_human_id
            WHERE tp.topic_id = ? AND tp.participant_type = 'agent'
              AND ai.deleted_at IS NULL
            UNION
            SELECT DISTINCT
                ai.id,
                ai.device_label,
                ai.display_name,
                ai.deleted_at,
                ar.name AS role,
                ah.name AS human_name,
                'member' AS participant_role,
                MIN(m.created_at) AS created_at,
                FALSE AS is_explicit
            FROM messages m
            JOIN agent_instances ai ON ai.id = m.actor_id
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans ah ON ah.id = ai.owner_human_id
            WHERE m.topic_id = ? AND m.actor_type = 'agent'
              AND NOT EXISTS (
                SELECT 1 FROM topic_participants tp
                WHERE tp.topic_id = m.topic_id
                  AND tp.participant_type = 'agent'
                  AND tp.participant_id = m.actor_id
              )
            GROUP BY ai.id, ai.device_label, ai.display_name, ai.deleted_at, ar.name, ah.name
            ORDER BY id ASC
            """,
            (topic_id, topic_id),
        ).fetchall()]
    return {
        "humans": humans,
        "agents": agents,
        "can_manage": context["can_manage"],
        "is_public": context["visibility"] == "public",
    }


@app.post("/api/topics/{topic_id}/participants")
def add_topic_participant(
    topic_id: int,
    payload: TopicParticipantCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    workspace_id, _visibility = _require_topic_manager(topic_id, human_id)
    with connect() as conn:
        _validate_topic_participant(conn, workspace_id or None, payload)
        _add_topic_participant(
            conn,
            topic_id,
            payload.participant_type,
            payload.participant_id,
            role=payload.role,
            added_by_human_id=human_id,
        )
    return get_topic_participants(topic_id, principal)


@app.delete("/api/topics/{topic_id}/participants/{participant_type}/{participant_id}")
def remove_topic_participant(
    topic_id: int,
    participant_type: Literal["human", "agent"],
    participant_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    _workspace_id, visibility = _require_topic_manager(topic_id, human_id)
    if visibility == "public":
        raise HTTPException(status_code=400, detail="public topic participants cannot be removed")
    with connect() as conn:
        if participant_type == "human":
            owner_row = conn.execute(
                """
                SELECT role FROM topic_participants
                WHERE topic_id = ?
                  AND participant_type = 'human'
                  AND participant_id = ?
                """,
                (topic_id, participant_id),
            ).fetchone()
            if owner_row is not None and owner_row["role"] == "owner":
                owner_count = conn.execute(
                    """
                    SELECT COUNT(*) AS c
                    FROM topic_participants
                    WHERE topic_id = ?
                      AND participant_type = 'human'
                      AND role = 'owner'
                    """,
                    (topic_id,),
                ).fetchone()["c"]
                if int(owner_count) <= 1:
                    raise HTTPException(status_code=400, detail="cannot remove last topic owner")
        conn.execute(
            """
            DELETE FROM topic_participants
            WHERE topic_id = ? AND participant_type = ? AND participant_id = ?
            """,
            (topic_id, participant_type, participant_id),
        )
    return get_topic_participants(topic_id, principal)


@app.patch("/api/topics/{topic_id}")
def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    workspace_id, visibility = _require_topic_manager(topic_id, human_id)
    sets, vals = [], []
    if payload.workspace_id is not None:
        if visibility == "public":
            raise HTTPException(status_code=400, detail="public topic cannot move workspace")
        from .workspaces import require_workspace_member
        require_workspace_member(payload.workspace_id, human_id)
        sets.append("workspace_id = ?")
        vals.append(payload.workspace_id)
    if payload.title is not None:
        if visibility == "public" and workspace_id:
            from .workspaces import require_workspace_owner
            require_workspace_owner(workspace_id, human_id)
        sets.append("title = ?")
        vals.append(payload.title)
    if payload.agent_intervention_mode is not None:
        sets.append("agent_intervention_mode = ?")
        vals.append(payload.agent_intervention_mode)
    if payload.shared_context_mode is not None:
        sets.append("shared_context_mode = ?")
        vals.append(payload.shared_context_mode)
    if not sets:
        raise HTTPException(status_code=400, detail="no fields to update")
    sets.append("updated_at = NOW()")  # literal, no value appended to vals
    vals.append(topic_id)
    with connect() as conn:
        row = conn.execute(
            f"UPDATE topics SET {', '.join(sets)} WHERE id = ? "
            "RETURNING id, slug, title, workspace_id, mode, visibility, "
            "agent_intervention_mode, shared_context_mode, archived_at, "
            "created_at, updated_at",
            tuple(vals),
        ).fetchone()
    return dict(row)


@app.post("/api/topics/{topic_id}/archive")
def archive_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    _require_topic_member(topic_id, human_id)
    with connect() as conn:
        topic = conn.execute(
            "SELECT visibility FROM topics WHERE id = ? AND deleted_at IS NULL",
            (topic_id,),
        ).fetchone()
        if topic is not None and topic["visibility"] == "public":
            raise HTTPException(status_code=400, detail="public topic cannot be archived")
        row = conn.execute(
            """
            UPDATE topics
            SET archived_at = COALESCE(archived_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            RETURNING id, slug, title, workspace_id, mode, visibility,
                      archived_at, deleted_at, created_at, updated_at
            """,
            (topic_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return dict(row)


@app.post("/api/topics/{topic_id}/restore")
def restore_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    _require_topic_member(topic_id, human_id)
    with connect() as conn:
        row = conn.execute(
            """
            UPDATE topics
            SET archived_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            RETURNING id, slug, title, workspace_id, mode, visibility,
                      archived_at, deleted_at, created_at, updated_at
            """,
            (topic_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return dict(row)


@app.delete("/api/topics/{topic_id}")
def delete_topic(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    _require_topic_member(topic_id, human_id)
    with connect() as conn:
        topic = conn.execute(
            "SELECT visibility FROM topics WHERE id = ? AND deleted_at IS NULL",
            (topic_id,),
        ).fetchone()
        if topic is not None and topic["visibility"] == "public":
            raise HTTPException(status_code=400, detail="public topic cannot be deleted")
        row = conn.execute(
            """
            UPDATE topics
            SET deleted_at = COALESCE(deleted_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            RETURNING id
            """,
            (topic_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return {"ok": True}


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


_OAUTH_STATES: dict[str, tuple[float, str]] = {}
_OAUTH_TTL_S = 600.0


def _safe_next(next_url: str | None) -> str:
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        return "/app"
    return next_url


def _new_state(next_url: str = "/app") -> str:
    now = _time.time()
    # Lazy cleanup of expired states.
    for k, (ts, _n) in list(_OAUTH_STATES.items()):
        if now - ts > _OAUTH_TTL_S:
            _OAUTH_STATES.pop(k, None)
    s = _secrets.token_urlsafe(24)
    _OAUTH_STATES[s] = (now, _safe_next(next_url))
    return s


def _consume_state(s: str) -> str | None:
    rec = _OAUTH_STATES.pop(s, None)
    return rec[1] if rec is not None else None


@app.get("/auth/github/start")
def auth_github_start(next: str = "/app") -> RedirectResponse:
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID not configured")
    state = _new_state(next)
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
    next_url = _consume_state(state)
    if next_url is None:
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
            # Don't touch `name` on re-login. It was disambiguated on first
            # INSERT (suffix "(2)" etc.) to satisfy the humans.name UNIQUE
            # constraint; setting it back to the bare display_name here can
            # collide with a different row that already holds that name.
            conn.execute(
                """
                UPDATE humans SET github_login = ?, avatar_url = ?,
                       updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (github_login, avatar_url, human_id),
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

    _ensure_onboarded(human_id)
    session_value = issue_session(human_id)
    res = RedirectResponse(url=next_url, status_code=307)
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
            "is_guest": principal["is_guest"],
        }
    }


@app.patch("/auth/me")
def update_auth_me(
    payload: CurrentUserUpdate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        name = _unique_human_name(conn, payload.name, exclude_human_id=human_id)
        conn.execute(
            "UPDATE humans SET name = ?, updated_at = NOW() WHERE id = ?",
            (name, human_id),
        )
        row = conn.execute(
            """
            SELECT id, name, github_login, avatar_url, is_guest
            FROM humans
            WHERE id = ?
            """,
            (human_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="human not found")
    return {
        "human": {
            "id": int(row["id"]),
            "name": row["name"],
            "github_login": row["github_login"],
            "avatar_url": row["avatar_url"],
            "is_guest": bool(row["is_guest"]),
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
# API-facing auth helpers (for test clients and programmatic use)
# ---------------------------------------------------------------------------


class DevLoginPayload(BaseModel):
    name: str = Field(default="Neo", min_length=1)
    email: str | None = None


@app.post("/api/auth/dev-login")
def api_dev_login(payload: DevLoginPayload, response: Response) -> dict:
    """JSON dev-login for test clients. Sets a session cookie and returns human_id.

    Only active when LETS_DEV_SESSIONS=1 (same gate as the browser dev-login).
    """
    if os.environ.get("LETS_DEV_SESSIONS") != "1":
        raise HTTPException(status_code=404, detail="not found")

    from .auth import issue_session
    from .identity import ensure_human

    human_id = ensure_human(payload.name.strip() or "Neo", email=payload.email)
    _ensure_onboarded(human_id)
    session_value = issue_session(human_id)
    response.set_cookie(
        "lets_session",
        session_value,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return {"human_id": human_id}


@app.post("/api/auth/logout", status_code=204)
def api_auth_logout(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> Response:
    """JSON-friendly logout alias for test clients and the SPA."""
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


def _device_flow_start_impl(
    request: Request,
    role: str,
    device_label: str,
    model: str | None,
    workspace_id: int | None,
    workspace_slug: str | None = None,
) -> dict:
    if role not in SUPPORTED_AGENT_ROLES:
        allowed = ", ".join(sorted(SUPPORTED_AGENT_ROLES))
        raise HTTPException(status_code=400, detail=f"role must be one of: {allowed}")
    device_label = device_label.strip()[:80] or "local"
    requested_model = (model or "").strip()
    if not requested_model:
        requested_model = _default_model_for_agent_role(role) or ""
    model = requested_model[:128] or None
    if model and any(ch.isspace() for ch in model):
        raise HTTPException(status_code=400, detail="model cannot contain whitespace")
    # Resolve workspace slug to id when caller can't authenticate to look it up themselves.
    # If slug doesn't resolve, fall through with workspace_id=None — authorize step
    # will default to the human's first workspace or auto-create.
    if workspace_id is None and workspace_slug:
        ws_slug = workspace_slug.strip().lower()
        if ws_slug:
            with connect() as conn:
                row = conn.execute(
                    "SELECT id FROM workspaces WHERE slug = ? AND deleted_at IS NULL",
                    (ws_slug,),
                ).fetchone()
            if row:
                workspace_id = int(row["id"])
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
                (device_code, user_code, role, device_label, model, workspace_id, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', '+10 minutes'))
            """,
            (device_code, user_code, role, device_label, model, workspace_id),
        )
    base_url = _public_base_url(request)
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_url": f"{base_url}/auth/device-flow/authorize?user_code={user_code}",
        "expires_in": 600,
        "interval": 3,
    }


@app.get("/auth/device-flow/start")
def device_flow_start(
    request: Request,
    role: str = Query(default="claude"),
    device_label: str = Query(default="local"),
    model: str | None = Query(default=None),
    workspace: str | None = Query(default=None),
) -> dict:
    return _device_flow_start_impl(
        request=request,
        role=role,
        device_label=device_label,
        model=model,
        workspace_id=None,
        workspace_slug=workspace,
    )


@app.post("/api/auth/device-flow/start")
def api_device_flow_start(
    request: Request,
    role: str = Query(default="claude"),
    device_label: str = Query(default="local"),
    model: str | None = Query(default=None),
    workspace_id: int | None = Query(default=None),
    workspace: str | None = Query(default=None),
) -> dict:
    return _device_flow_start_impl(
        request=request,
        role=role,
        device_label=device_label,
        model=model,
        workspace_id=workspace_id,
        workspace_slug=workspace,
    )


@app.get("/auth/device-flow/authorize")
def device_flow_authorize(
    user_code: str,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
):
    from .auth import issue_token, verify_session
    from .identity import ensure_agent_instance

    next_url = f"/auth/device-flow/authorize?user_code={user_code}"
    principal = verify_session(lets_session) if lets_session else None
    if principal is None:
        # Send the user through whichever login flow is configured, then bring
        # them right back here so the token can be minted in one round-trip.
        if os.environ.get("GITHUB_CLIENT_ID"):
            login_url = "/auth/github/start?next=" + _urllib_parse.quote(next_url, safe="")
        elif os.environ.get("LETS_DEV_SESSIONS") == "1":
            login_url = "/auth/dev/login?next=" + _urllib_parse.quote(next_url, safe="")
        else:
            raise HTTPException(status_code=401, detail="login in the browser first")
        return RedirectResponse(url=login_url, status_code=307)

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
            return HTMLResponse("<h1>Let's gateway already authorized</h1>")
        expired = conn.execute(
            "SELECT CURRENT_TIMESTAMP > ? AS expired", (row["expires_at"],)
        ).fetchone()["expired"]
        if expired:
            raise HTTPException(status_code=410, detail="device flow expired")

    human_id = int(principal["human_id"])
    role = str(row["role"])
    device_label = str(row["device_label"])
    ws_id = row["workspace_id"]
    if ws_id is None:
        from .workspaces import list_workspaces_for_human, create_workspace
        mine = list_workspaces_for_human(human_id)
        if mine:
            ws_id = mine[0]["id"]
        else:
            ws = create_workspace(name="我的工作区", owner_human_id=human_id)
            ws_id = ws["id"]
    agent_instance_id = ensure_agent_instance(
        role=role,
        human_id=human_id,
        device_label=device_label,
        workspace_id=int(ws_id),
        model=str(row["model"]).strip() if row["model"] else None,
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
            SET workspace_id = ?, human_id = ?, agent_instance_id = ?, token_id = ?,
                token_value = ?, authorized_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(ws_id), human_id, agent_instance_id, token_id, token_value, row["id"]),
        )

    return HTMLResponse(_device_authorized_page(role=role, device_label=device_label))


def _device_authorized_page(role: str, device_label: str) -> str:
    safe_role = role.replace("<", "&lt;")
    safe_device = device_label.replace("<", "&lt;")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Let's connected</title>
  <style>
    :root {{
      --bg: oklch(0.985 0.006 75);
      --surface: oklch(0.995 0.004 75);
      --border: oklch(0.88 0.010 75);
      --text: oklch(0.22 0.010 240);
      --muted: oklch(0.46 0.010 240);
      --accent: oklch(0.62 0.16 55);
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: oklch(0.18 0.012 75);
        --surface: oklch(0.22 0.012 75);
        --border: oklch(0.32 0.012 75);
        --text: oklch(0.94 0.010 75);
        --muted: oklch(0.72 0.012 75);
      }}
    }}
    html, body {{ height: 100%; margin: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Helvetica Neue", system-ui, sans-serif;
      display: flex; align-items: center; justify-content: center;
      padding: 32px;
      -webkit-font-smoothing: antialiased;
    }}
    main {{
      max-width: 560px; width: 100%;
      text-align: center;
    }}
    h1 {{
      font-size: 56px; line-height: 1.05; margin: 0 0 24px;
      font-weight: 600; letter-spacing: -0.02em;
    }}
    .lede {{ font-size: 20px; color: var(--muted); line-height: 1.5; margin: 0 0 32px; }}
    .pill {{
      display: inline-flex; align-items: center; gap: 8px;
      padding: 8px 14px; border: 1px solid var(--border); border-radius: 999px;
      background: var(--surface); font-size: 14px; color: var(--muted);
    }}
    .dot {{
      width: 8px; height: 8px; border-radius: 50%;
      background: oklch(0.62 0.14 145);
      box-shadow: 0 0 0 4px color-mix(in oklch, oklch(0.62 0.14 145) 25%, transparent);
    }}
    @media (max-width: 480px) {{
      h1 {{ font-size: 40px; }}
      .lede {{ font-size: 17px; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>You're connected.</h1>
    <p class="lede">Your terminal is set up. You can close this window and head back to it.</p>
    <span class="pill"><span class="dot"></span>{safe_role} · {safe_device}</span>
  </main>
</body>
</html>
"""


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
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model,
                   ai.display_name, ai.owner_human_id, h.name AS human_name
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            WHERE ai.id = ?
            """,
            (row["agent_instance_id"],),
        ).fetchone()
        if agent is not None:
            agent = dict(agent)
            agent["workspace_id"] = row["workspace_id"]
    return {
        "status": "authorized",
        "token": token_value,
        "agent_instance": agent if agent else None,
    }


@app.post("/api/auth/device-flow/authorize/{user_code}")
def api_device_flow_authorize(
    user_code: str,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    """JSON-friendly authorize endpoint for test clients and the SPA.

    Requires an active session cookie. Returns JSON instead of HTML.
    """
    from .auth import issue_token, verify_session
    from .identity import ensure_agent_instance

    principal = verify_session(lets_session) if lets_session else None
    if principal is None:
        raise HTTPException(status_code=401, detail="login required")

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
            return {"status": "already_authorized"}
        expired = conn.execute(
            "SELECT CURRENT_TIMESTAMP > ? AS expired", (row["expires_at"],)
        ).fetchone()["expired"]
        if expired:
            raise HTTPException(status_code=410, detail="device flow expired")

    human_id = int(principal["human_id"])
    role = str(row["role"])
    device_label = str(row["device_label"])
    ws_id = row["workspace_id"]
    if ws_id is None:
        from .workspaces import list_workspaces_for_human, create_workspace
        mine = list_workspaces_for_human(human_id)
        if mine:
            ws_id = mine[0]["id"]
        else:
            ws = create_workspace(name="我的工作区", owner_human_id=human_id)
            ws_id = ws["id"]
    agent_instance_id = ensure_agent_instance(
        role=role,
        human_id=human_id,
        device_label=device_label,
        workspace_id=int(ws_id),
        model=str(row["model"]).strip() if row["model"] else None,
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
            SET workspace_id = ?, human_id = ?, agent_instance_id = ?, token_id = ?,
                token_value = ?, authorized_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (int(ws_id), human_id, agent_instance_id, token_id, token_value, row["id"]),
        )
    return {"status": "authorized", "role": role, "device_label": device_label}


@app.get("/api/auth/device-flow/poll/{device_code}")
def api_device_flow_poll(device_code: str) -> dict:
    """JSON poll endpoint (path param variant) for test clients and the SPA."""
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
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model,
                   ai.display_name, ai.owner_human_id, h.name AS human_name
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
            JOIN humans h ON h.id = ai.owner_human_id
            WHERE ai.id = ?
            """,
            (row["agent_instance_id"],),
        ).fetchone()
        if agent is not None:
            agent = dict(agent)
            agent["workspace_id"] = row["workspace_id"]
    return {
        "status": "authorized",
        "token": token_value,
        "agent": agent if agent else None,
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
    model: str | None = None
    workspace_id: int | None = None


class AgentModelUpdate(BaseModel):
    model: str | None = Field(default=None, min_length=1, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=40)


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
    tokens = [t for t in tokens if t.get("revoked_at") is None]
    with connect() as conn:
        agent_rows = {
            int(r["id"]): {
                "id": int(r["id"]),
                "role": r["role"],
                "device_label": r["device_label"],
                "model": r["model"],
                "display_name": r["display_name"],
            }
            for r in conn.execute(
                """
                SELECT ai.id, ar.name AS role, ai.device_label, ai.model, ai.display_name
                FROM agent_instances ai
                JOIN agent_types ar ON ar.id = ai.agent_type_id
                WHERE ai.owner_human_id = ?
                  AND ai.deleted_at IS NULL
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
    if principal.get("is_guest"):
        raise HTTPException(status_code=403, detail="guest users cannot create agent tokens")
    if payload.role not in SUPPORTED_AGENT_ROLES:
        allowed = ", ".join(sorted(SUPPORTED_AGENT_ROLES))
        raise HTTPException(status_code=400, detail=f"role must be one of: {allowed}")

    _token_ws_id = payload.workspace_id
    if _token_ws_id is None:
        from .workspaces import list_workspaces_for_human, create_workspace
        _mine = list_workspaces_for_human(principal["human_id"])
        if _mine:
            _token_ws_id = _mine[0]["id"]
        else:
            _ws = create_workspace(name="我的工作区", owner_human_id=principal["human_id"])
            _token_ws_id = _ws["id"]
    agent_instance_id = ensure_agent_instance(
        role=payload.role,
        human_id=principal["human_id"],
        device_label=payload.device_label,
        workspace_id=int(_token_ws_id),
        model=payload.model or _default_model_for_agent_role(payload.role),
    )
    raw_value, token_id = issue_token(
        human_id=principal["human_id"],
        agent_instance_id=agent_instance_id,
        label=payload.label,
    )
    with connect() as conn:
        row = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model, ai.display_name
            FROM agent_instances ai
            JOIN agent_types ar ON ar.id = ai.agent_type_id
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
    from .auth import verify_session
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    with connect() as conn:
        owner = conn.execute(
            "SELECT human_id, agent_instance_id FROM tokens WHERE id = ?", (token_id,)
        ).fetchone()
        if owner is None or owner["human_id"] != principal["human_id"]:
            raise HTTPException(status_code=404, detail="token not found")

        agent_instance_id = owner["agent_instance_id"]
        if agent_instance_id is not None:
            _remove_agent_instance_for_owner(
                conn,
                int(agent_instance_id),
                int(principal["human_id"]),
            )
        else:
            conn.execute(
                "UPDATE device_auth_flows SET token_id = NULL, token_value = NULL WHERE token_id = ?",
                (token_id,),
            )
            conn.execute("DELETE FROM tokens WHERE id = ?", (token_id,))
    return Response(status_code=204)
