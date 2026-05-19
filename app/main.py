from __future__ import annotations

import base64
import json
import importlib
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.types import ASGIApp, Receive, Scope, Send

from . import mcp_server as mcp_server_module
from .auth import get_current_principal, verify_token
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
        if (
            len(parts) != 2
            or parts[0].lower() != "bearer"
            or verify_token(parts[1].strip()) is None
        ):
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

        await self.app(scope, receive, send)


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


class EventCreate(BaseModel):
    event_type: str
    actor_type: ActorType
    actor_id: int | None = None
    target_type: str
    target_id: int | None = None
    project_id: int | None = None
    topic_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


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


@app.get("/")
def home() -> FileResponse:
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
        }
    }


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
def post_message_endpoint(
    payload: MessageCreate,
    principal: dict = Depends(get_current_principal),
) -> dict:
    from .messages import post_message

    message_id = post_message(
        topic_id=payload.topic_id,
        type=payload.type,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        body=payload.body,
        metadata=payload.metadata,
        ref_event_id=payload.ref_event_id,
    )
    with connect() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()

    message = dict(row)
    message["metadata"] = json.loads(message["metadata"])
    return message


@app.get("/api/topics/{topic_id}/messages")
def get_topic_messages(
    topic_id: int,
    type: list[str] | None = Query(default=None),
    limit: int = 500,
    principal: dict = Depends(get_current_principal),
) -> list[dict]:
    from .messages import topic_stream

    return topic_stream(topic_id, type_filter=type, limit=limit)


@app.post("/api/events")
def post_event(
    payload: EventCreate,
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
) -> list[dict]:
    from .events import query_events

    return query_events(
        target_type=target_type,
        target_id=target_id,
        topic_id=topic_id,
        event_type=event_type,
        limit=limit,
    )


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
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
) -> list[dict]:
    from .projects import list_projects
    return list_projects()


@app.get("/api/projects/{project_id}")
def get_project(
    project_id: int,
    principal: dict = Depends(get_current_principal),
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
    principal: dict = Depends(get_current_principal),
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
