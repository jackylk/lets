def _make_topic(client, slug="t-legacy"):
    from app.db import connect

    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES (?, ?)", (slug, slug))
        return cursor.lastrowid


def _auth_header():
    from app.auth import issue_token
    from app.identity import ensure_human

    human_id = ensure_human("admin")
    token, _ = issue_token(human_id=human_id, label="legacy-compat-test")
    return {"Authorization": f"Bearer {token}"}


def test_legacy_status_also_mirrored_to_messages(client):
    work_item = client.post(
        "/api/work-items",
        json={"type": "task", "title": "T", "body": "B"},
    ).json()
    topic_id = _make_topic(client)

    response = client.post(
        "/api/status",
        json={
            "agent_name": "claude-test",
            "agent_type": "claude",
            "work_item_id": work_item["id"],
            "status": "active",
            "message": "starting",
            "topic_id": topic_id,
        },
    )
    assert response.status_code == 200

    messages = client.get(
        f"/api/topics/{topic_id}/messages?type=status",
        headers=_auth_header(),
    ).json()["messages"]
    assert len(messages) == 1
    assert messages[0]["type"] == "status"
    assert "starting" in messages[0]["body"]


def test_legacy_work_item_status_transition_mirrored(client):
    work_item = client.post(
        "/api/work-items",
        json={"type": "task", "title": "T", "body": "B"},
    ).json()
    topic_id = _make_topic(client, "t-transition")

    response = client.post(
        f"/api/work-items/{work_item['id']}/status",
        json={
            "agent_name": "claude-test",
            "agent_type": "claude",
            "status": "in_progress",
            "message": "moving",
            "topic_id": topic_id,
        },
    )
    assert response.status_code == 200

    messages = client.get(
        f"/api/topics/{topic_id}/messages?type=status",
        headers=_auth_header(),
    ).json()["messages"]
    assert len(messages) == 1
    assert messages[0]["metadata"]["work_item_id"] == work_item["id"]


def test_legacy_finding_mirrored(client):
    topic_id = _make_topic(client, "t-finding")
    response = client.post(
        "/api/findings",
        json={
            "agent_name": "claude-test",
            "agent_type": "claude",
            "work_item_id": None,
            "title": "F1",
            "body": "found",
            "topic_id": topic_id,
        },
    )
    assert response.status_code == 200

    messages = client.get(
        f"/api/topics/{topic_id}/messages?type=finding",
        headers=_auth_header(),
    ).json()["messages"]
    assert len(messages) == 1
    assert messages[0]["body"].startswith("F1")


def test_legacy_feedback_mirrored(client):
    topic_id = _make_topic(client, "t-fb")
    client.post(
        "/api/feedback",
        json={
            "feedback_type": "question",
            "body": "should we do X?",
            "topic_id": topic_id,
        },
    )

    messages = client.get(
        f"/api/topics/{topic_id}/messages?type=question",
        headers=_auth_header(),
    ).json()["messages"]
    assert len(messages) == 1
    assert "should we do X?" in messages[0]["body"]


def test_legacy_endpoints_still_work_without_topic_id(client):
    work_item = client.post(
        "/api/work-items",
        json={"type": "task", "title": "T", "body": "B"},
    ).json()
    response = client.post(
        "/api/status",
        json={
            "agent_name": "claude-test",
            "agent_type": "claude",
            "work_item_id": work_item["id"],
            "status": "active",
            "message": "hi",
        },
    )

    assert response.status_code == 200
