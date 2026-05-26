"""Track C1.5 Task 3 — context-pane endpoints.

Three endpoints:
  - GET /api/artifacts?topic_id=N      → list artifacts in that topic
  - GET /api/topics/{id}/participants  → distinct humans/agents who posted
  - GET /api/projects/{id}/git-status  → HEAD + dirty files
"""
from __future__ import annotations

import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="ctx-test")
    return {"Authorization": f"Bearer {tok}"}


def test_artifacts_by_topic(client, auth, tmp_path, monkeypatch):
    """GET /api/artifacts?topic_id=N returns artifacts in that topic only."""
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    monkeypatch.setenv("LETS_GIT_REPO", str(tmp_path))

    from app.db import connect
    with connect() as conn:
        c1 = conn.execute("INSERT INTO topics (slug, title) VALUES ('ctx-1', 'C1')")
        t1 = c1.lastrowid
        c2 = conn.execute("INSERT INTO topics (slug, title) VALUES ('ctx-2', 'C2')")
        t2 = c2.lastrowid

    import base64
    for tid, slug in ((t1, "a-1"), (t2, "a-2")):
        r = client.post("/api/artifacts", headers=auth, json={
            "topic_id": tid, "slug": slug, "type": "doc", "title": slug,
            "backend": "git",
            "content_b64": base64.b64encode(b"x").decode(),
        })
        assert r.status_code == 200, r.text

    r = client.get(f"/api/artifacts?topic_id={t1}", headers=auth)
    assert r.status_code == 200
    slugs = {a["slug"] for a in r.json()}
    assert slugs == {"a-1"}


def test_participants_endpoint(client, auth):
    from app.identity import ensure_agent_instance, ensure_human
    from app.messages import post_message
    from app.db import connect
    neo = ensure_human("Neo")
    trinity = ensure_human("Trinity")
    agent_id = ensure_agent_instance("codex", neo, "neo-mbp")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('p-t', 'P')")
        topic_id = c.lastrowid
    for hid in (neo, trinity, neo):  # Neo posts twice
        r = client.post("/api/messages", headers=auth, json={
            "topic_id": topic_id, "type": "chat", "actor_type": "human",
            "actor_id": hid, "body": "hi",
        })
        assert r.status_code == 200, r.text
    post_message(topic_id, "chat", "agent", agent_id, "agent reply")

    r = client.get(f"/api/topics/{topic_id}/participants", headers=auth)
    assert r.status_code == 200
    data = r.json()
    names = {p["name"] for p in data["humans"]}
    assert names == {"Neo", "Trinity"}
    assert {p["is_explicit"] for p in data["humans"]} == {True}
    assert data["agents"][0]["id"] == agent_id
    assert data["agents"][0]["device_label"] == "neo-mbp"
    assert data["agents"][0]["display_name"] == "Neo"
    assert data["agents"][0]["model"] is None
    assert data["agents"][0]["role"] == "codex"
    assert data["agents"][0]["human_name"] == "Neo"


def test_git_status_endpoint(client, auth, tmp_path):
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "f.txt").write_text("hello")
    subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )

    proj = client.post("/api/projects", headers=auth, json={
        "name": "G", "repo_path": str(tmp_path),
    }).json()
    r = client.get(f"/api/projects/{proj['id']}/git-status", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert "head" in data
    assert data["head"].get("subject") == "init"
    assert data["dirty"] == []


def test_git_status_no_repo_path_404(client, auth):
    proj = client.post("/api/projects", headers=auth, json={"name": "NoR"}).json()
    r = client.get(f"/api/projects/{proj['id']}/git-status", headers=auth)
    assert r.status_code == 404


def test_context_pane_endpoints_require_auth(client):
    assert client.get("/api/artifacts?topic_id=1").status_code == 401
    assert client.get("/api/topics/1/participants").status_code == 401
    assert client.get("/api/projects/1/git-status").status_code == 401
