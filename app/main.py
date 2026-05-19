from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .auth import get_current_principal
from .db import connect, init_db

app = FastAPI(title="Lets")


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


@app.on_event("startup")
def startup() -> None:
    init_db()


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
