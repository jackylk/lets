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


def _auth_header():
    from app.auth import issue_token
    from app.identity import ensure_human

    human_id = ensure_human("admin")
    token, _ = issue_token(human_id=human_id, label="messages-test")
    return {"Authorization": f"Bearer {token}"}


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
        "edited_at",
        "edited_by_human_id",
        "edit_count",
        "deleted_at",
        "deleted_by_human_id",
        "deletion_kind",
        "deletion_reason",
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


def test_post_and_get_topic_messages_via_api(client):
    from app.db import connect

    headers = _auth_header()
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t-api', 'T API')")
        topic_id = cursor.lastrowid

    response = client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "chat",
            "actor_type": "human",
            "actor_id": 1,
            "body": "hello from api",
        },
    )
    assert response.status_code == 200
    assert response.json()["body"] == "hello from api"

    response2 = client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "finding",
            "actor_type": "agent",
            "actor_id": 7,
            "body": "found something",
            "metadata": {"finding_type": "observation"},
        },
    )
    assert response2.status_code == 200

    response3 = client.get(f"/api/topics/{topic_id}/messages", headers=headers)
    assert response3.status_code == 200
    messages = response3.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["body"] == "hello from api"
    assert messages[1]["type"] == "finding"
    assert messages[1]["metadata"]["finding_type"] == "observation"


def test_post_message_invalid_type_returns_400(client):
    from app.db import connect

    headers = _auth_header()
    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t-bad', 'T Bad')")
        topic_id = conn.execute("SELECT id FROM topics WHERE slug='t-bad'").fetchone()["id"]

    response = client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "bogus_type",
            "actor_type": "human",
            "actor_id": 1,
            "body": "x",
        },
    )

    assert response.status_code in (400, 422)


def test_get_topic_messages_type_filter(client):
    from app.db import connect

    headers = _auth_header()
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t-flt', 'T F')")
        topic_id = cursor.lastrowid

    for message_type in ("chat", "chat", "finding", "decision"):
        client.post(
            "/api/messages",
            headers=headers,
            json={
                "topic_id": topic_id,
                "type": message_type,
                "actor_type": "human",
                "actor_id": 1,
                "body": message_type,
            },
        )

    response = client.get(f"/api/topics/{topic_id}/messages?type=chat", headers=headers)
    assert response.status_code == 200
    body = response.json()["messages"]
    assert all(message["type"] == "chat" for message in body)
    assert len(body) == 2

    response2 = client.get(
        f"/api/topics/{topic_id}/messages?type=chat&type=decision",
        headers=headers,
    )
    assert response2.status_code == 200
    types = sorted(message["type"] for message in response2.json()["messages"])
    assert types == ["chat", "chat", "decision"]


def test_edit_message_updates_body_and_marks_agent_read(client):
    import uuid
    from app.db import connect

    headers = _auth_header()
    slug = f"t-edit-{uuid.uuid4().hex}"
    with connect() as conn:
        human_id = conn.execute("SELECT id FROM humans WHERE name = 'admin'").fetchone()["id"]
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES (?, 'T Edit')", (slug,))
        topic_id = cursor.lastrowid

    created = client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "chat",
            "actor_type": "human",
            "actor_id": human_id,
            "body": "helo",
        },
    )
    assert created.status_code == 200
    message_id = created.json()["id"]
    client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "chat",
            "actor_type": "agent",
            "actor_id": 7,
            "body": "I read that",
            "metadata": {"cites": [message_id]},
        },
    )

    edited = client.patch(
        f"/api/messages/{message_id}",
        headers=headers,
        json={"body": "hello"},
    )

    assert edited.status_code == 200
    body = edited.json()
    assert body["body"] == "hello"
    assert body["edited_at"] is not None
    assert body["edit_count"] == 1
    assert body["edited_after_agent_read"] is True


def test_retract_message_soft_deletes_with_tombstone(client):
    import uuid
    from app.db import connect

    headers = _auth_header()
    slug = f"t-retract-{uuid.uuid4().hex}"
    with connect() as conn:
        human_id = conn.execute("SELECT id FROM humans WHERE name = 'admin'").fetchone()["id"]
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES (?, 'T Retract')", (slug,))
        topic_id = cursor.lastrowid

    created = client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "chat",
            "actor_type": "human",
            "actor_id": human_id,
            "body": "wrong room",
        },
    )
    message_id = created.json()["id"]

    retracted = client.post(f"/api/messages/{message_id}/retract", headers=headers, json={})
    assert retracted.status_code == 200
    assert retracted.json()["body"] == "这条消息已撤回"
    assert retracted.json()["deletion_kind"] == "retracted"

    response = client.get(f"/api/topics/{topic_id}/messages", headers=headers)
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert messages[0]["body"] == "这条消息已撤回"
    assert messages[0]["metadata"] == {}

    with connect() as conn:
        stored = conn.execute("SELECT body FROM messages WHERE id = ?", (message_id,)).fetchone()
    assert stored["body"] == "wrong room"


def test_delete_message_soft_deletes_with_tombstone(client):
    import uuid
    from app.db import connect

    headers = _auth_header()
    slug = f"t-delete-{uuid.uuid4().hex}"
    with connect() as conn:
        human_id = conn.execute("SELECT id FROM humans WHERE name = 'admin'").fetchone()["id"]
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES (?, 'T Delete')", (slug,))
        topic_id = cursor.lastrowid

    created = client.post(
        "/api/messages",
        headers=headers,
        json={
            "topic_id": topic_id,
            "type": "chat",
            "actor_type": "human",
            "actor_id": human_id,
            "body": "remove me",
        },
    )
    message_id = created.json()["id"]

    deleted = client.delete(f"/api/messages/{message_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["body"] == "这条消息已删除"
    assert deleted.json()["deletion_kind"] == "deleted"
