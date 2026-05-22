def _login(client) -> str:
    """Helper: seed Neo as a logged-in human, return session cookie value."""
    from app.identity import ensure_human
    from app.auth import issue_session
    hid = ensure_human("Neo")
    return issue_session(hid)


def test_list_tokens_requires_session(client):
    res = client.get("/api/tokens")
    assert res.status_code == 401


def test_list_tokens_returns_only_my_tokens(client):
    session = _login(client)
    res = client.get("/api/tokens", cookies={"lets_session": session})
    assert res.status_code == 200
    assert res.json() == []


def test_create_token_returns_raw_value_once(client):
    session = _login(client)
    res = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "claude on neo-mbp", "role": "claude", "device_label": "neo-mbp"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["value"].startswith("lets_")
    assert body["label"] == "claude on neo-mbp"
    assert body["agent_instance"]["role"] == "claude"
    assert body["agent_instance"]["device_label"] == "neo-mbp"

    # Subsequent list does NOT echo the raw value
    listed = client.get("/api/tokens", cookies={"lets_session": session}).json()
    assert len(listed) == 1
    assert "value" not in listed[0]
    assert listed[0]["label"] == "claude on neo-mbp"


def test_guest_cannot_create_agent_token(client):
    from app.auth import issue_session
    from app.db import connect

    with connect() as conn:
        row = conn.execute(
            "INSERT INTO humans (name, is_guest) VALUES ('Guest', TRUE) RETURNING id"
        ).fetchone()
    session = issue_session(int(row["id"]))

    res = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "x", "role": "claude", "device_label": "guest-laptop"},
    )
    assert res.status_code == 403


def test_revoke_token(client):
    session = _login(client)
    create = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "x", "role": "codex", "device_label": "neo-mbp"},
    )
    tid = create.json()["id"]

    res = client.delete(f"/api/tokens/{tid}", cookies={"lets_session": session})
    assert res.status_code == 204

    listed = client.get("/api/tokens", cookies={"lets_session": session}).json()
    assert listed[0]["revoked_at"] is not None


def test_update_agent_display_name(client):
    session = _login(client)
    create = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "codex on neo-mbp", "role": "codex", "device_label": "neo-mbp"},
    )
    agent_id = create.json()["agent_instance"]["id"]

    res = client.patch(
        f"/api/agent-instances/{agent_id}",
        cookies={"lets_session": session},
        json={"display_name": "Morpheus"},
    )

    assert res.status_code == 200
    assert res.json()["display_name"] == "Morpheus"


def test_update_codex_model_is_rejected_but_display_name_is_allowed(client):
    session = _login(client)
    create = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "codex on neo-mbp", "role": "codex", "device_label": "neo-mbp"},
    )
    agent_id = create.json()["agent_instance"]["id"]

    model_res = client.patch(
        f"/api/agent-instances/{agent_id}",
        cookies={"lets_session": session},
        json={"model": "sonnet"},
    )
    name_res = client.patch(
        f"/api/agent-instances/{agent_id}",
        cookies={"lets_session": session},
        json={"display_name": "Oracle"},
    )

    assert model_res.status_code == 400
    assert name_res.status_code == 200
