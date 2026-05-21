import pytest


@pytest.fixture(autouse=True)
def _enable_dev_sessions(monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name="alice", email=None):
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_list_topics_requires_membership(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.get(f"/api/workspaces/{ws['id']}/topics")
    assert r.status_code == 403


def test_create_topic_member_allowed(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth 流程"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "OAuth 流程"


def test_create_topic_non_member_403(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth"},
    )
    assert r.status_code == 403
