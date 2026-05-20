def test_gateway_login_opens_browser_and_saves_token(monkeypatch, tmp_path, capsys):
    from app import gateway

    calls: list[tuple[str, str, str]] = []
    opened: list[str] = []

    def fake_http(host: str, method: str, path: str):
        calls.append((host, method, path))
        if path.startswith("/auth/device-flow/start"):
            return {
                "device_code": "dev-123",
                "user_code": "ABCD-1234",
                "verification_url": "https://lets.test/auth/device-flow/authorize?user_code=ABCD-1234",
                "interval": 0,
            }
        if path.startswith("/auth/device-flow/poll"):
            return {
                "status": "authorized",
                "token": "lets_test_token",
                "agent_instance": {
                    "id": 7,
                    "role": "claude",
                    "device_label": "neo-mbp",
                },
            }
        raise AssertionError(path)

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: opened.append(url) or True)

    rc = gateway.main([
        "login",
        "--host", "https://lets.test",
        "--role", "claude",
        "--device-label", "neo-mbp",
    ])

    assert rc == 0
    assert opened == ["https://lets.test/auth/device-flow/authorize?user_code=ABCD-1234"]
    assert (tmp_path / "token").read_text() == "lets_test_token"
    assert "Opened your browser" in capsys.readouterr().out
    assert calls[0][2].startswith("/auth/device-flow/start?")


def test_gateway_login_no_open(monkeypatch, tmp_path):
    from app import gateway

    opened: list[str] = []
    polls = 0

    def fake_http(host: str, method: str, path: str):
        nonlocal polls
        if path.startswith("/auth/device-flow/start"):
            return {
                "device_code": "dev-123",
                "user_code": "ABCD-1234",
                "verification_url": "https://lets.test/verify",
                "interval": 0,
            }
        if path.startswith("/auth/device-flow/poll"):
            polls += 1
            return {"status": "authorized", "token": "lets_test_token", "agent_instance": None}
        raise AssertionError(path)

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: opened.append(url) or True)

    rc = gateway.main(["login", "--host", "https://lets.test", "--no-open"])

    assert rc == 0
    assert opened == []
    assert polls == 1
