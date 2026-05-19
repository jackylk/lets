from __future__ import annotations

from typing import Optional

from .db import connect


def ensure_human(name: str, email: Optional[str] = None) -> int:
    """Return the humans.id for a given name. Create if missing. Idempotent."""
    with connect() as conn:
        row = conn.execute("SELECT id FROM humans WHERE name = ?", (name,)).fetchone()
        if row:
            if email is not None:
                conn.execute(
                    "UPDATE humans SET email = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (email, row["id"]),
                )
            return int(row["id"])
        cursor = conn.execute(
            "INSERT INTO humans (name, email) VALUES (?, ?)", (name, email)
        )
        return int(cursor.lastrowid)


def ensure_agent_instance(role: str, human_id: int, device_label: str) -> int:
    """Return agent_instances.id. Create if missing. Idempotent. Raises ValueError if role unknown."""
    with connect() as conn:
        role_row = conn.execute(
            "SELECT id FROM agent_roles WHERE name = ?", (role,)
        ).fetchone()
        if not role_row:
            raise ValueError(f"unknown agent role: {role}")
        role_id = int(role_row["id"])

        existing = conn.execute(
            """
            SELECT id FROM agent_instances
            WHERE role_id = ? AND human_id = ? AND device_label = ?
            """,
            (role_id, human_id, device_label),
        ).fetchone()
        if existing:
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO agent_instances (role_id, human_id, device_label)
            VALUES (?, ?, ?)
            """,
            (role_id, human_id, device_label),
        )
        return int(cursor.lastrowid)
