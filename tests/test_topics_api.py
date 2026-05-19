import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="topics-test")
    return {"Authorization": f"Bearer {tok}"}


def test_topics_helper_create(temp_db):
    """app.topics.create_topic creates a row."""
    from app.topics import create_topic
    from app.projects import create_project
    pid = create_project(name="P")
    tid = create_topic(slug="t1", title="Topic One", project_id=pid)
    assert isinstance(tid, int)


def test_topics_helper_get_by_slug_within_project(temp_db):
    from app.topics import create_topic, get_topic_by_slug
    from app.projects import create_project
    pid = create_project(name="P")
    create_topic(slug="t1", title="T1", project_id=pid)
    t = get_topic_by_slug("t1", project_id=pid)
    assert t["title"] == "T1"


def test_topics_helper_list_by_project(temp_db):
    from app.topics import create_topic, list_topics_by_project
    from app.projects import create_project
    pid = create_project(name="P")
    create_topic(slug="t1", title="T1", project_id=pid)
    create_topic(slug="t2", title="T2", project_id=pid)
    topics = list_topics_by_project(pid)
    slugs = {t["slug"] for t in topics}
    assert {"t1", "t2"} == slugs


def test_topics_helper_slug_collision_within_project_raises(temp_db):
    import pytest
    from app.topics import create_topic
    from app.projects import create_project
    pid = create_project(name="P")
    create_topic(slug="dupe", title="A", project_id=pid)
    with pytest.raises(ValueError, match="slug already in use"):
        create_topic(slug="dupe", title="B", project_id=pid)


def test_post_topic_in_project(client, auth):
    proj = client.post("/api/projects", headers=auth, json={"name": "P"}).json()
    r = client.post(
        f"/api/projects/{proj['id']}/topics",
        headers=auth,
        json={"slug": "t1", "title": "Topic One"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["slug"] == "t1"
    assert data["project_id"] == proj["id"]


def test_post_topic_unknown_project_404(client, auth):
    r = client.post(
        "/api/projects/99999/topics",
        headers=auth,
        json={"slug": "t", "title": "T"},
    )
    assert r.status_code == 404


def test_post_topic_slug_collision_within_project_400(client, auth):
    proj = client.post("/api/projects", headers=auth, json={"name": "P2"}).json()
    client.post(
        f"/api/projects/{proj['id']}/topics",
        headers=auth,
        json={"slug": "dupe", "title": "A"},
    )
    r = client.post(
        f"/api/projects/{proj['id']}/topics",
        headers=auth,
        json={"slug": "dupe", "title": "B"},
    )
    assert r.status_code == 400


def test_get_topics_in_project(client, auth):
    proj = client.post("/api/projects", headers=auth, json={"name": "P3"}).json()
    client.post(
        f"/api/projects/{proj['id']}/topics",
        headers=auth,
        json={"slug": "a", "title": "A"},
    )
    client.post(
        f"/api/projects/{proj['id']}/topics",
        headers=auth,
        json={"slug": "b", "title": "B"},
    )
    r = client.get(f"/api/projects/{proj['id']}/topics", headers=auth)
    assert r.status_code == 200
    topics = r.json()
    assert {t["slug"] for t in topics} == {"a", "b"}


def test_get_topic_by_id(client, auth):
    proj = client.post("/api/projects", headers=auth, json={"name": "P4"}).json()
    created = client.post(
        f"/api/projects/{proj['id']}/topics",
        headers=auth,
        json={"slug": "x", "title": "X"},
    ).json()
    r = client.get(f"/api/topics/{created['id']}", headers=auth)
    assert r.status_code == 200
    assert r.json()["title"] == "X"


def test_get_topic_404(client, auth):
    r = client.get("/api/topics/99999", headers=auth)
    assert r.status_code == 404


def test_topics_endpoints_require_auth(client):
    assert client.post("/api/projects/1/topics", json={"slug": "x", "title": "X"}).status_code == 401
    assert client.get("/api/projects/1/topics").status_code == 401
    assert client.get("/api/topics/1").status_code == 401
