def test_resolve_nudge_dismissed(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("DismissHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('resnud-d', 'x')")
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid,
        triggered_by_agent_instance_id=None,
        reason="off-topic",
        drift_summary="discussing friday team dinner",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "dismissed"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_by"] == "dismissed"
    assert body["resolved_at"] is not None


def test_resolve_nudge_returned(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("ReturnHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('resnud-r', 'x')")
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid, triggered_by_agent_instance_id=None,
        reason="off", drift_summary="x",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "returned"},
    )
    assert res.status_code == 200
    assert res.json()["resolved_by"] == "returned"


def test_resolve_nudge_moved_to_topic_creates_new_topic(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("SpinoffHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (slug, name) VALUES ('p-spinoff', 'P')"
        )
        pid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO topics (slug, title, project_id) VALUES ('resnud-m', 'x', ?)",
            (pid,),
        )
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid, triggered_by_agent_instance_id=None,
        reason="off-topic", drift_summary="planning friday dinner at 7pm",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "moved_to_topic", "spinoff_title": "周五团建"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["resolved_by"] == "moved_to_topic"
    assert body["resolved_to_topic_id"] is not None

    # Verify the new topic has a system message with the drift_summary
    new_tid = body["resolved_to_topic_id"]
    with connect() as conn:
        topic_row = conn.execute(
            "SELECT slug, title, project_id FROM topics WHERE id = ?", (new_tid,)
        ).fetchone()
        msg_row = conn.execute(
            """SELECT body FROM messages
               WHERE topic_id = ? AND type = 'system' LIMIT 1""",
            (new_tid,),
        ).fetchone()
    assert topic_row["title"] == "周五团建"
    assert topic_row["project_id"] == pid
    assert "planning friday dinner" in msg_row["body"]


def test_resolve_nudge_missing_spinoff_title(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("MissingHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('resnud-miss', 'x')")
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid, triggered_by_agent_instance_id=None,
        reason="off", drift_summary="x",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "moved_to_topic"},  # no spinoff_title
    )
    assert res.status_code == 400
