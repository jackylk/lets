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


def _decode_metadata(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if raw in (None, ""):
        return {}
    return json.loads(raw)


def _deleted_placeholder(kind: str | None) -> str:
    return "这条消息已撤回" if kind == "retracted" else "这条消息已删除"


def message_from_row(row: Any, *, redact_deleted: bool = True) -> dict[str, Any]:
    message = dict(row)
    message["metadata"] = _decode_metadata(message.get("metadata"))
    if redact_deleted and message.get("deleted_at") is not None:
        message["body"] = _deleted_placeholder(message.get("deletion_kind"))
        message["metadata"] = {}
        message["addressed_to"] = None
    return message


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

    messages = [message_from_row(row) for row in rows]
    cited_ids: set[int] = set()
    for message in messages:
        meta = message.get("metadata") or {}
        raw_cites = meta.get("cites")
        if isinstance(raw_cites, list):
            cited_ids.update(n for n in raw_cites if isinstance(n, int))
    for message in messages:
        message["edited_after_agent_read"] = (
            message.get("edited_at") is not None
            and int(message["id"]) in cited_ids
        )
    return messages


def edit_message(message_id: int, body: str, edited_by_human_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            UPDATE messages
            SET body = ?,
                edited_at = CURRENT_TIMESTAMP,
                edited_by_human_id = ?,
                edit_count = edit_count + 1
            WHERE id = ? AND deleted_at IS NULL
            RETURNING *
            """,
            (body, edited_by_human_id, message_id),
        ).fetchone()
    if row is None:
        raise ValueError("message not found")
    return message_from_row(row)


def mark_message_deleted(
    message_id: int,
    *,
    deleted_by_human_id: int,
    kind: str,
    reason: str | None = None,
) -> dict[str, Any]:
    if kind not in {"deleted", "retracted"}:
        raise ValueError("invalid deletion kind")
    with connect() as conn:
        row = conn.execute(
            """
            UPDATE messages
            SET deleted_at = COALESCE(deleted_at, CURRENT_TIMESTAMP),
                deleted_by_human_id = COALESCE(deleted_by_human_id, ?),
                deletion_kind = COALESCE(deletion_kind, ?),
                deletion_reason = COALESCE(deletion_reason, ?)
            WHERE id = ?
            RETURNING *
            """,
            (deleted_by_human_id, kind, reason, message_id),
        ).fetchone()
    if row is None:
        raise ValueError("message not found")
    return message_from_row(row)
