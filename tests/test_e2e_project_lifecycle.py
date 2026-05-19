"""End-to-end: create project → set repo_path → add topics → post messages → list spec.

Exercises the full Track C1 surface (plus relies on Track A messages + Track B auth).
"""
from __future__ import annotations

import base64
import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="e2e-c1")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def project_repo(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Q3 PPT project\nGoals here.\n")
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {}}')
    skill_dir = tmp_path / ".claude" / "skills" / "research-talk-style"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Research talk style\nFont size: 14pt\n")
    return tmp_path


def test_e2e_project_lifecycle(client, auth, project_repo):
    # 1. Create project with repo_path
    create_resp = client.post("/api/projects", headers=auth, json={
        "name": "Q3 Review",
        "description": "Quarterly review PPT prep",
        "repo_path": str(project_repo),
    })
    assert create_resp.status_code == 200
    proj = create_resp.json()
    assert proj["slug"] == "q3-review"
    project_id = proj["id"]

    # 2. Add two topics
    t1 = client.post(
        f"/api/projects/{project_id}/topics",
        headers=auth,
        json={"slug": "ppt", "title": "Q3 PPT"},
    ).json()
    t2 = client.post(
        f"/api/projects/{project_id}/topics",
        headers=auth,
        json={"slug": "data", "title": "Q3 data prep"},
    ).json()

    # 3. List topics in project
    topics_resp = client.get(f"/api/projects/{project_id}/topics", headers=auth)
    assert topics_resp.status_code == 200
    topics = topics_resp.json()
    assert {t["slug"] for t in topics} == {"ppt", "data"}

    # 4. Post messages into the PPT topic
    from app.identity import ensure_human
    neo_hid = ensure_human("Neo")
    client.post("/api/messages", headers=auth, json={
        "topic_id": t1["id"],
        "type": "chat",
        "actor_type": "human",
        "actor_id": neo_hid,
        "body": "let's start the q3 ppt",
    })
    client.post("/api/messages", headers=auth, json={
        "topic_id": t1["id"],
        "type": "project_proposal",
        "actor_type": "human",
        "actor_id": neo_hid,
        "body": "proposal: q3-review project structure",
        "metadata": {"proposed_project_slug": "q3-review"},
    })

    # 5. Verify the message stream
    stream = client.get(f"/api/topics/{t1['id']}/messages", headers=auth).json()
    types = [m["type"] for m in stream]
    assert "chat" in types and "project_proposal" in types

    # 6. Project Spec view returns CLAUDE.md + skill
    spec_resp = client.get(f"/api/projects/{project_id}/spec?include_content=true", headers=auth)
    assert spec_resp.status_code == 200
    spec = spec_resp.json()
    paths = {f["path"] for f in spec["files"]}
    assert "CLAUDE.md" in paths
    assert ".claude/skills/research-talk-style/SKILL.md" in paths

    # 7. CLAUDE.md content decoded
    claude_md = next(f for f in spec["files"] if f["path"] == "CLAUDE.md")
    decoded = base64.b64decode(claude_md["content_b64"]).decode()
    assert "Q3 PPT project" in decoded
