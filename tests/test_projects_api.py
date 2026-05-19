import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="api-test")
    return {"Authorization": f"Bearer {tok}"}


def test_post_project_requires_auth(client):
    r = client.post("/api/projects", json={"name": "X"})
    assert r.status_code == 401


def test_post_project_creates(client, auth):
    r = client.post("/api/projects", headers=auth, json={
        "name": "Hello World",
        "description": "first project",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["slug"] == "hello-world"
    assert data["name"] == "Hello World"
    assert data["description"] == "first project"


def test_post_project_with_explicit_slug(client, auth):
    r = client.post("/api/projects", headers=auth, json={
        "name": "Hello", "slug": "hi"
    })
    assert r.status_code == 200
    assert r.json()["slug"] == "hi"


def test_post_project_slug_collision_400(client, auth):
    client.post("/api/projects", headers=auth, json={"name": "A", "slug": "dupe"})
    r = client.post("/api/projects", headers=auth, json={"name": "B", "slug": "dupe"})
    assert r.status_code == 400
    assert "slug already in use" in r.json()["detail"]


def test_get_projects_lists(client, auth):
    client.post("/api/projects", headers=auth, json={"name": "Alpha"})
    client.post("/api/projects", headers=auth, json={"name": "Beta"})
    r = client.get("/api/projects", headers=auth)
    assert r.status_code == 200
    projects = r.json()
    slugs = {p["slug"] for p in projects}
    # 'default' from init_db + alpha + beta
    assert {"default", "alpha", "beta"}.issubset(slugs)


def test_get_projects_requires_auth(client):
    r = client.get("/api/projects")
    assert r.status_code == 401
