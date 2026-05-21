from __future__ import annotations

import json
from typing import Any, Literal

from .db import connect


ALLOWED_TYPES = {
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
}

MessageType = Literal[
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

ActorType = Literal["human", "agent", "system"]


def post_message(
    topic_id: int,
    type: str,
    actor_type: str,
    actor_id: int | None,
    body: str,
    metadata: dict[str, Any] | None = None,
    ref_event_id: int | None = None,
    addressed_to: str | None = None,
) -> int:
    """Insert a typed message into a topic stream. Returns messages.id.

    ``addressed_to`` is a CSV of human IDs the message is directed at —
    consumed by GET /api/attention to build the per-user inbox.
    """
    if type not in ALLOWED_TYPES:
        raise ValueError(f"unknown message type: {type}")
    if actor_type not in ("human", "agent", "system"):
        raise ValueError(f"unknown actor_type: {actor_type}")

    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages
                (topic_id, type, actor_type, actor_id, body, metadata, ref_event_id, addressed_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (topic_id, type, actor_type, actor_id, body, metadata_json, ref_event_id, addressed_to),
        )
        return int(cursor.lastrowid)


def topic_stream(
    topic_id: int,
    *,
    order: str = "asc",
    type_filter: list[str] | None = None,
    limit: int = 500,
    after_id: int | None = None,
) -> list[dict]:
    """Return messages for a topic. order='asc' for chronological, 'desc' for newest first.

    When ``after_id`` is set, only messages with ``id > after_id`` are returned —
    used by SSE clients for catch-up polling on reconnect.
    """
    if order not in ("asc", "desc"):
        raise ValueError("order must be 'asc' or 'desc'")

    clauses = ["topic_id = ?"]
    params: list[Any] = [topic_id]
    if type_filter:
        placeholders = ",".join("?" * len(type_filter))
        clauses.append(f"type IN ({placeholders})")
        params.extend(type_filter)
    if after_id is not None:
        clauses.append("id > ?")
        params.append(after_id)

    where = " AND ".join(clauses)
    sql = f"""
        SELECT * FROM messages
        WHERE {where}
        ORDER BY created_at {order.upper()}, id {order.upper()}
        LIMIT ?
    """
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    messages = []
    for row in rows:
        message = dict(row)
        message["metadata"] = json.loads(message["metadata"])
        messages.append(message)
    return messages
