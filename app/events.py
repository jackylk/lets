from __future__ import annotations

import json
from typing import Any, Optional

from .db import connect


ALLOWED_ACTOR_TYPES = {"human", "agent", "system"}


def record_event(
    event_type: str,
    actor_type: str,
    actor_id: Optional[int],
    target_type: str,
    target_id: Optional[int],
    payload: Optional[dict[str, Any]] = None,
    project_id: Optional[int] = None,
    topic_id: Optional[int] = None,
) -> int:
    """Append an event. Returns events.id."""
    if actor_type not in ALLOWED_ACTOR_TYPES:
        raise ValueError(f"actor_type must be one of {sorted(ALLOWED_ACTOR_TYPES)}")
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO events
                (event_type, actor_type, actor_id, target_type, target_id,
                 project_id, topic_id, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_type, actor_type, actor_id, target_type, target_id,
             project_id, topic_id, payload_json),
        )
        return int(cursor.lastrowid)


def query_events(
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Filtered events query, newest first."""
    clauses: list[str] = []
    params: list[Any] = []
    if target_type:
        clauses.append("target_type = ?")
        params.append(target_type)
    if target_id is not None:
        clauses.append("target_id = ?")
        params.append(target_id)
    if topic_id is not None:
        clauses.append("topic_id = ?")
        params.append(topic_id)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT * FROM events
        {where}
        ORDER BY occurred_at DESC, id DESC
        LIMIT ?
    """
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        out.append(d)
    return out
