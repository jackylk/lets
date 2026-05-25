def test_device_flow_authorizes_gateway_token(client):
    from app.auth import issue_session, verify_token
    from app.identity import ensure_human

    human_id = ensure_human("Device Human")
    session = issue_session(human_id)

    start = client.get(
        "/auth/device-flow/start?role=claude&device_label=device-mbp",
        headers={"host": "lets.test", "x-forwarded-proto": "https"},
    )
    assert start.status_code == 200
    started = start.json()
    assert started["verification_url"].startswith(
        "https://lets.test/auth/device-flow/authorize?user_code="
    )
    assert started["user_code"] in started["verification_url"]

    pending = client.get(
        "/auth/device-flow/poll",
        params={"device_code": started["device_code"]},
    )
    assert pending.status_code == 200
    assert pending.json() == {"status": "pending"}

    authz = client.get(
        "/auth/device-flow/authorize",
        params={"user_code": started["user_code"].lower()},
        cookies={"lets_session": session},
    )
    assert authz.status_code == 200
    assert "You're connected." in authz.text
    assert "claude · device-mbp" in authz.text

    done = client.get(
        "/auth/device-flow/poll",
        params={"device_code": started["device_code"]},
    )
    assert done.status_code == 200
    body = done.json()
    assert body["status"] == "authorized"
    assert body["token"].startswith("lets_")
    assert body["agent_instance"]["role"] == "claude"
    assert body["agent_instance"]["device_label"] == "device-mbp"
    assert body["agent_instance"]["human_name"] == "Device Human"

    principal = verify_token(body["token"])
    assert principal is not None
    assert principal["human_id"] == human_id
    assert principal["agent_instance_id"] == body["agent_instance"]["id"]

    consumed = client.get(
        "/auth/device-flow/poll",
        params={"device_code": started["device_code"]},
    )
    assert consumed.status_code == 410


def test_device_flow_authorize_requires_session(client):
    start = client.get("/auth/device-flow/start?role=codex&device_label=lab")
    res = client.get(
        "/auth/device-flow/authorize",
        params={"user_code": start.json()["user_code"]},
    )
    assert res.status_code == 401


def _login_or_seed_alice(client) -> int:
    """Log in as alice via the dev-login API and return the human_id."""
    import os
    os.environ.setdefault("LETS_DEV_SESSIONS", "1")
    r = client.post("/api/auth/dev-login", json={"name": "alice"})
    assert r.status_code == 200, r.text
    return r.json()["human_id"]


def test_device_flow_codex_defaults_model_to_gpt55(temp_db, client, monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    _login_or_seed_alice(client)

    r = client.post(
        "/api/auth/device-flow/start",
        params={"role": "codex", "device_label": "mac"},
    )
    assert r.status_code == 200
    user_code = r.json()["user_code"]
    auth = client.post(f"/api/auth/device-flow/authorize/{user_code}")
    assert auth.status_code == 200

    poll = client.get(f"/api/auth/device-flow/poll/{r.json()['device_code']}")
    assert poll.status_code == 200
    assert poll.json()["agent"]["model"] == "gpt-5.5"


def test_device_flow_cc_deepseek_keeps_model_unset_by_default(temp_db, client, monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    _login_or_seed_alice(client)

    r = client.post(
        "/api/auth/device-flow/start",
        params={"role": "cc-deepseek", "device_label": "mac"},
    )
    assert r.status_code == 200
    user_code = r.json()["user_code"]
    auth = client.post(f"/api/auth/device-flow/authorize/{user_code}")
    assert auth.status_code == 200

    poll = client.get(f"/api/auth/device-flow/poll/{r.json()['device_code']}")
    assert poll.status_code == 200
    agent = poll.json()["agent"]
    assert agent["role"] == "cc-deepseek"
    assert agent["model"] is None


def test_device_flow_with_workspace(temp_db, client, monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    alice_id = _login_or_seed_alice(client)
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(
        "/api/auth/device-flow/start",
        params={"role": "claude", "workspace_id": ws["id"]},
    )
    assert r.status_code == 200
    device_code = r.json()["device_code"]
    user_code = r.json()["user_code"]
    # Authorize via the JSON test endpoint
    auth = client.post(f"/api/auth/device-flow/authorize/{user_code}")
    assert auth.status_code == 200
    poll = client.get(f"/api/auth/device-flow/poll/{device_code}")
    assert poll.status_code == 200
    agent = poll.json()["agent"]
    assert agent["workspace_id"] == ws["id"]
    assert agent["human_name"] == "alice"
    from app import db
    with db.connect() as conn:
        membership = conn.execute(
            """
            SELECT 1 FROM workspace_agent_members
            WHERE workspace_id = ? AND agent_instance_id = ?
            """,
            (ws["id"], agent["id"]),
        ).fetchone()
    assert membership is not None


def test_device_flow_revives_deleted_agent_for_workspace(temp_db, client, monkeypatch):
    from app import db
    from app.auth import verify_token
    from app.identity import ensure_agent_instance

    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    alice_id = _login_or_seed_alice(client)
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    agent_id = ensure_agent_instance("codex", alice_id, "mac", workspace_id=ws["id"])

    deleted = client.delete(f"/api/agents/{agent_id}")
    assert deleted.status_code == 200

    start = client.post(
        "/api/auth/device-flow/start",
        params={"role": "codex", "device_label": "mac", "workspace_id": ws["id"]},
    )
    assert start.status_code == 200
    user_code = start.json()["user_code"]
    auth = client.post(f"/api/auth/device-flow/authorize/{user_code}")
    assert auth.status_code == 200
    poll = client.get(f"/api/auth/device-flow/poll/{start.json()['device_code']}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["agent"]["id"] == agent_id
    assert body["agent"]["workspace_id"] == ws["id"]
    assert verify_token(body["token"]) is not None

    with db.connect() as conn:
        row = conn.execute(
            "SELECT deleted_at, paused_at FROM agent_instances WHERE id = ?",
            (agent_id,),
        ).fetchone()
    assert row["deleted_at"] is None
    assert row["paused_at"] is None

    members = client.get(f"/api/workspaces/{ws['id']}/members")
    assert members.status_code == 200
    agents = [m for m in members.json() if m["kind"] == "agent"]
    assert [a["id"] for a in agents] == [agent_id]


def test_device_flow_defaults_to_caller_first_workspace(temp_db, client, monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    alice_id = _login_or_seed_alice(client)
    ws = client.post("/api/workspaces", json={"name": "MyWS"}).json()
    r = client.post(
        "/api/auth/device-flow/start", params={"role": "claude"}
    )
    user_code = r.json()["user_code"]
    client.post(f"/api/auth/device-flow/authorize/{user_code}")
    poll = client.get(f"/api/auth/device-flow/poll/{r.json()['device_code']}")
    agent = poll.json()["agent"]
    assert agent["workspace_id"] == ws["id"]
    from app import db
    with db.connect() as conn:
        membership = conn.execute(
            """
            SELECT 1 FROM workspace_agent_members
            WHERE workspace_id = ? AND agent_instance_id = ?
            """,
            (ws["id"], agent["id"]),
        ).fetchone()
    assert membership is not None
