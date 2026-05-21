import pytest


@pytest.fixture(autouse=True)
def _enable_dev_sessions(monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name="alice", email=None):
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_create_invite_returns_url(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(f"/api/workspaces/{ws['id']}/invites", json={})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert len(body["token"]) >= 20
    assert body["join_url"].endswith(f"/join/{body['token']}")


def test_list_invites_excludes_revoked(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.delete(f"/api/invites/{inv['id']}")
    listing = client.get(f"/api/workspaces/{ws['id']}/invites").json()
    assert listing == []


def test_create_invite_owner_only_403(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    # Add bob as a 'member' (not owner) so he passes basic membership check
    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], bob_id),
        )
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/workspaces/{ws['id']}/invites", json={})
    assert r.status_code == 403
