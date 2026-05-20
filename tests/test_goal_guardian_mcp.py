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
