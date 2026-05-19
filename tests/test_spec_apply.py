import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="apply-test")
    return {"Authorization": f"Bearer {tok}"}, hid


def test_spec_apply_writes_claude_md(client, auth, tmp_path):
    headers, _ = auth
    (tmp_path / "CLAUDE.md").write_text("old\n")
    proj = client.post("/api/projects", headers=headers, json={
        "name": "P", "repo_path": str(tmp_path)
    }).json()
    r = client.post(
        f"/api/projects/{proj['id']}/spec/apply",
        headers=headers,
        json={"file": "CLAUDE.md", "content": "new content\n"},
    )
    assert r.status_code == 200, r.text
    assert (tmp_path / "CLAUDE.md").read_text() == "new content\n"


def test_spec_apply_creates_nested_skill_file(client, auth, tmp_path):
    headers, _ = auth
    proj = client.post("/api/projects", headers=headers, json={
        "name": "P2", "repo_path": str(tmp_path)
    }).json()
    r = client.post(
        f"/api/projects/{proj['id']}/spec/apply",
        headers=headers,
        json={
            "file": ".claude/skills/research/SKILL.md",
            "content": "# Research skill\n",
        },
    )
    assert r.status_code == 200, r.text
    assert (tmp_path / ".claude" / "skills" / "research" / "SKILL.md").read_text().startswith("# Research")


def test_spec_apply_rejects_path_traversal(client, auth, tmp_path):
    headers, _ = auth
    (tmp_path / "CLAUDE.md").write_text("x\n")
    proj = client.post("/api/projects", headers=headers, json={
        "name": "PT", "repo_path": str(tmp_path)
    }).json()
    r = client.post(
        f"/api/projects/{proj['id']}/spec/apply",
        headers=headers,
        json={"file": "../../etc/passwd", "content": "bad"},
    )
    assert r.status_code == 400


def test_spec_apply_rejects_unmanaged_file(client, auth, tmp_path):
    """Only CLAUDE.md / .mcp.json / .claude/** are writable."""
    headers, _ = auth
    proj = client.post("/api/projects", headers=headers, json={
        "name": "PU", "repo_path": str(tmp_path)
    }).json()
    r = client.post(
        f"/api/projects/{proj['id']}/spec/apply",
        headers=headers,
        json={"file": "README.md", "content": "no"},
    )
    assert r.status_code == 400


def test_spec_apply_no_repo_path_404(client, auth):
    headers, _ = auth
    proj = client.post("/api/projects", headers=headers, json={"name": "NR"}).json()
    r = client.post(
        f"/api/projects/{proj['id']}/spec/apply",
        headers=headers,
        json={"file": "CLAUDE.md", "content": "x"},
    )
    assert r.status_code == 404


def test_spec_apply_requires_auth(client):
    r = client.post("/api/projects/1/spec/apply", json={"file": "x", "content": "y"})
    assert r.status_code == 401
