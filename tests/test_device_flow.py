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
    assert "Lets gateway authorized" in authz.text

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
