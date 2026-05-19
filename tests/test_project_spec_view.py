import base64
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="spec-test")
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture
def project_repo(tmp_path):
    """Materialize a fake project repo with CLAUDE.md + a skill + .mcp.json."""
    (tmp_path / "CLAUDE.md").write_text("# Project CLAUDE\n\nProject-level instructions.\n")
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {}}')
    skills_dir = tmp_path / ".claude" / "skills" / "demo-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Demo Skill\n")
    return tmp_path


def test_spec_view_no_repo_path_returns_404(client, auth):
    proj = client.post("/api/projects", headers=auth, json={"name": "NoRepo"}).json()
    r = client.get(f"/api/projects/{proj['id']}/spec", headers=auth)
    assert r.status_code == 404


def test_spec_view_lists_files(client, auth, project_repo):
    proj = client.post("/api/projects", headers=auth, json={
        "name": "WithRepo", "repo_path": str(project_repo)
    }).json()
    r = client.get(f"/api/projects/{proj['id']}/spec", headers=auth)
    assert r.status_code == 200
    data = r.json()
    paths = {f["path"] for f in data["files"]}
    assert "CLAUDE.md" in paths
    assert ".mcp.json" in paths
    assert ".claude/skills/demo-skill/SKILL.md" in paths


def test_spec_view_returns_file_content(client, auth, project_repo):
    proj = client.post("/api/projects", headers=auth, json={
        "name": "Content", "repo_path": str(project_repo)
    }).json()
    r = client.get(f"/api/projects/{proj['id']}/spec?include_content=true", headers=auth)
    assert r.status_code == 200
    data = r.json()
    files_by_path = {f["path"]: f for f in data["files"]}
    claude_md = files_by_path["CLAUDE.md"]
    assert "content_b64" in claude_md
    assert base64.b64decode(claude_md["content_b64"]).decode().startswith("# Project CLAUDE")


def test_spec_view_rejects_path_traversal(client, auth, tmp_path):
    """Even if a project has a repo_path, the API only reads under .claude/ etc.
    It must not be tricked into returning files outside repo_path."""
    (tmp_path / "CLAUDE.md").write_text("ok\n")
    proj = client.post("/api/projects", headers=auth, json={
        "name": "Safe", "repo_path": str(tmp_path)
    }).json()
    r = client.get(f"/api/projects/{proj['id']}/spec", headers=auth)
    data = r.json()
    for f in data["files"]:
        assert not f["path"].startswith("/")
        assert ".." not in f["path"]


def test_spec_view_404_for_unknown_project(client, auth):
    r = client.get("/api/projects/99999/spec", headers=auth)
    assert r.status_code == 404


def test_spec_view_requires_auth(client):
    r = client.get("/api/projects/1/spec")
    assert r.status_code == 401
