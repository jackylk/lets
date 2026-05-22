from __future__ import annotations

from typing import Optional

from .db import connect


AGENT_DISPLAY_NAMES = (
    "Neo",
    "Trinity",
    "Morpheus",
    "Oracle",
    "Tank",
    "Switch",
    "Apoc",
    "Seraph",
    "Niobe",
    "Dozer",
    "Link",
    "Sparks",
)


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
    """Return agent_instances.id. Create if missing. Idempotent. Raises ValueError if type unknown.

    If workspace_id is provided, the owned agent is also added to that
    workspace. Agent identity is keyed on (owner human, agent type, device).
    """
    with connect() as conn:
        role_row = conn.execute(
            "SELECT id FROM agent_types WHERE name = ?", (role,)
        ).fetchone()
        if not role_row:
            raise ValueError(f"unknown agent type: {role}")
        agent_type_id = int(role_row["id"])

        existing = conn.execute(
            """
            SELECT id FROM agent_instances
            WHERE agent_type_id = ? AND owner_human_id = ? AND device_label = ?
            """,
            (agent_type_id, human_id, device_label),
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

        display_name = _next_agent_display_name(conn, human_id)
        cursor = conn.execute(
            """
            INSERT INTO agent_instances
                (agent_type_id, owner_human_id, device_label, model, display_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent_type_id, human_id, device_label, model, display_name),
        )
        agent_id = int(cursor.lastrowid)
        if workspace_id is not None:
            _join_agent_workspace(conn, workspace_id, agent_id, human_id)
        return agent_id


def _next_agent_display_name(conn, human_id: int) -> str:
    rows = conn.execute(
        """
        SELECT display_name FROM agent_instances
        WHERE owner_human_id = ? AND display_name IS NOT NULL
        """,
        (human_id,),
    ).fetchall()
    used = {str(r["display_name"]) for r in rows if r["display_name"]}
    for name in AGENT_DISPLAY_NAMES:
        if name not in used:
            return name
    i = 2
    while True:
        for name in AGENT_DISPLAY_NAMES:
            candidate = f"{name} {i}"
            if candidate not in used:
                return candidate
        i += 1


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
