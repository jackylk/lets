"""Topic CRUD helpers."""
from __future__ import annotations

from typing import Optional

from .db import connect


def create_topic(slug: str, title: str, project_id: int) -> int:
    """Create a topic in a project. Raises ValueError on slug collision within the project."""
    import sqlite3
    with connect() as conn:
        # Pre-check for slug collision within the same project
        existing = conn.execute(
            "SELECT id FROM topics WHERE slug = ? AND project_id = ?",
            (slug, project_id),
        ).fetchone()
        if existing:
            raise ValueError(f"slug already in use within project: {slug}")
        try:
            cursor = conn.execute(
                "INSERT INTO topics (slug, title, project_id) VALUES (?, ?, ?)",
                (slug, title, project_id),
            )
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as e:
            # topics.slug is globally UNIQUE in Track A schema; surface as the
            # same ValueError so callers see a uniform error type.
            raise ValueError(f"slug already in use: {slug}") from e


def get_topic_by_id(topic_id: int) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
    return dict(row) if row else None


def get_topic_by_slug(slug: str, project_id: int) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM topics WHERE slug = ? AND project_id = ?",
            (slug, project_id),
        ).fetchone()
    return dict(row) if row else None


def list_topics_by_project(project_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM topics
            WHERE project_id = ?
            ORDER BY id ASC
            """,
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]
