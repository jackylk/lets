"""Backend API for the「导出 spec」UI button."""
from __future__ import annotations

import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="spec-test")
    return {"Authorization": f"Bearer {tok}"}


def test_spec_endpoint_renders_markdown_with_disposition(client, auth):
    """GET /api/topics/{id}/spec returns the same markdown the CLI produces,
    with content-disposition so the browser downloads it as a .md file."""
    from app.identity import ensure_human
    from app.db import connect
    me = ensure_human("Neo")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('spec-t', 'Spec T')")
        tid = c.lastrowid

    # Post a chat + a decision typed message with discussion_kind=decision
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid, "type": "chat", "actor_type": "human", "actor_id": me,
        "body": "let's go with X",
    })
    assert r.status_code == 200
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid, "type": "decision", "actor_type": "human", "actor_id": me,
        "body": "MVP locks scope to X",
        "metadata": {"discussion_kind": "decision"},
    })
    assert r.status_code == 200

    r = client.get(f"/api/topics/{tid}/spec", headers=auth)
    assert r.status_code == 200, r.text
    assert "text/markdown" in r.headers["content-type"]
    cd = r.headers.get("content-disposition", "")
    assert f"topic-{tid}-spec.md" in cd

    body = r.text
    assert f"# Topic #{tid}" in body
    assert "共识 (decisions)" in body
    assert "MVP locks scope to X" in body
    # The chat tail section must surface the chat message too.
    assert "let's go with X" in body


def test_spec_endpoint_404_on_missing_topic(client, auth):
    r = client.get("/api/topics/99999/spec", headers=auth)
    assert r.status_code == 404


def test_spec_endpoint_requires_auth(client):
    r = client.get("/api/topics/1/spec")
    assert r.status_code == 401
