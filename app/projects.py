"""Project helpers — CRUD on the projects table.

Track C1: local-only mode. No GitHub integration. ``repo_path`` is an
optional pointer to a local filesystem directory (a git repo or not — we
read files but don't perform git operations).
"""
from __future__ import annotations

import re
from typing import Optional

from .db import connect


_SLUG_NORMALIZE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Lowercase + dash-separated alphanumeric. 'Hello World!' → 'hello-world'."""
    return _SLUG_NORMALIZE.sub("-", name.lower()).strip("-") or "project"


def create_project(
    name: str,
    *,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    owner_human_id: Optional[int] = None,
    repo_path: Optional[str] = None,
) -> int:
    """Create a project. Returns projects.id. Raises ValueError on slug collision."""
    import sqlite3
    final_slug = slug or slugify(name)
    with connect() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO projects (slug, name, description, owner_human_id, repo_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (final_slug, name, description, owner_human_id, repo_path),
            )
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) and "slug" in str(e):
                raise ValueError(f"slug already in use: {final_slug}")
            raise


def get_project_by_id(project_id: int) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def get_project_by_slug(slug: str) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE slug = ?", (slug,)).fetchone()
    return dict(row) if row else None


def list_projects() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY id ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_project_repo_path(project_id: int, repo_path: Optional[str]) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE projects
            SET repo_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (repo_path, project_id),
        )


def update_project(
    project_id: int,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    repo_path: Optional[str] = None,
) -> None:
    """Patch-style update. Only updates fields explicitly passed."""
    fields = []
    params: list = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if repo_path is not None:
        fields.append("repo_path = ?")
        params.append(repo_path)
    if not fields:
        return
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(project_id)
    sql = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
    with connect() as conn:
        conn.execute(sql, params)
