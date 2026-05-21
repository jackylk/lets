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


def test_patch_topic_moves_workspace(temp_db, client):
    _login(client, "alice")
    ws_a = client.post("/api/workspaces", json={"name": "A"}).json()
    ws_b = client.post("/api/workspaces", json={"name": "B"}).json()
    topic = client.post(
        f"/api/workspaces/{ws_a['id']}/topics",
        json={"slug": "oauth", "title": "OAuth"},
    ).json()
    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={"workspace_id": ws_b["id"]},
    )
    assert r.status_code == 200
    assert r.json()["workspace_id"] == ws_b["id"]


def test_patch_topic_403_if_not_member_of_target(temp_db, client):
    alice_id = _login(client, "alice")
    ws_a = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws_a['id']}/topics",
        json={"slug": "x", "title": "X"},
    ).json()
    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        bob_ws = conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES ('bob-ws', 'Bob WS', ?) RETURNING id",
            (bob_id,),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'owner') RETURNING workspace_id",
            (bob_ws, bob_id),
        )
    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={"workspace_id": bob_ws},
    )
    assert r.status_code == 403
