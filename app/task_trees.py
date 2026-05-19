"""Task tree + task item domain helpers."""
from __future__ import annotations

import json
from typing import Any

from .db import connect


def get_tree_by_topic(topic_id: int) -> dict | None:
    """Return the active task_tree row for ``topic_id`` or None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM task_trees WHERE topic_id = ?", (topic_id,)
        ).fetchone()
    return dict(row) if row else None


def list_items(tree_id: int) -> list[dict]:
    """Return all task_items for ``tree_id`` ordered by parent then position."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM task_items
               WHERE task_tree_id = ?
               ORDER BY COALESCE(parent_item_id, 0), position, id""",
            (tree_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_tree(
    topic_id: int,
    goal_artifact_id: int | None,
    goal_spec_text: str | None,
    proposal_message_id: int | None,
    approved_by_human_id: int | None,
) -> dict:
    """Insert a new task_trees row for ``topic_id`` or bump version + update goal."""
    with connect() as conn:
        existing = conn.execute(
            "SELECT id, version FROM task_trees WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE task_trees SET
                       version = version + 1,
                       goal_artifact_id = COALESCE(?, goal_artifact_id),
                       goal_spec_text = COALESCE(?, goal_spec_text),
                       proposal_message_id = COALESCE(?, proposal_message_id),
                       approved_by_human_id = COALESCE(?, approved_by_human_id),
                       approved_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    goal_artifact_id, goal_spec_text,
                    proposal_message_id, approved_by_human_id,
                    existing["id"],
                ),
            )
            tree_id = existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO task_trees
                       (topic_id, goal_artifact_id, goal_spec_text,
                        proposal_message_id, approved_by_human_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    topic_id, goal_artifact_id, goal_spec_text,
                    proposal_message_id, approved_by_human_id,
                ),
            )
            tree_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT * FROM task_trees WHERE id = ?", (tree_id,)
        ).fetchone()
    return dict(row)


def replace_items(tree_id: int, items: list[dict]) -> list[dict]:
    """Replace all task_items under ``tree_id`` with the given list.

    Each item dict has: title (required), parent_index (optional, 0-based into
    the items list to set parent), owner_human_id (optional),
    owner_agent_instance_id (optional). position is assigned by enumeration.
    """
    with connect() as conn:
        conn.execute("DELETE FROM task_items WHERE task_tree_id = ?", (tree_id,))
        # Two-pass insert: first all items without parent set, then UPDATE parent FKs.
        new_ids: list[int] = []
        for pos, item in enumerate(items):
            cur = conn.execute(
                """INSERT INTO task_items
                       (task_tree_id, title, owner_human_id, owner_agent_instance_id,
                        position)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    tree_id, item["title"],
                    item.get("owner_human_id"),
                    item.get("owner_agent_instance_id"),
                    pos,
                ),
            )
            new_ids.append(int(cur.lastrowid))
        for pos, item in enumerate(items):
            parent_idx = item.get("parent_index")
            if parent_idx is not None and 0 <= parent_idx < len(new_ids):
                conn.execute(
                    "UPDATE task_items SET parent_item_id = ? WHERE id = ?",
                    (new_ids[parent_idx], new_ids[pos]),
                )
    return list_items(tree_id)


def add_item(
    tree_id: int,
    title: str,
    parent_item_id: int | None = None,
    owner_human_id: int | None = None,
    owner_agent_instance_id: int | None = None,
) -> dict:
    """Append a new task_item under ``tree_id`` (optionally under a parent)."""
    with connect() as conn:
        row = conn.execute(
            """SELECT COALESCE(MAX(position), -1) + 1 AS next_pos
               FROM task_items
               WHERE task_tree_id = ?
                 AND (parent_item_id IS ? OR parent_item_id = ?)""",
            (tree_id, parent_item_id, parent_item_id),
        ).fetchone()
        next_pos = row["next_pos"]
        cur = conn.execute(
            """INSERT INTO task_items
                   (task_tree_id, parent_item_id, title,
                    owner_human_id, owner_agent_instance_id, position)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tree_id, parent_item_id, title,
             owner_human_id, owner_agent_instance_id, next_pos),
        )
        new_row = conn.execute(
            "SELECT * FROM task_items WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(new_row)


def update_item(item_id: int, *, status: str | None = None, title: str | None = None) -> dict:
    """Update status and/or title of a task_item."""
    if status is None and title is None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM task_items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"task_item {item_id} not found")
        return dict(row)

    fields: list[str] = []
    params: list[Any] = []
    if status is not None:
        if status not in ("pending", "active", "done"):
            raise ValueError(f"invalid status: {status}")
        fields.append("status = ?")
        params.append(status)
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(item_id)
    with connect() as conn:
        conn.execute(
            f"UPDATE task_items SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        row = conn.execute(
            "SELECT * FROM task_items WHERE id = ?", (item_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"task_item {item_id} not found")
    return dict(row)


def active_item(topic_id: int) -> dict | None:
    """Return the single task_item with status='active' for this topic, or None."""
    with connect() as conn:
        row = conn.execute(
            """SELECT ti.*
               FROM task_items ti
               JOIN task_trees tt ON tt.id = ti.task_tree_id
               WHERE tt.topic_id = ? AND ti.status = 'active'
               ORDER BY ti.position ASC, ti.id ASC
               LIMIT 1""",
            (topic_id,),
        ).fetchone()
    return dict(row) if row else None
