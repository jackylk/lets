from mcp.server.fastmcp import FastMCP

from .db import connect, init_db

mcp = FastMCP("Lets")


def ensure_agent(name: str, agent_type: str) -> int:
    with connect() as conn:
        row = conn.execute("SELECT id FROM agents WHERE name = ?", (name,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE agents
                SET agent_type = ?, last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (agent_type, row["id"]),
            )
            return int(row["id"])
        cursor = conn.execute(
            "INSERT INTO agents (name, agent_type, status) VALUES (?, ?, 'idle')",
            (name, agent_type),
        )
        return int(cursor.lastrowid)


@mcp.tool()
def get_project_context() -> dict:
    """Return the current Lets project context."""
    return {
        "project": {
            "name": "Lets",
            "description": "Shared workboard for local coding agents.",
        }
    }


@mcp.tool()
def list_work_items(status: str | None = None) -> list[dict]:
    """List shared work items, optionally filtered by status."""
    query = """
        SELECT wi.*, a.name AS claimed_by_agent_name
        FROM work_items wi
        LEFT JOIN agents a ON a.id = wi.claimed_by_agent_id
    """
    params: tuple[object, ...] = ()
    if status:
        query += " WHERE wi.status = ?"
        params = (status,)
    query += " ORDER BY wi.created_at DESC, wi.id DESC"
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


@mcp.tool()
def create_work_item(
    type: str,
    title: str,
    body: str,
    agent_name: str,
    agent_type: str = "unknown",
) -> dict:
    """Create a new idea or task on the shared board.

    type must be 'idea' or 'task'. The created_by field is set to the agent
    name so the board attributes agent-authored items distinctly from
    human-authored ones.
    """
    if type not in {"idea", "task"}:
        raise ValueError("type must be 'idea' or 'task'")
    ensure_agent(agent_name, agent_type)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO work_items (type, title, body, created_by)
            VALUES (?, ?, ?, ?)
            """,
            (type, title, body, agent_name),
        )
        row = conn.execute(
            "SELECT * FROM work_items WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


@mcp.tool()
def create_feedback(
    feedback_type: str,
    body: str,
    agent_name: str,
    agent_type: str = "unknown",
    work_item_id: int | None = None,
) -> dict:
    """Post typed feedback to the board.

    feedback_type must be one of: instruction, opinion, question, correction,
    priority_change, review. Agents typically use 'question' to flag a point
    that needs human input, or 'review' to comment on an existing item.
    """
    allowed = {
        "instruction",
        "opinion",
        "question",
        "correction",
        "priority_change",
        "review",
    }
    if feedback_type not in allowed:
        raise ValueError(f"feedback_type must be one of {sorted(allowed)}")
    ensure_agent(agent_name, agent_type)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO human_notes (work_item_id, body, feedback_type)
            VALUES (?, ?, ?)
            """,
            (work_item_id, body, feedback_type),
        )
        row = conn.execute(
            "SELECT * FROM human_notes WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


@mcp.tool()
def claim_work_item(
    work_item_id: int,
    agent_name: str,
    agent_type: str = "unknown",
    git_branch: str | None = None,
) -> dict:
    """Claim an open work item for one agent."""
    agent_id = ensure_agent(agent_name, agent_type)
    with connect() as conn:
        item = conn.execute("SELECT * FROM work_items WHERE id = ?", (work_item_id,)).fetchone()
        if not item:
            raise ValueError("work item not found")
        if item["claimed_by_agent_id"] and item["claimed_by_agent_id"] != agent_id:
            raise ValueError("work item already claimed")
        conn.execute(
            """
            UPDATE work_items
            SET status = 'claimed',
                claimed_by_agent_id = ?,
                claimed_at = CURRENT_TIMESTAMP,
                git_branch = COALESCE(?, git_branch),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (agent_id, git_branch, work_item_id),
        )
        conn.execute(
            """
            UPDATE agents
            SET status = 'active', last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (agent_id,),
        )
        row = conn.execute(
            """
            SELECT wi.*, a.name AS claimed_by_agent_name
            FROM work_items wi
            LEFT JOIN agents a ON a.id = wi.claimed_by_agent_id
            WHERE wi.id = ?
            """,
            (work_item_id,),
        ).fetchone()
    return dict(row)


@mcp.tool()
def set_work_item_status(
    work_item_id: int,
    status: str,
    agent_name: str | None = None,
    agent_type: str = "unknown",
    message: str | None = None,
) -> dict:
    """Transition a work item to one of: open, claimed, in_progress, done, rejected.

    Used to mark a claimed item as 'done' once the agent finishes the work, or
    to release it back to 'open' if the agent gives up. When agent_name is
    given, an audit row is written to status_updates so the activity feed
    reflects the transition.
    """
    allowed = {"open", "claimed", "in_progress", "done", "rejected"}
    if status not in allowed:
        raise ValueError(f"status must be one of {sorted(allowed)}")
    agent_id = ensure_agent(agent_name, agent_type) if agent_name else None
    with connect() as conn:
        item = conn.execute(
            "SELECT * FROM work_items WHERE id = ?", (work_item_id,)
        ).fetchone()
        if not item:
            raise ValueError("work item not found")

        conn.execute(
            """
            UPDATE work_items
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, work_item_id),
        )

        if agent_id is not None:
            conn.execute(
                """
                INSERT INTO status_updates (agent_id, work_item_id, status, message)
                VALUES (?, ?, ?, ?)
                """,
                (
                    agent_id,
                    work_item_id,
                    status,
                    message or f"transitioned work item to {status}",
                ),
            )

        row = conn.execute(
            """
            SELECT wi.*, a.name AS claimed_by_agent_name
            FROM work_items wi
            LEFT JOIN agents a ON a.id = wi.claimed_by_agent_id
            WHERE wi.id = ?
            """,
            (work_item_id,),
        ).fetchone()
    return dict(row)


@mcp.tool()
def report_status(
    agent_name: str,
    status: str,
    message: str,
    agent_type: str = "unknown",
    work_item_id: int | None = None,
) -> dict:
    """Publish the current status of an agent."""
    agent_id = ensure_agent(agent_name, agent_type)
    with connect() as conn:
        conn.execute(
            """
            UPDATE agents
            SET status = ?, last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, agent_id),
        )
        cursor = conn.execute(
            """
            INSERT INTO status_updates (agent_id, work_item_id, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (agent_id, work_item_id, status, message),
        )
        row = conn.execute(
            """
            SELECT su.*, a.name AS agent_name, wi.title AS work_item_title
            FROM status_updates su
            JOIN agents a ON a.id = su.agent_id
            LEFT JOIN work_items wi ON wi.id = su.work_item_id
            WHERE su.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


@mcp.tool()
def publish_finding(
    agent_name: str,
    title: str,
    body: str,
    agent_type: str = "unknown",
    work_item_id: int | None = None,
) -> dict:
    """Publish a reusable finding for other agents and the human operator."""
    agent_id = ensure_agent(agent_name, agent_type)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO findings (work_item_id, agent_id, title, body)
            VALUES (?, ?, ?, ?)
            """,
            (work_item_id, agent_id, title, body),
        )
        row = conn.execute(
            """
            SELECT f.*, a.name AS agent_name, wi.title AS work_item_title
            FROM findings f
            JOIN agents a ON a.id = f.agent_id
            LEFT JOIN work_items wi ON wi.id = f.work_item_id
            WHERE f.id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


@mcp.tool()
def list_peer_activity() -> dict:
    """Return recent findings and status updates from all agents."""
    with connect() as conn:
        findings = [
            dict(row)
            for row in conn.execute(
                """
                SELECT f.*, a.name AS agent_name, wi.title AS work_item_title
                FROM findings f
                JOIN agents a ON a.id = f.agent_id
                LEFT JOIN work_items wi ON wi.id = f.work_item_id
                ORDER BY f.created_at DESC, f.id DESC
                LIMIT 20
                """
            ).fetchall()
        ]
        statuses = [
            dict(row)
            for row in conn.execute(
                """
                SELECT su.*, a.name AS agent_name, wi.title AS work_item_title
                FROM status_updates su
                JOIN agents a ON a.id = su.agent_id
                LEFT JOIN work_items wi ON wi.id = su.work_item_id
                ORDER BY su.created_at DESC, su.id DESC
                LIMIT 20
                """
            ).fetchall()
        ]
    return {"findings": findings, "statuses": statuses}


def main() -> None:
    init_db()
    mcp.run()


if __name__ == "__main__":
    main()
