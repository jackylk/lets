def test_drift_context_default_exploratory(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human

    hid = ensure_human("CtxHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('dctx-1', 'x')")
        tid = cur.lastrowid
    res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    body = res.json()
    assert isinstance(body, dict)
    assert "messages" in body
    assert "drift_context" in body
    ctx = body["drift_context"]
    assert ctx["topic_mode"] == "exploratory"
    assert ctx["active_task"] is None
    assert ctx["last_nudge_at"] is None
    assert ctx["last_nudge_message_id"] is None
    assert ctx["last_nudge_resolved_by"] is None
    assert ctx["messages_since_last_nudge"] == 0


def test_drift_context_after_nudge(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("CtxNudgeHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('dctx-n', 'x')")
        tid = cur.lastrowid
    # 1 chat, nudge, 2 chats
    post_message(topic_id=tid, type="chat", actor_type="human",
                 actor_id=hid, body="m1", metadata={})
    post_nudge(topic_id=tid, triggered_by_agent_instance_id=None,
               reason="drift", drift_summary="s")
    post_message(topic_id=tid, type="chat", actor_type="human",
                 actor_id=hid, body="m2", metadata={})
    post_message(topic_id=tid, type="chat", actor_type="human",
                 actor_id=hid, body="m3", metadata={})

    res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx = res.json()["drift_context"]
    assert ctx["last_nudge_message_id"] is not None
    assert ctx["messages_since_last_nudge"] == 2


def test_drift_context_active_task(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, add_item, update_item

    hid = ensure_human("CtxActive")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('dctx-act', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "Section 1")
    update_item(item["id"], status="active")
    res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx = res.json()["drift_context"]
    assert ctx["active_task"] is not None
    assert ctx["active_task"]["title"] == "Section 1"
