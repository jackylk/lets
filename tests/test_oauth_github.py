"""Track F Task 43 — GitHub OAuth + session cookie tests.

The endpoints under test are mounted directly on the FastAPI ``app``:

- ``GET  /auth/github/start``     — redirect to github.com with state
- ``GET  /auth/github/callback``  — exchange code -> set session cookie -> /app
- ``GET  /auth/me``               — return logged-in human or 401
- ``POST /auth/logout``           — revoke session and clear cookie

GitHub API access is mocked at the module level (``app.main._gh_exchange_code``
and ``app.main._gh_fetch_user``); no real HTTP egress is required.
"""
from __future__ import annotations

from unittest.mock import patch


def test_oauth_start_redirects_with_state(client, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")
    res = client.get("/auth/github/start", follow_redirects=False)
    assert res.status_code == 307
    loc = res.headers["location"]
    assert loc.startswith("https://github.com/login/oauth/authorize")
    assert "client_id=test_id" in loc
    assert "state=" in loc
    assert "scope=" in loc


def test_oauth_callback_creates_human_and_sets_session_cookie(client, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_secret")
    # Local http test client → don't require Secure cookies (would be dropped).
    monkeypatch.setenv("LETS_COOKIE_SECURE", "false")

    # Prime a state via /start so /callback accepts it.
    started = client.get("/auth/github/start", follow_redirects=False)
    loc = started.headers["location"]
    state = [
        p.split("=", 1)[1] for p in loc.split("?", 1)[1].split("&") if p.startswith("state=")
    ][0]

    fake_user = {
        "id": 12345,
        "login": "neo",
        "name": "Neo Anderson",
        "email": "neo@example.com",
        "avatar_url": "https://avatars.example/neo.png",
    }

    async def fake_token(*a, **kw):
        class R:
            status_code = 200

            def json(self):
                return {"access_token": "ghu_x"}

        return R()

    async def fake_user_get(*a, **kw):
        class R:
            status_code = 200

            def json(self):
                return fake_user

        return R()

    with patch("app.main._gh_exchange_code", new=fake_token), patch(
        "app.main._gh_fetch_user", new=fake_user_get
    ):
        res = client.get(
            f"/auth/github/callback?code=abc&state={state}",
            follow_redirects=False,
        )

    assert res.status_code == 307
    assert res.headers["location"] == "/app"
    assert "lets_session" in res.cookies

    me = client.get(
        "/auth/me", cookies={"lets_session": res.cookies["lets_session"]}
    )
    assert me.status_code == 200
    body = me.json()
    assert body["human"]["github_login"] == "neo"
    assert body["human"]["name"] == "Neo Anderson"


def test_logout_revokes_session(client, monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "x")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "y")
    # Seed a session directly via the auth helpers.
    from app.auth import issue_session
    from app.identity import ensure_human

    hid = ensure_human("Trinity")
    token = issue_session(hid)

    me = client.get("/auth/me", cookies={"lets_session": token})
    assert me.status_code == 200

    logout = client.post("/auth/logout", cookies={"lets_session": token})
    assert logout.status_code == 204

    me2 = client.get("/auth/me", cookies={"lets_session": token})
    assert me2.status_code == 401


def test_session_cookie_can_use_conversation_api(client, monkeypatch):
    """Browser sessions from GitHub OAuth can use the same REST API as the SPA."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human

    hid = ensure_human("Morpheus")
    session = issue_session(hid)
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('oauth-chat', 'OAuth Chat')"
        )
        topic_id = cur.lastrowid

    create = client.post(
        "/api/messages",
        cookies={"lets_session": session},
        json={
            "topic_id": topic_id,
            "type": "chat",
            "actor_type": "human",
            "actor_id": hid,
            "body": "hello from browser session",
        },
    )
    assert create.status_code == 200, create.text

    stream = client.get(
        f"/api/topics/{topic_id}/messages",
        cookies={"lets_session": session},
    )
    assert stream.status_code == 200
    assert [m["body"] for m in stream.json()] == ["hello from browser session"]
