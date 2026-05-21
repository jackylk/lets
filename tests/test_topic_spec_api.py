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


def test_spec_surfaces_per_node_diagram_annotations(client, auth):
    """Annotations with target_quote = node text should appear under the
    matching diagram in 图与资料 — both ±1 vote aggregates and free-form
    comments — so the downstream agent sees which nodes the team blessed
    vs. flagged."""
    from app.identity import ensure_human
    from app.db import connect
    me = ensure_human("Reviewer")
    other = ensure_human("Second")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('spec-d', 'D')")
        tid = c.lastrowid

    # Diagram message (human-authored chat — exporter looks at body only)
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid, "type": "chat", "actor_type": "human", "actor_id": me,
        "body": "架构：\n```mermaid\ngraph TD\nA[KB] --> B[Critique]\n```\n",
    })
    assert r.status_code == 200
    diagram_id = r.json()["id"]

    # Two humans vote +1 on KB (aggregate +2)
    for hid in (me, other):
        r = client.post("/api/messages", headers=auth, json={
            "topic_id": tid, "type": "annotation", "actor_type": "human", "actor_id": hid,
            "body": "",
            "metadata": {"target_message_id": diagram_id, "target_quote": "KB", "score": 1},
        })
        assert r.status_code == 200, r.text

    # One human -1 on Critique
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid, "type": "annotation", "actor_type": "human", "actor_id": me,
        "body": "",
        "metadata": {"target_message_id": diagram_id, "target_quote": "Critique", "score": -1},
    })
    assert r.status_code == 200

    # Free-form comment on KB
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid, "type": "annotation", "actor_type": "human", "actor_id": me,
        "body": "KB 要包含 tutor preferences",
        "metadata": {"target_message_id": diagram_id, "target_quote": "KB"},
    })
    assert r.status_code == 200

    r = client.get(f"/api/topics/{tid}/spec", headers=auth)
    assert r.status_code == 200, r.text
    body = r.text
    assert "## 图与资料" in body
    assert "节点评分" in body
    # KB has +2 from two voters
    assert "`+2` KB" in body
    # Critique has -1
    assert "`-1` Critique" in body
    # Comment surfaced
    assert "节点批注" in body
    assert "KB 要包含 tutor preferences" in body

