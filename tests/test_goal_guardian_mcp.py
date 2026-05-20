def test_propose_goal_via_mcp(client):
    """Through MCP, propose_goal should insert a goal_proposal message."""
    from app.db import connect
    from app.mcp_server import propose_goal
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-pg', 'x')")
        tid = cur.lastrowid
    result = propose_goal(
        topic_id=tid,
        spec_text="30 分钟 talk · 技术受众",
        artifact_id=None,
    )
    assert result["topic_id"] == tid
    assert result["type"] == "goal_proposal"
    assert "30 分钟" in result["body"]
    assert result["metadata"]["spec_text"] == "30 分钟 talk · 技术受众"


def test_propose_task_tree_via_mcp(client):
    from app.db import connect
    from app.mcp_server import propose_task_tree
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-ptt', 'x')")
        tid = cur.lastrowid
    result = propose_task_tree(
        topic_id=tid,
        title="PPT Tree",
        items=[
            {"title": "Outline"},
            {"title": "P1", "parent_index": 0},
            {"title": "P2", "parent_index": 0},
        ],
    )
    assert result["type"] == "task_tree_proposal"
    assert result["metadata"]["title"] == "PPT Tree"
    assert len(result["metadata"]["items"]) == 3


def test_update_task_status_via_mcp(client):
    from app.db import connect
    from app.identity import ensure_human
    from app.mcp_server import update_task_status
    from app.task_trees import upsert_tree, add_item
    hid = ensure_human("MCPStatHuman")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-uts', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "section")
    result = update_task_status(item_id=item["id"], status="active")
    assert result["status"] == "active"
    # Also check a status typed message was posted for visibility
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE topic_id = ? AND type = 'status'", (tid,)
        ).fetchall()
    assert len(rows) >= 1


def test_post_nudge_via_mcp(client):
    from app.db import connect
    from app.mcp_server import post_nudge as mcp_post_nudge
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-pn', 'x')")
        tid = cur.lastrowid
    result = mcp_post_nudge(
        topic_id=tid,
        reason="off-topic for 5 minutes",
        drift_summary="discussion about friday team dinner",
    )
    assert "nudge_message_id" in result
    assert "drift_nudge_id" in result
    # Both rows exist
    with connect() as conn:
        msg = conn.execute(
            "SELECT type, body FROM messages WHERE id = ?",
            (result["nudge_message_id"],),
        ).fetchone()
        dnudge = conn.execute(
            "SELECT topic_id, drift_summary FROM drift_nudges WHERE id = ?",
            (result["drift_nudge_id"],),
        ).fetchone()
    assert msg["type"] == "nudge"
    assert dnudge["topic_id"] == tid
    assert "friday" in dnudge["drift_summary"]
