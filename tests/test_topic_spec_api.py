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


def test_share_link_exposes_public_read_only_spec(client, auth):
    from app.identity import ensure_human
    from app.db import connect

    me = ensure_human("Share Reviewer")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('spec-share', 'Share Spec')")
        tid = c.lastrowid

    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid,
        "type": "decision",
        "actor_type": "human",
        "actor_id": me,
        "body": "方案以 context pane 为活的设计纪要",
        "metadata": {"discussion_kind": "decision"},
    })
    assert r.status_code == 200, r.text

    r = client.post(
        f"/api/topics/{tid}/share",
        headers={**auth, "x-forwarded-proto": "https", "x-forwarded-host": "lets.example"},
        json={},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["url"].startswith("https://lets.example/s/")
    assert data["markdown_url"].endswith(".md")

    public_path = data["url"].replace("https://lets.example", "")
    page = client.get(public_path)
    assert page.status_code == 200, page.text
    assert "Design Spec" in page.text
    assert "方案以 context pane" in page.text

    md_path = data["markdown_url"].replace("https://lets.example", "")
    md = client.get(md_path)
    assert md.status_code == 200, md.text
    assert "text/markdown" in md.headers["content-type"]
    assert "共识 (decisions)" in md.text
    assert "方案以 context pane" in md.text


def test_share_link_requires_topic_member(client):
    from app.identity import ensure_human
    from app.auth import issue_token
    from app.db import connect

    owner = ensure_human("share-owner")
    outsider = ensure_human("share-outsider")
    outsider_token, _ = issue_token(human_id=outsider, label="outsider")
    with connect() as conn:
        ws = conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) VALUES ('share-ws', 'Share WS', ?) RETURNING id",
            (owner,),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) VALUES (?, ?, 'owner') RETURNING workspace_id",
            (ws, owner),
        )
        tid = conn.execute(
            "INSERT INTO topics (slug, title, workspace_id) VALUES ('share-private', 'Private', ?) RETURNING id",
            (ws,),
        ).fetchone()["id"]

    r = client.post(
        f"/api/topics/{tid}/share",
        headers={"Authorization": f"Bearer {outsider_token}"},
        json={},
    )
    assert r.status_code == 403


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
