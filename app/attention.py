"""Attention-queue aggregator: cross-topic queries for things the user owes a response to."""
from __future__ import annotations

import json
from .db import connect


_NEEDS_DECISION_TYPES = (
    "question", "spec_change", "task_tree_proposal",
    "project_proposal", "goal_proposal",
)


def get_attention(human_id: int) -> dict:
    """Return three buckets of attention items for one human.

    The ``messages.addressed_to`` column is treated as a comma-separated
    list of human IDs. We wrap with commas on both sides so an integer-id
    match doesn't false-positive on a substring (e.g., "5" inside "15").
    """
    needle = str(human_id)
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT m.*, t.slug as topic_slug, t.title as topic_title, t.project_id
            FROM messages m
            JOIN topics t ON t.id = m.topic_id
            WHERE m.addressed_to IS NOT NULL
              AND ',' || REPLACE(m.addressed_to, ' ', '') || ',' LIKE '%,' || ? || ',%'
            ORDER BY m.created_at DESC
            """,
            (needle,),
        ).fetchall()

    needs_decision: list[dict] = []
    mentioned_questions: list[dict] = []
    suggestions: list[dict] = []
    for row in rows:
        msg = dict(row)
        try:
            msg["metadata"] = json.loads(msg["metadata"]) if msg.get("metadata") else {}
        except (json.JSONDecodeError, TypeError):
            msg["metadata"] = {}
        if msg["type"] == "proactive_finding":
            suggestions.append(msg)
        elif msg["type"] in _NEEDS_DECISION_TYPES:
            needs_decision.append(msg)
        else:
            mentioned_questions.append(msg)
    return {
        "needs_decision": needs_decision,
        "mentioned_questions": mentioned_questions,
        "suggestions": suggestions,
    }
