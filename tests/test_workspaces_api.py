import pytest


@pytest.fixture(autouse=True)
def enable_dev_sessions(monkeypatch):
    """Enable LETS_DEV_SESSIONS for all tests in this module."""
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name="alice", email=None):
    """Helper: dev-login as a human, return human_id."""
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_post_workspaces_creates(temp_db, client):
    _login(client)
    r = client.post("/api/workspaces", json={"name": "User Auth"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "User Auth"
    assert body["slug"] == "user-auth"
    assert body["my_role"] == "owner"


def test_get_workspaces_lists_only_mine(temp_db, client):
    alice_id = _login(client, "alice")
    client.post("/api/workspaces", json={"name": "Auth"})
    client.post("/api/auth/logout")
    bob_id = _login(client, "bob", "b@b")
    client.post("/api/workspaces", json={"name": "Bob WS"})
    r = client.get("/api/workspaces")
    names = [w["name"] for w in r.json()]
    assert "Bob WS" in names
    assert "Auth" not in names  # Alice's workspace, not visible to Bob


def test_patch_workspace_rename_owner_only(temp_db, client):
    _login(client, "alice")
    r = client.post("/api/workspaces", json={"name": "Old"})
    ws_id = r.json()["id"]
    r2 = client.patch(f"/api/workspaces/{ws_id}", json={"name": "New"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "New"


def test_patch_workspace_403_for_non_owner(temp_db, client):
    alice_id = _login(client, "alice")
    r = client.post("/api/workspaces", json={"name": "A"})
    ws_id = r.json()["id"]
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r2 = client.patch(f"/api/workspaces/{ws_id}", json={"name": "Hijack"})
    assert r2.status_code == 403


def test_delete_workspace_soft_delete(temp_db, client):
    _login(client, "alice")
    r1 = client.post("/api/workspaces", json={"name": "Keeper"})
    r2 = client.post("/api/workspaces", json={"name": "Disposable"})
    ws_id = r2.json()["id"]
    r3 = client.delete(f"/api/workspaces/{ws_id}")
    assert r3.status_code == 200
    r4 = client.get("/api/workspaces")
    names = [w["name"] for w in r4.json()]
    assert "Disposable" not in names
    assert "Keeper" in names


def test_delete_last_workspace_refused(temp_db, client):
    _login(client, "alice")
    # alice now has "我的工作区" auto-created; add "Only" so she has two
    r = client.post("/api/workspaces", json={"name": "Only"})
    ws_id = r.json()["id"]
    # Delete the auto-created workspace first, leaving "Only" as the last one
    all_ws = client.get("/api/workspaces").json()
    auto_ws = next(w for w in all_ws if w["name"] == "我的工作区")
    client.delete(f"/api/workspaces/{auto_ws['id']}")
    # Now deleting the last remaining workspace should be refused
    r2 = client.delete(f"/api/workspaces/{ws_id}")
    assert r2.status_code == 400
