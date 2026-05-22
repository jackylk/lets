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


def ensure_agent_instance(
    role: str,
    human_id: int,
    device_label: str,
    workspace_id: int | None = None,
    model: str | None = None,
) -> int:
    """Return agent_instances.id. Create if missing. Idempotent. Raises ValueError if role unknown.

    If workspace_id is provided, the owned agent is also added to that
    workspace. Agent identity is keyed on (owner human, role, device).
    """
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
            WHERE role_id = ? AND owner_human_id = ? AND device_label = ?
            """,
            (role_id, human_id, device_label),
        ).fetchone()
        if existing:
            if model is not None:
                conn.execute(
                    """
                    UPDATE agent_instances
                    SET model = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (model, existing["id"]),
                )
            agent_id = int(existing["id"])
            if workspace_id is not None:
                _join_agent_workspace(conn, workspace_id, agent_id, human_id)
            return agent_id

        cursor = conn.execute(
            """
            INSERT INTO agent_instances (role_id, owner_human_id, device_label, model)
            VALUES (?, ?, ?, ?)
            """,
            (role_id, human_id, device_label, model),
        )
        agent_id = int(cursor.lastrowid)
        if workspace_id is not None:
            _join_agent_workspace(conn, workspace_id, agent_id, human_id)
        return agent_id


def _join_agent_workspace(conn, workspace_id: int, agent_instance_id: int, owner_human_id: int) -> None:
    row = conn.execute(
        """
        SELECT 1 FROM workspace_members
        WHERE workspace_id = ? AND human_id = ?
        """,
        (workspace_id, owner_human_id),
    ).fetchone()
    if row is None:
        raise ValueError("agent owner must be a workspace member")
    conn.execute(
        """
        INSERT INTO workspace_agent_members
            (workspace_id, agent_instance_id, joined_by_human_id)
        VALUES (?, ?, ?)
        ON CONFLICT DO NOTHING
        RETURNING workspace_agent_members.workspace_id
        """,
        (workspace_id, agent_instance_id, owner_human_id),
    )
