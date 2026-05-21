from __future__ import annotations

import re
import secrets
from typing import Any

from .db import connect


def slugify(name: str) -> str:
    """Lowercase + dashes; CJK / non-ASCII names fall back to ws-<6hex>."""
    s = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    if not s:
        s = f"ws-{secrets.token_hex(3)}"
    return s


def _next_unique_slug(base: str, conn) -> str:
    candidate = base
    n = 2
    while True:
        row = conn.execute(
            "SELECT 1 FROM workspaces WHERE slug = ?", (candidate,)
        ).fetchone()
        if row is None:
            return candidate
        candidate = f"{base}-{n}"
        n += 1


def create_workspace(name: str, owner_human_id: int) -> dict[str, Any]:
    """Create workspace and add the owner as a member in one transaction."""
    base = slugify(name)
    with connect() as conn:
        slug = _next_unique_slug(base, conn)
        row = conn.execute(
            """
            INSERT INTO workspaces (slug, name, owner_human_id)
            VALUES (?, ?, ?)
            RETURNING id, slug, name, description, owner_human_id,
                      is_private, deleted_at, created_at, updated_at
            """,
            (slug, name, owner_human_id),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, human_id, role)
            VALUES (?, ?, 'owner')
            RETURNING workspace_id
            """,
            (row["id"], owner_human_id),
        )
        return dict(row)


def is_workspace_member(workspace_id: int, human_id: int) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = ? AND human_id = ?
            """,
            (workspace_id, human_id),
        ).fetchone()
    return row is not None


def list_workspaces_for_human(human_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT w.id, w.slug, w.name, w.description, w.owner_human_id,
                   w.is_private, w.created_at, w.updated_at,
                   wm.role AS my_role
            FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE wm.human_id = ? AND w.deleted_at IS NULL
            ORDER BY w.updated_at DESC
            """,
            (human_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def generate_invite_token() -> str:
    return secrets.token_urlsafe(16)
