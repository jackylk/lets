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
    assert body["agent_instance"]["display_name"] == "Neo"

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


def test_delete_token_removes_agent_from_settings_list(client):
    session = _login(client)
    create = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "x", "role": "codex", "device_label": "neo-mbp"},
    )
    tid = create.json()["id"]
    agent_id = create.json()["agent_instance"]["id"]

    res = client.delete(f"/api/tokens/{tid}", cookies={"lets_session": session})
    assert res.status_code == 204

    listed = client.get("/api/tokens", cookies={"lets_session": session}).json()
    assert listed == []

    from app.db import connect

    with connect() as conn:
        agent = conn.execute(
            "SELECT deleted_at FROM agent_instances WHERE id = ?",
            (agent_id,),
        ).fetchone()
        token = conn.execute("SELECT 1 FROM tokens WHERE id = ?", (tid,)).fetchone()
    assert agent["deleted_at"] is not None
    assert token is None


def test_readding_removed_agent_creates_new_identity(client):
    session = _login(client)
    first = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "x", "role": "codex", "device_label": "neo-mbp"},
    )
    first_agent_id = first.json()["agent_instance"]["id"]
    first_token_id = first.json()["id"]

    assert client.delete(
        f"/api/tokens/{first_token_id}",
        cookies={"lets_session": session},
    ).status_code == 204

    second = client.post(
        "/api/tokens",
        cookies={"lets_session": session},
        json={"label": "x2", "role": "codex", "device_label": "neo-mbp"},
    )

    assert second.status_code == 201
    assert second.json()["agent_instance"]["id"] != first_agent_id
    assert second.json()["agent_instance"]["display_name"] == "Neo"


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


def test_update_codex_model_and_display_name(client):
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
        json={"model": "gpt-5-codex"},
    )
    name_res = client.patch(
        f"/api/agent-instances/{agent_id}",
        cookies={"lets_session": session},
        json={"display_name": "Oracle"},
    )

    assert model_res.status_code == 200
    assert model_res.json()["model"] == "gpt-5-codex"
    assert name_res.status_code == 200
