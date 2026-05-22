import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="online-test")
    return {"Authorization": f"Bearer {tok}"}


def test_agents_online_empty(client, auth):
    r = client.get("/api/agents/online", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


def test_agents_online_requires_auth(client):
    r = client.get("/api/agents/online")
    assert r.status_code == 401


def test_agents_online_lists_recent_agent(client, auth):
    """An agent_instance with a token used in the last 5 minutes shows up."""
    from app.identity import ensure_human, ensure_agent_instance
    from app.auth import issue_token

    neo_hid = ensure_human("Neo")
    aid = ensure_agent_instance("claude", neo_hid, "neo-mbp")
    _, token_id = issue_token(human_id=neo_hid, agent_instance_id=aid, label="dev")

    from app.db import connect
    with connect() as conn:
        conn.execute(
            "UPDATE tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_id,),
        )

    r = client.get("/api/agents/online", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert any(a["agent_instance_id"] == aid for a in data), f"got {data}"
    me = next(a for a in data if a["agent_instance_id"] == aid)
    assert me["role"] == "claude"
    assert me["device_label"] == "neo-mbp"
    assert me["human_name"] == "Neo"


def test_agents_online_excludes_revoked(client, auth):
    from app.identity import ensure_human, ensure_agent_instance
    from app.auth import issue_token
    from app.db import connect

    neo_hid = ensure_human("Neo")
    aid = ensure_agent_instance("claude", neo_hid, "neo-mbp-2")
    tok, token_id = issue_token(human_id=neo_hid, agent_instance_id=aid, label="will-revoke")
    with connect() as conn:
        conn.execute(
            "UPDATE tokens SET last_used_at = CURRENT_TIMESTAMP, revoked_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_id,),
        )

    r = client.get("/api/agents/online", headers=auth)
    assert not any(a["agent_instance_id"] == aid for a in r.json())


def test_agents_online_excludes_stale(client, auth):
    """Token used >5min ago should not appear."""
    from app.identity import ensure_human, ensure_agent_instance
    from app.auth import issue_token
    from app.db import connect

    neo_hid = ensure_human("Neo")
    aid = ensure_agent_instance("claude", neo_hid, "neo-mbp-stale")
    tok, token_id = issue_token(human_id=neo_hid, agent_instance_id=aid, label="stale")
    with connect() as conn:
        conn.execute(
            "UPDATE tokens SET last_used_at = datetime('now', '-1 hour') WHERE id = ?",
            (token_id,),
        )

    r = client.get("/api/agents/online", headers=auth)
    assert not any(a["agent_instance_id"] == aid for a in r.json())
