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


def test_topic_invite_adds_member_to_workspace_and_topic(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "private", "title": "Private"},
    ).json()
    inv = client.post(
        f"/api/workspaces/{ws['id']}/invites",
        json={"topic_id": topic["id"]},
    ).json()
    assert inv["topic_id"] == topic["id"]

    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 200
    assert r.json()["workspace_id"] == ws["id"]
    assert r.json()["topic_id"] == topic["id"]

    visible = client.get(f"/api/workspaces/{ws['id']}/topics?scope=all").json()
    assert topic["id"] in {t["id"] for t in visible}
    assert client.get(f"/api/topics/{topic['id']}/messages").status_code == 200


def test_topic_invite_existing_workspace_member_adds_topic_only(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "private", "title": "Private"},
    ).json()
    workspace_inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    topic_inv = client.post(
        f"/api/workspaces/{ws['id']}/invites",
        json={"topic_id": topic["id"]},
    ).json()

    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    assert client.post(f"/api/invites/{workspace_inv['token']}/accept").status_code == 200
    assert client.get(f"/api/topics/{topic['id']}/messages").status_code == 403

    accept = client.post(f"/api/invites/{topic_inv['token']}/accept")
    assert accept.status_code == 200
    assert accept.json()["topic_id"] == topic["id"]
    assert client.get(f"/api/topics/{topic['id']}/messages").status_code == 200

    client.post("/api/auth/logout")
    _login(client, "alice")
    invs = client.get(f"/api/workspaces/{ws['id']}/invites").json()
    used_by_token = {inv["token"]: inv["used_count"] for inv in invs}
    assert used_by_token[topic_inv["token"]] == 1


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


def test_authenticated_member_can_rename_self(temp_db, client):
    _login(client, "alice")

    r = client.patch("/auth/me", json={"name": "Alice Li"})
    assert r.status_code == 200
    assert r.json()["human"]["name"] == "Alice Li"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["human"]["name"] == "Alice Li"


def test_authenticated_member_rename_disambiguates_existing_name(temp_db, client):
    _login(client, "alice")
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO humans (name, email) VALUES ('bob', 'b@b')")

    r = client.patch("/auth/me", json={"name": "bob"})
    assert r.status_code == 200
    assert r.json()["human"]["name"] == "bob (2)"


def test_join_token_unauthenticated_returns_spa(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    r = client.get(f"/join/{inv['token']}", follow_redirects=False)
    assert r.status_code == 200
    assert "/app/assets/" in r.text or "web/index" not in r.text


def test_join_token_authenticated_returns_spa(temp_db, client):
    """Authenticated /join/:token returns the SPA so JoinTokenPage can run accept client-side."""
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.get(f"/join/{inv['token']}", follow_redirects=False)
    assert r.status_code == 200
    # The membership add does NOT happen on this GET — it's the SPA's accept call that does it.
    bobs_ws_before_accept = client.get("/api/workspaces").json()
    assert ws["id"] not in [w["id"] for w in bobs_ws_before_accept]
    # Simulate the SPA's accept call
    r2 = client.post(f"/api/invites/{inv['token']}/accept")
    assert r2.status_code == 200
    bobs_ws = client.get("/api/workspaces").json()
    assert ws["id"] in [w["id"] for w in bobs_ws]
