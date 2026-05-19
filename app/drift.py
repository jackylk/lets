"""Drift context computation + nudge persistence."""
from __future__ import annotations

import json

from .db import connect
from .task_trees import active_item


def compute_drift_context(topic_id: int) -> dict:
    """Return the drift_context dict embedded in topic_stream responses.

    Shape (see spec §5.3):
      topic_mode: "exploratory" | "actionable"
      active_task: {id, title} | null
      last_nudge_at: ISO timestamp | null
      last_nudge_message_id: int | null
      last_nudge_resolved_by: "moved_to_topic"|"returned"|"dismissed"|null
      messages_since_last_nudge: int
    """
    with connect() as conn:
        topic_row = conn.execute(
            "SELECT mode FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if topic_row is None:
            raise KeyError(f"topic {topic_id} not found")
        mode = topic_row["mode"]

        last_nudge = conn.execute(
            """SELECT id, nudge_message_id, resolved_by, created_at
               FROM drift_nudges
               WHERE topic_id = ?
               ORDER BY created_at DESC, id DESC
               LIMIT 1""",
            (topic_id,),
        ).fetchone()

        last_nudge_msg_id = last_nudge["nudge_message_id"] if last_nudge else None
        if last_nudge_msg_id is None:
            count_row = conn.execute(
                "SELECT COUNT(*) AS n FROM messages WHERE topic_id = ?",
                (topic_id,),
            ).fetchone()
        else:
            count_row = conn.execute(
                """SELECT COUNT(*) AS n FROM messages
                   WHERE topic_id = ? AND id > ?""",
                (topic_id, last_nudge_msg_id),
            ).fetchone()
        msgs_since = int(count_row["n"])

    active = active_item(topic_id)
    return {
        "topic_mode": mode,
        "active_task": (
            {"id": active["id"], "title": active["title"]} if active else None
        ),
        "last_nudge_at": last_nudge["created_at"] if last_nudge else None,
        "last_nudge_message_id": last_nudge_msg_id,
        "last_nudge_resolved_by": (
            last_nudge["resolved_by"] if last_nudge else None
        ),
        "messages_since_last_nudge": msgs_since,
    }


def post_nudge(
    topic_id: int,
    triggered_by_agent_instance_id: int | None,
    reason: str,
    drift_summary: str,
    window_start_message_id: int | None = None,
    window_end_message_id: int | None = None,
) -> dict:
    """Posts a nudge typed message + drift_nudges row in a single transaction.

    If either INSERT fails, both roll back.

    Returns: {"nudge_message_id": ..., "drift_nudge_id": ...}.
    """
    actor_type = "agent" if triggered_by_agent_instance_id else "system"
    metadata = {"reason": reason, "drift_summary": drift_summary}
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages
                (topic_id, type, actor_type, actor_id, body, metadata, ref_event_id, addressed_to)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                "nudge",
                actor_type,
                triggered_by_agent_instance_id,
                reason,
                metadata_json,
                None,
                None,
            ),
        )
        nudge_msg_id = int(cur.lastrowid)
        cur = conn.execute(
            """INSERT INTO drift_nudges
                   (topic_id, nudge_message_id, triggered_by_agent_instance_id,
                    drift_window_start_message_id, drift_window_end_message_id,
                    drift_summary)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                topic_id, nudge_msg_id, triggered_by_agent_instance_id,
                window_start_message_id, window_end_message_id, drift_summary,
            ),
        )
        drift_id = int(cur.lastrowid)
    return {"nudge_message_id": nudge_msg_id, "drift_nudge_id": drift_id}


def resolve_nudge(
    drift_nudge_id: int,
    resolution: str,
    resolved_to_topic_id: int | None = None,
) -> dict:
    """Mark a drift_nudge resolved. Caller is responsible for FK validity."""
    if resolution not in ("moved_to_topic", "returned", "dismissed"):
        raise ValueError(f"invalid resolution: {resolution}")
    with connect() as conn:
        conn.execute(
            """UPDATE drift_nudges
               SET resolved_at = CURRENT_TIMESTAMP,
                   resolved_by = ?,
                   resolved_to_topic_id = ?
               WHERE id = ?""",
            (resolution, resolved_to_topic_id, drift_nudge_id),
        )
        row = conn.execute(
            "SELECT * FROM drift_nudges WHERE id = ?", (drift_nudge_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"drift_nudge {drift_nudge_id} not found")
    return dict(row)
