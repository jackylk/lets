def test_drift_nudges_table_exists(client):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(drift_nudges)").fetchall()}
    expected = {
        "id", "topic_id", "nudge_message_id", "triggered_by_agent_instance_id",
        "drift_window_start_message_id", "drift_window_end_message_id",
        "drift_summary", "resolved_at", "resolved_by", "resolved_to_topic_id",
        "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_drift_nudges_resolved_by_check(client):
    import sqlite3
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("Drift Test")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('drift-rb', 'x')")
        tid = cur.lastrowid
    mid = post_message(
        topic_id=tid, type="nudge",
        actor_type="system", actor_id=None,
        body="off topic", metadata={"reason": "test"},
    )
    with connect() as conn:
        try:
            conn.execute(
                """INSERT INTO drift_nudges (topic_id, nudge_message_id, resolved_by)
                   VALUES (?, ?, ?)""",
                (tid, mid, "bogus"),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised


def test_drift_nudges_nudge_message_id_unique(client):
    """A single message can back at most one drift_nudges row."""
    import sqlite3
    from app.db import connect
    from app.messages import post_message

    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('drift-uniq', 'x')")
        tid = cur.lastrowid
    mid = post_message(
        topic_id=tid, type="nudge",
        actor_type="system", actor_id=None,
        body="off topic", metadata={},
    )
    with connect() as conn:
        conn.execute(
            "INSERT INTO drift_nudges (topic_id, nudge_message_id) VALUES (?, ?)",
            (tid, mid),
        )
        try:
            conn.execute(
                "INSERT INTO drift_nudges (topic_id, nudge_message_id) VALUES (?, ?)",
                (tid, mid),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised
