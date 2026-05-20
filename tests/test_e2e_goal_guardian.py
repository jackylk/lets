"""End-to-end scenario for Goal Guardian (spec §10).

Replays the full success criteria: propose tree → adopt → drift →
nudge (via MCP) → moved_to_topic spinoff → verify new topic + system
message + drift_context update on the original topic.
"""
from __future__ import annotations


def test_e2e_goal_guardian_full_scenario(client):
    """Replays the spec §10 success criteria as a pytest scenario."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human, ensure_agent_instance
    from app.mcp_server import (
        propose_task_tree,
        post_nudge as mcp_post_nudge,
    )
    from app.messages import post_message, topic_stream

    # 1. Neo sets up a topic in actionable mode
    neo = ensure_human("Neo")
    sess = issue_session(neo)
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO topics (slug, title, mode)
               VALUES ('e2e-gg', 'Goal Guardian E2E', 'actionable')"""
        )
        tid = cur.lastrowid

    # 2. claude proposes a 5-item task tree (1 has nested children)
    cc = ensure_agent_instance(role="claude", human_id=neo, device_label="neo-mbp")
    proposal = propose_task_tree(
        topic_id=tid,
        title="PPT Tree",
        items=[
            {"title": "Outline"},
            {"title": "Section 1", "parent_index": 0},
            {"title": "Section 1.1", "parent_index": 1},
            {"title": "Section 1.2", "parent_index": 1},
            {"title": "Section 2", "parent_index": 0},
        ],
    )

    # 3. Neo adopts → tree visible with hierarchy
    res = client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": proposal["id"]},
    )
    assert res.status_code == 201
    tree_response = res.json()
    assert len(tree_response["items"]) == 5
    # Item with parent_index=1 should have parent_item_id of items[1]
    items_by_title = {i["title"]: i for i in tree_response["items"]}
    assert items_by_title["Section 1.1"]["parent_item_id"] == items_by_title["Section 1"]["id"]

    # 4. Conversation drifts to team dinner (3+ chat messages)
    for body in ["顺便聊一下周五团建", "周五晚 7 点 OK 吗", "去那家烤肉店？"]:
        post_message(
            topic_id=tid, type="chat", actor_type="human",
            actor_id=neo, body=body, metadata={},
        )

    # 5. codex (different agent) reads drift_context, posts nudge
    cx = ensure_agent_instance(role="codex", human_id=neo, device_label="neo-mbp")
    stream_res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx = stream_res.json()["drift_context"]
    assert ctx["topic_mode"] == "actionable"
    assert ctx["messages_since_last_nudge"] >= 3

    nudge = mcp_post_nudge(
        topic_id=tid,
        reason="看起来话题漂到周五团建了，需要回主线吗？",
        drift_summary="周五团建",
        triggered_by_agent_instance_id=cx,
    )
    assert "nudge_message_id" in nudge

    # 6. Neo clicks "独立成新 topic" — verify the spinoff flow
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "moved_to_topic", "spinoff_title": "周五团建"},
    )
    assert res.status_code == 200
    body = res.json()
    new_topic_id = body["resolved_to_topic_id"]
    assert new_topic_id is not None
    assert new_topic_id != tid

    # 7. New topic has the expected system message with drift_summary
    with connect() as conn:
        sysmsg = conn.execute(
            """SELECT body FROM messages
               WHERE topic_id = ? AND type = 'system' LIMIT 1""",
            (new_topic_id,),
        ).fetchone()
        title_row = conn.execute(
            "SELECT title FROM topics WHERE id = ?", (new_topic_id,)
        ).fetchone()
    assert "周五团建" in sysmsg["body"]
    assert title_row["title"] == "周五团建"

    # 8. Original topic's drift_context now reflects resolution
    res2 = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx2 = res2.json()["drift_context"]
    assert ctx2["last_nudge_resolved_by"] == "moved_to_topic"
