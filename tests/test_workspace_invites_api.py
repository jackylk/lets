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


def test_accept_invite_adds_member(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == ws["id"]
    bobs = client.get("/api/workspaces").json()
    assert ws["id"] in [w["id"] for w in bobs]


def test_accept_invite_idempotent(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    client.post(f"/api/invites/{inv['token']}/accept")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 200
    client.post("/api/auth/logout")
    _login(client, "alice")
    invs = client.get(f"/api/workspaces/{ws['id']}/invites").json()
    assert invs[0]["used_count"] == 1


def test_accept_invite_revoked_token_404(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.delete(f"/api/invites/{inv['id']}")
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 404


def test_accept_invite_as_guest_creates_session_and_member(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")

    r = client.post(f"/api/invites/{inv['token']}/accept-guest", json={"name": "Bob"})
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == ws["id"]
    assert body["human"]["name"] == "Bob"
    assert body["human"]["is_guest"] is True
    assert "lets_session" in r.cookies

    me = client.get("/auth/me", cookies={"lets_session": r.cookies["lets_session"]})
    assert me.status_code == 200
    assert me.json()["human"]["is_guest"] is True

    mine = client.get("/api/workspaces", cookies={"lets_session": r.cookies["lets_session"]})
    assert ws["id"] in [w["id"] for w in mine.json()]


def test_accept_invite_as_guest_disambiguates_existing_name(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")

    first = client.post(f"/api/invites/{inv['token']}/accept-guest", json={"name": "Sam"})
    second = client.post(f"/api/invites/{inv['token']}/accept-guest", json={"name": "Sam"})
    assert first.json()["human"]["name"] == "Sam"
    assert second.json()["human"]["name"] == "Sam (2)"


def test_join_token_unauthenticated_returns_spa(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    r = client.get(f"/join/{inv['token']}", follow_redirects=False)
    assert r.status_code in (200, 307)


def test_join_token_authenticated_returns_spa(temp_db, client):
    """Authenticated /join/:token returns the SPA so JoinTokenPage can run accept client-side."""
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.get(f"/join/{inv['token']}", follow_redirects=False)
    # Either 200 (SPA HTML) or 307 (redirect to /app when frontend/dist exists)
    assert r.status_code in (200, 307)
    # The membership add does NOT happen on this GET — it's the SPA's accept call that does it.
    bobs_ws_before_accept = client.get("/api/workspaces").json()
    assert ws["id"] not in [w["id"] for w in bobs_ws_before_accept]
    # Simulate the SPA's accept call
    r2 = client.post(f"/api/invites/{inv['token']}/accept")
    assert r2.status_code == 200
    bobs_ws = client.get("/api/workspaces").json()
    assert ws["id"] in [w["id"] for w in bobs_ws]
