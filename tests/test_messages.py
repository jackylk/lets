ALLOWED_TYPES = {
    "chat",
    "status",
    "finding",
    "decision",
    "question",
    "handoff",
    "review",
    "artifact_revision",
    "spec_change",
    "nudge",
    "proactive_finding",
    "task_tree_proposal",
    "system",
}


def test_messages_table_exists(temp_db):
    from app.db import connect

    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        ).fetchall()

    assert len(rows) == 1


def test_messages_columns(temp_db):
    from app.db import connect

    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    expected = {
        "id",
        "topic_id",
        "type",
        "actor_type",
        "actor_id",
        "body",
        "metadata",
        "ref_event_id",
        "created_at",
    }

    assert expected.issubset(cols)


def test_messages_type_check_rejects_unknown(temp_db):
    import sqlite3

    from app.db import connect

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1', 'T1')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
        try:
            conn.execute(
                """INSERT INTO messages
                   (topic_id, type, actor_type, actor_id, body)
                   VALUES (?, ?, ?, ?, ?)""",
                (topic_id, "not_a_real_type", "human", 1, "hello"),
            )
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass


def test_messages_accepts_all_known_types(temp_db):
    from app.db import connect

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1', 'T1')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
        for message_type in ALLOWED_TYPES:
            conn.execute(
                """INSERT INTO messages
                   (topic_id, type, actor_type, actor_id, body)
                   VALUES (?, ?, ?, ?, ?)""",
                (topic_id, message_type, "human", 1, f"hello {message_type}"),
            )
        count = conn.execute("SELECT COUNT(*) AS c FROM messages").fetchone()["c"]

    assert count == len(ALLOWED_TYPES)


def test_post_message_helper(temp_db):
    from app.db import connect
    from app.messages import post_message

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1', 'T1')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
    message_id = post_message(
        topic_id=topic_id,
        type="chat",
        actor_type="human",
        actor_id=1,
        body="hello",
        metadata={"flag": True},
    )

    assert isinstance(message_id, int)


def test_post_message_unknown_type_raises(temp_db):
    import pytest

    from app.db import connect
    from app.messages import post_message

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1', 'T1')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]

    with pytest.raises(ValueError, match="unknown message type"):
        post_message(
            topic_id=topic_id,
            type="bogus",
            actor_type="human",
            actor_id=1,
            body="x",
        )


def test_topic_stream_returns_in_order(temp_db):
    from app.db import connect
    from app.messages import post_message, topic_stream

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1', 'T1')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
    post_message(topic_id=topic_id, type="chat", actor_type="human", actor_id=1, body="first")
    post_message(topic_id=topic_id, type="chat", actor_type="human", actor_id=1, body="second")

    messages = topic_stream(topic_id, order="asc")

    assert [m["body"] for m in messages] == ["first", "second"]


def test_topic_stream_metadata_decoded(temp_db):
    from app.db import connect
    from app.messages import post_message, topic_stream

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1', 'T1')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
    post_message(
        topic_id=topic_id,
        type="status",
        actor_type="agent",
        actor_id=99,
        body="working",
        metadata={"work_item_id": 7},
    )

    messages = topic_stream(topic_id)

    assert messages[0]["metadata"]["work_item_id"] == 7
