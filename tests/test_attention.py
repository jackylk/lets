import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="att-test")
    return {"Authorization": f"Bearer {tok}"}, hid


def test_attention_requires_auth(client):
    r = client.get("/api/attention?human_id=1")
    assert r.status_code == 401


def test_attention_empty_when_no_messages(client, auth):
    headers, hid = auth
    r = client.get(f"/api/attention?human_id={hid}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data == {"needs_decision": [], "mentioned_questions": [], "suggestions": []}


def test_attention_needs_decision_includes_question_addressed_to_me(client, auth):
    headers, admin_hid = auth
    from app.identity import ensure_human
    from app.db import connect
    neo_hid = ensure_human("Neo")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('att-t1', 'T1')")
        topic_id = cur.lastrowid
        conn.execute(
            "INSERT INTO messages (topic_id, type, actor_type, actor_id, body, metadata, addressed_to) "
            "VALUES (?, 'question', 'human', ?, '?', '{}', ?)",
            (topic_id, neo_hid, str(admin_hid)),
        )
    r = client.get(f"/api/attention?human_id={admin_hid}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["needs_decision"]) == 1
    assert data["needs_decision"][0]["type"] == "question"


def test_attention_suggestions_includes_proactive_finding(client, auth):
    headers, admin_hid = auth
    from app.identity import ensure_human
    from app.db import connect
    neo_hid = ensure_human("Neo")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('att-t2', 'T2')")
        topic_id = cur.lastrowid
        conn.execute(
            "INSERT INTO messages (topic_id, type, actor_type, actor_id, body, metadata, addressed_to) "
            "VALUES (?, 'proactive_finding', 'agent', ?, 'hey', '{}', ?)",
            (topic_id, neo_hid, str(admin_hid)),
        )
    r = client.get(f"/api/attention?human_id={admin_hid}", headers=headers)
    data = r.json()
    assert len(data["suggestions"]) == 1


def test_attention_addressed_to_multi_id_csv(client, auth):
    """addressed_to='99,5,88' should match human_id=5 (in the middle)."""
    headers, admin_hid = auth
    from app.identity import ensure_human
    from app.db import connect
    neo_hid = ensure_human("Neo")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('att-t3', 'T3')")
        topic_id = cur.lastrowid
        conn.execute(
            "INSERT INTO messages (topic_id, type, actor_type, actor_id, body, metadata, addressed_to) "
            "VALUES (?, 'question', 'human', ?, 'q', '{}', ?)",
            (topic_id, neo_hid, f"99,{admin_hid},88"),
        )
    r = client.get(f"/api/attention?human_id={admin_hid}", headers=headers)
    assert len(r.json()["needs_decision"]) == 1
