def test_dev_login_disabled_by_default(client):
    res = client.get("/auth/dev/login", follow_redirects=False)
    assert res.status_code == 404


def test_dev_login_sets_session_cookie(monkeypatch, client):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    res = client.get(
        "/auth/dev/login?human=Local%20Tester&next=/app",
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert res.headers["location"] == "/app"
    assert "lets_session=" in res.headers["set-cookie"]

    cookie = res.cookies.get("lets_session")
    me = client.get("/auth/me", cookies={"lets_session": cookie})
    assert me.status_code == 200
    assert me.json()["human"]["name"] == "Local Tester"


def test_dev_login_rejects_external_redirect(monkeypatch, client):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")
    res = client.get(
        "/auth/dev/login?next=//evil.test",
        follow_redirects=False,
    )
    assert res.status_code == 307
    assert res.headers["location"] == "/app"
