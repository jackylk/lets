import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="goal-test")
    return {"Authorization": f"Bearer {tok}"}


def test_goal_proposal_accepted(client, auth):
    from app.identity import ensure_human
    from app.db import connect
    neo = ensure_human("Neo")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('g-t', 'G')")
        topic_id = c.lastrowid
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id, "type": "goal_proposal",
        "actor_type": "human", "actor_id": neo,
        "body": "goal: ship the q3 ppt by friday",
        "metadata": {"target_artifact_slug": "q3-ppt", "progress": 0.4},
    })
    assert r.status_code == 200, r.text
    assert r.json()["type"] == "goal_proposal"


def test_goal_proposal_in_topic_stream(client, auth):
    from app.identity import ensure_human
    from app.db import connect
    neo = ensure_human("Neo")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('g-t2', 'G2')")
        topic_id = c.lastrowid
    client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id, "type": "goal_proposal",
        "actor_type": "human", "actor_id": neo,
        "body": "goal", "metadata": {},
    })
    stream = client.get(f"/api/topics/{topic_id}/messages", headers=auth).json()["messages"]
    assert any(m["type"] == "goal_proposal" for m in stream)
