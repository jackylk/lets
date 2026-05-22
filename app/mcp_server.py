from mcp.server.fastmcp import FastMCP

from .db import connect, init_db

_mcp_kwargs = {
    "streamable_http_path": "/",
    "stateless_http": True,
}

try:
    from mcp.server.transport_security import TransportSecuritySettings
except ModuleNotFoundError:
    TransportSecuritySettings = None  # type: ignore[assignment]

if TransportSecuritySettings is not None:
    _mcp_kwargs["transport_security"] = TransportSecuritySettings(
        allowed_hosts=[
            "testserver",
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
            "lets.up.railway.app",
        ],
        allowed_origins=[
            "http://testserver",
            "http://localhost:*",
            "http://127.0.0.1:*",
            "https://lets.up.railway.app",
        ],
    )

mcp = FastMCP("Let's", **_mcp_kwargs)


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
    """Return the current Let's project context."""
    return {
        "project": {
            "name": "Let's",
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


# ---------------------------------------------------------------------------
# v1.5 tools — bridge agents to the typed-message + artifact world the
# web UI lives in. These read the calling principal from a contextvar set
# by the BearerAuthMiddleware (so the agent doesn't pass actor_id; the
# token itself identifies who they are).
# ---------------------------------------------------------------------------


def _require_agent_principal() -> dict:
    """Return the calling principal or raise. Agent-bound tokens only."""
    from .auth import get_mcp_principal

    p = get_mcp_principal()
    if p is None:
        raise ValueError("MCP call has no authenticated principal")
    if p.get("agent_instance_id") is None:
        raise ValueError(
            "this tool requires a token bound to an agent_instance "
            "(issue with --role and --device)"
        )
    return p


@mcp.tool()
def whoami() -> dict:
    """Return the human + agent_instance the calling Bearer token is bound to.

    Call this first on a new MCP connection so the agent knows its own
    identity. Returns ``{human_id, human_name, agent_instance_id, role,
    device_label}`` — fields that aren't set on the token come back as
    ``None``.
    """
    from .auth import get_mcp_principal

    p = get_mcp_principal()
    if p is None:
        raise ValueError("MCP call has no authenticated principal")
    out = {
        "human_id": p["human_id"],
        "agent_instance_id": p.get("agent_instance_id"),
        "token_id": p.get("token_id"),
    }
    with connect() as conn:
        if out["human_id"] is not None:
            row = conn.execute(
                "SELECT name FROM humans WHERE id = ?", (out["human_id"],)
            ).fetchone()
            out["human_name"] = row["name"] if row else None
        if out["agent_instance_id"] is not None:
            row = conn.execute(
                """
                SELECT ai.device_label, ai.model, ar.name AS role
                FROM agent_instances ai
                JOIN agent_roles ar ON ar.id = ai.role_id
                WHERE ai.id = ?
                """,
                (out["agent_instance_id"],),
            ).fetchone()
            if row:
                out["role"] = row["role"]
                out["device_label"] = row["device_label"]
                out["model"] = row["model"]
    return out


@mcp.tool()
def list_my_topics(limit: int = 50) -> list[dict]:
    """List topics visible to the calling human or agent, newest activity first.

    For each topic returns: ``{id, slug, title, project_id, project_slug,
    project_name, last_message_id, last_message_at, last_message_body}``.
    """
    from .auth import get_mcp_principal

    p = get_mcp_principal()
    if p is None:
        raise ValueError("MCP call has no authenticated principal")

    agent_id = p.get("agent_instance_id")
    if agent_id is not None:
        membership_predicate = """
            (
              t.workspace_id IS NULL OR EXISTS (
                SELECT 1
                FROM workspace_agent_members wam
                JOIN agent_instances ai ON ai.id = wam.agent_instance_id
                WHERE wam.workspace_id = t.workspace_id
                  AND wam.agent_instance_id = ?
                  AND ai.paused_at IS NULL
                  AND ai.deleted_at IS NULL
              )
            )
        """
        params: list[object] = [int(agent_id), limit]
    else:
        membership_predicate = """
            (
              t.workspace_id IS NULL OR EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.workspace_id = t.workspace_id AND wm.human_id = ?
              )
            )
        """
        params = [int(p["human_id"]), limit]

    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                t.id, t.slug, t.title, t.workspace_id AS project_id,
                w.slug AS project_slug, w.name AS project_name,
                m.id AS last_message_id,
                m.created_at AS last_message_at,
                m.body AS last_message_body
            FROM topics t
            LEFT JOIN workspaces w ON w.id = t.workspace_id
            LEFT JOIN messages m ON m.id = (
                SELECT MAX(id) FROM messages WHERE topic_id = t.id
            )
            WHERE {membership_predicate}
            ORDER BY COALESCE(m.created_at, t.created_at) DESC, t.id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _require_mcp_topic_actor(topic_id: int, principal: dict) -> None:
    with connect() as conn:
        row = conn.execute(
            "SELECT workspace_id FROM topics WHERE id = ?",
            (topic_id,),
        ).fetchone()
        if row is None:
            raise ValueError("topic not found")
        if row["workspace_id"] is None:
            return
        workspace_id = int(row["workspace_id"])
        agent_id = principal.get("agent_instance_id")
        if agent_id is not None:
            membership = conn.execute(
                """
                SELECT ai.paused_at, ai.deleted_at
                FROM workspace_agent_members wam
                JOIN agent_instances ai ON ai.id = wam.agent_instance_id
                WHERE wam.workspace_id = ? AND wam.agent_instance_id = ?
                """,
                (workspace_id, int(agent_id)),
            ).fetchone()
            if membership is None:
                raise ValueError("agent is not a member of this topic workspace")
            if membership["paused_at"] is not None:
                raise ValueError("agent is paused")
            if membership["deleted_at"] is not None:
                raise ValueError("agent is deleted")
            return
        membership = conn.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = ? AND human_id = ?
            """,
            (workspace_id, int(principal["human_id"])),
        ).fetchone()
        if membership is None:
            raise ValueError("human is not a member of this topic workspace")


@mcp.tool()
def read_topic(
    topic_id: int,
    after_id: int | None = None,
    limit: int = 100,
    order: str = "asc",
) -> list[dict]:
    """Read the typed message stream of a topic.

    Pass ``after_id`` to fetch only messages with ``id > after_id`` —
    use this for incremental polling.

    ``order='asc'`` (default) returns oldest-first, which is what tail
    polling wants. ``order='desc'`` returns newest-first; combined with
    ``limit`` this is how callers grab the most recent N messages on a
    long topic without missing the tail.
    """
    from .messages import topic_stream
    from .auth import get_mcp_principal

    p = get_mcp_principal()
    if p is None:
        raise ValueError("MCP call has no authenticated principal")
    _require_mcp_topic_actor(topic_id, p)
    return topic_stream(topic_id, after_id=after_id, limit=limit, order=order)


@mcp.tool()
async def post_typed_message(
    topic_id: int,
    type: str,
    body: str,
    metadata: dict | None = None,
    addressed_to: str | None = None,
) -> dict:
    """Post a typed message into a topic as the calling agent.

    ``type`` is one of the v1.5 typed-message kinds: chat, status,
    finding, decision, question, handoff, review, artifact_revision,
    spec_change, nudge, proactive_finding, task_tree_proposal,
    project_proposal, goal_proposal. ``actor_type`` is fixed to 'agent'
    and ``actor_id`` is taken from the calling token's agent_instance_id.
    ``addressed_to`` is a CSV of human IDs the agent wants to ping —
    those humans will see this message in their /api/attention queue.

    Also broadcasts to SSE subscribers so the web UI updates live.
    """
    import json as _json
    from .messages import post_message
    from .sse import broadcaster

    p = _require_agent_principal()
    _require_mcp_topic_actor(topic_id, p)
    msg_id = post_message(
        topic_id=topic_id,
        type=type,
        actor_type="agent",
        actor_id=p["agent_instance_id"],
        body=body,
        metadata=metadata,
        addressed_to=addressed_to,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        ).fetchone()
    message = dict(row)
    message["metadata"] = _json.loads(message["metadata"])
    await broadcaster.publish(topic_id, message)
    return message


@mcp.tool()
def create_artifact(
    topic_id: int,
    slug: str,
    type: str,
    title: str,
    content_b64: str,
    summary: str | None = None,
    backend: str = "git",
) -> dict:
    """Create a new artifact (PPT / doc / code / etc.) attached to a topic.

    ``content_b64`` is the base64-encoded initial bytes. The 'git' backend
    writes one file per artifact into ``LETS_GIT_REPO`` and commits.
    Returns ``{artifact, version}`` — version_label of the first revision
    is always 'v0'.
    """
    import base64 as _b64
    import os as _os
    from .artifacts.registry import get_adapter
    from .artifacts.models import (
        create_artifact_row, record_version, get_artifact_by_id,
    )

    _require_agent_principal()
    if backend != "git":
        raise ValueError("only 'git' backend supported in v1.5b")
    repo_path = _os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise ValueError("LETS_GIT_REPO not configured on this server")

    adapter = get_adapter("git", repo_path=repo_path)
    content = _b64.b64decode(content_b64)
    result = adapter.create(
        slug=slug, content=content,
        metadata={"type": type, "summary": summary or f"create {slug}"},
    )
    art_id = create_artifact_row(
        slug=slug, type=type, backend=backend,
        backend_ref=result.backend_ref, title=title, topic_id=topic_id,
    )
    v_id = record_version(
        artifact_id=art_id, version_label="v0",
        backend_revision_id=result.revision_id, summary=summary,
    )
    return {
        "artifact": get_artifact_by_id(art_id),
        "version": {
            "id": v_id, "version_label": "v0",
            "backend_revision_id": result.revision_id,
        },
    }


@mcp.tool()
def update_artifact(
    artifact_id: int,
    version_label: str,
    content_b64: str,
    summary: str | None = None,
) -> dict:
    """Add a new version to an existing artifact.

    Reads the artifact's ``backend_ref`` from the DB, hands new content
    to the configured backend (git: rewrites the file + commits), and
    records a new ``artifact_versions`` row with the agent's chosen
    semantic ``version_label`` (e.g. 'v1', 'v2-draft').
    """
    import base64 as _b64
    import os as _os
    from .artifacts.registry import get_adapter
    from .artifacts.models import record_version, get_artifact_by_id

    _require_agent_principal()
    art = get_artifact_by_id(artifact_id)
    if not art:
        raise ValueError("artifact not found")
    if art["backend"] != "git":
        raise ValueError("only 'git' backend supported in v1.5b")
    repo_path = _os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise ValueError("LETS_GIT_REPO not configured on this server")

    adapter = get_adapter("git", repo_path=repo_path)
    content = _b64.b64decode(content_b64)
    result = adapter.update(
        backend_ref=art["backend_ref"], content=content,
        metadata={"summary": summary or f"update {art['slug']} to {version_label}"},
    )
    v_id = record_version(
        artifact_id=artifact_id, version_label=version_label,
        backend_revision_id=result.revision_id, summary=summary,
    )
    return {
        "artifact": get_artifact_by_id(artifact_id),
        "version": {
            "id": v_id, "version_label": version_label,
            "backend_revision_id": result.revision_id,
        },
    }


@mcp.tool()
def propose_goal(
    topic_id: int,
    spec_text: str,
    artifact_id: int | None = None,
) -> dict:
    """Propose the final goal for a topic (artifact + spec). Posts a
    goal_proposal typed message; humans must adopt to make it active."""
    import json
    from .db import connect
    from .messages import post_message

    metadata = {
        "artifact_id": artifact_id,
        "spec_text": spec_text,
        "proposed_at": "now",
    }
    msg_id = post_message(
        topic_id=topic_id,
        type="goal_proposal",
        actor_type="agent",
        actor_id=None,
        body=spec_text,
        metadata=metadata,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        ).fetchone()
    msg = dict(row)
    if isinstance(msg.get("metadata"), str):
        msg["metadata"] = json.loads(msg["metadata"])
    return msg


@mcp.tool()
def propose_task_tree(
    topic_id: int,
    title: str,
    items: list[dict],
) -> dict:
    """Propose a hierarchical task breakdown for a topic.

    items is a list of {title, parent_index?, owner_human_id?,
    owner_agent_instance_id?}. parent_index is 0-based into the items
    list itself, used to express parent-child relations at adoption time.

    Posts a task_tree_proposal typed message; humans must adopt via
    POST /api/topics/{id}/task-tree to make it active."""
    import json
    from .db import connect
    from .messages import post_message

    body = f"提议把这个 topic 拆成 {len(items)} 个任务"
    metadata = {"title": title, "items": items}
    msg_id = post_message(
        topic_id=topic_id,
        type="task_tree_proposal",
        actor_type="agent",
        actor_id=None,
        body=body,
        metadata=metadata,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        ).fetchone()
    msg = dict(row)
    if isinstance(msg.get("metadata"), str):
        msg["metadata"] = json.loads(msg["metadata"])
    return msg


@mcp.tool()
def update_task_status(item_id: int, status: str) -> dict:
    """Update a task_item's status (pending|active|done). Posts a status
    typed message into the parent topic so the stream reflects the change."""
    import json
    from .db import connect
    from .messages import post_message
    from .task_trees import update_item

    if status not in ("pending", "active", "done"):
        raise ValueError(f"invalid status: {status}")
    updated = update_item(item_id, status=status)

    # Find the topic for the item's tree
    with connect() as conn:
        topic_row = conn.execute(
            """SELECT tt.topic_id
               FROM task_items ti
               JOIN task_trees tt ON tt.id = ti.task_tree_id
               WHERE ti.id = ?""",
            (item_id,),
        ).fetchone()
    if topic_row is None:
        return updated

    body = f"task {item_id} ({updated['title']}) → {status}"
    post_message(
        topic_id=int(topic_row["topic_id"]),
        type="status",
        actor_type="agent",
        actor_id=None,
        body=body,
        metadata={"task_item_id": item_id, "new_status": status},
    )
    return updated


@mcp.tool()
def post_nudge(
    topic_id: int,
    reason: str,
    drift_summary: str,
    triggered_by_agent_instance_id: int | None = None,
    window_start_message_id: int | None = None,
    window_end_message_id: int | None = None,
) -> dict:
    """Post a nudge typed message + record a drift_nudges row in one txn.

    Agents should only call this after consulting the drift_context
    in the topic_stream response and confirming the previous nudge
    wasn't 'dismissed'. See .claude/skills/lets-goal-guardian/SKILL.md."""
    from .drift import post_nudge as _post_nudge
    return _post_nudge(
        topic_id=topic_id,
        triggered_by_agent_instance_id=triggered_by_agent_instance_id,
        reason=reason,
        drift_summary=drift_summary,
        window_start_message_id=window_start_message_id,
        window_end_message_id=window_end_message_id,
    )


def main() -> None:
    """Stand-alone stdio entry, kept for backward compatibility."""
    init_db()
    mcp.run()


def get_http_app():
    """Return an ASGI app for FastMCP's streamable-http transport."""
    init_db()
    return mcp.streamable_http_app()


if __name__ == "__main__":
    main()
