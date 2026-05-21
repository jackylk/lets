import os
import pytest


@pytest.fixture(autouse=True)
def _enable_dev_sessions(monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name="alice", email=None):
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_list_members_includes_owner(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.get(f"/api/workspaces/{ws['id']}/members")
    assert r.status_code == 200
    members = r.json()
    humans = [m for m in members if m["kind"] == "human"]
    assert len(humans) == 1
    assert humans[0]["role"] == "owner"


def test_list_members_includes_agents(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    from app.db import connect
    with connect() as conn:
        conn.execute(
            "INSERT INTO agent_roles (name) VALUES ('claude') ON CONFLICT DO NOTHING"
        )
        role_id = conn.execute(
            "SELECT id FROM agent_roles WHERE name='claude'"
        ).fetchone()["id"]
        # human_id 1 = alice (from her first dev-login)
        conn.execute(
            "INSERT INTO agent_instances (role_id, human_id, workspace_id, device_label) "
            "VALUES (?, ?, ?, 'mac')",
            (role_id, 1, ws["id"]),
        )
    r = client.get(f"/api/workspaces/{ws['id']}/members")
    agents = [m for m in r.json() if m["kind"] == "agent"]
    assert len(agents) == 1
    assert agents[0]["role"] == "claude"


def test_remove_member_owner_only(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], bob_id),
        )
    r = client.delete(f"/api/workspaces/{ws['id']}/members/{bob_id}")
    assert r.status_code == 200
    members = client.get(f"/api/workspaces/{ws['id']}/members").json()
    bob_rows = [m for m in members if m["kind"] == "human" and m["name"] == "bob"]
    assert bob_rows == []


def test_cannot_remove_owner(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.delete(f"/api/workspaces/{ws['id']}/members/{alice_id}")
    assert r.status_code == 400
