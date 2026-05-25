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


def test_top_level_help_lists_commands_without_run_options(capsys):
    from app import gateway

    rc = gateway.main(["--help"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "usage: lets <command> [options]" in out
    assert "leave" in out
    assert "workspaces" in out
    assert "agents" in out
    assert "doctor" in out
    assert "logs" in out
    assert "update" in out
    assert "join" in out
    assert "model set" in out
    assert "retire" in out
    assert "--persona" not in out
    assert "--poll-interval" not in out


def test_run_help_does_not_expose_persona(capsys):
    import pytest
    from app import gateway

    with pytest.raises(SystemExit) as exc:
        gateway.main(["run", "--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "usage: lets run" in out
    assert "--persona" not in out


def test_gateway_topic_mode_helpers_default_and_validate():
    from app import gateway

    assert gateway._topic_agent_intervention_mode({}) == "auto"
    assert gateway._topic_agent_intervention_mode({"agent_intervention_mode": "mentions"}) == "mentions"
    assert gateway._topic_agent_intervention_mode({"agent_intervention_mode": "bogus"}) == "auto"
    assert gateway._topic_shared_context_mode({}) == "topic_with_files"
    assert gateway._topic_shared_context_mode({"shared_context_mode": "topic_only"}) == "topic_only"
    assert gateway._topic_shared_context_mode({"shared_context_mode": "bogus"}) == "topic_with_files"


def test_gateway_shared_context_section_lists_topic_attachments(monkeypatch):
    from app import gateway

    def fake_http(host, token, method, path, body=None):
        assert method == "GET"
        assert path == "/api/topics/42/attachments"
        return [
            {
                "kind": "image",
                "filename": "screen.png",
                "mime_type": "image/png",
                "byte_size": 123,
            }
        ]

    monkeypatch.setattr(gateway, "_http", fake_http)

    section = gateway._shared_context_section(
        "https://lets.test",
        "lets_token",
        42,
        "topic_with_files",
    )

    assert "Shared files/images" in section
    assert "screen.png" in section
    assert gateway._shared_context_section("https://lets.test", "lets_token", 42, "topic_only") == ""


def test_gateway_status_uses_human_name_and_human_id_fallback(monkeypatch, tmp_path, capsys):
    import json
    import os
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    (tmp_path / "token").write_text("lets_test_token")
    (tmp_path / "token.json").write_text(json.dumps({
        "host": "https://lets.test",
        "agent_instance": {
            "id": 7,
            "role": "codex",
            "device_label": "mac16",
            "owner_human_id": 1,
        },
    }))

    rc = gateway.main(["status"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "human=id:1" in out
    assert "gateway: not running (Run: lets gateway --agent codex)" in out

    locks_dir = tmp_path / "locks"
    locks_dir.mkdir(exist_ok=True)
    (locks_dir / "agent-7.lock").write_text(f"{os.getpid()}\n")

    rc = gateway.main(["status"])

    assert rc == 0
    assert f"gateway: running (pid {os.getpid()})" in capsys.readouterr().out

    (tmp_path / "token.json").write_text(json.dumps({
        "host": "https://lets.test",
        "agent_instance": {
            "id": 7,
            "role": "codex",
            "device_label": "mac16",
            "human_name": "Jacky Li",
            "owner_human_id": 1,
        },
    }))

    rc = gateway.main(["status"])

    assert rc == 0
    assert "human=Jacky Li" in capsys.readouterr().out


def test_gateway_turn_reuses_claude_session_by_topic_and_engine(monkeypatch, tmp_path):
    from app import gateway

    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str):
            self.stdout = stdout

    outputs = [
        Result('{"type":"result","session_id":"sess-1","result":"在"}'),
        Result('{"type":"result","session_id":"sess-1","result":"还在"}'),
    ]

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return outputs.pop(0)

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    me = gateway.Identity(
        human_id=1,
        human_name="Jacky Li",
        agent_instance_id=7,
        role="claude",
        device_label="mac16",
    )

    ok, text = gateway._invoke_agent_turn(
        cmd=["claude", "--print"],
        prompt="CC在吗",
        timeout=30,
        me=me,
        host="http://localhost:8000",
        topic_id=42,
        session_dir=str(tmp_path),
        trigger_message_id=100,
    )
    assert ok is True
    assert text == "在"
    assert calls[0] == ["claude", "--print", "--output-format", "json", "CC在吗"]

    ok, text = gateway._invoke_agent_turn(
        cmd=["claude", "--print"],
        prompt="继续",
        timeout=30,
        me=me,
        host="http://localhost:8000",
        topic_id=42,
        session_dir=str(tmp_path),
        trigger_message_id=101,
    )
    assert ok is True
    assert text == "还在"
    assert calls[1] == [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--resume",
        "sess-1",
        "继续",
    ]


def test_gateway_session_key_ignores_agent_instance_id(monkeypatch, tmp_path):
    from app import gateway

    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

        def __init__(self, stdout: str):
            self.stdout = stdout

    outputs = [
        Result('{"session_id":"shared-topic-session","result":"first"}'),
        Result('{"session_id":"shared-topic-session","result":"second"}'),
    ]

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return outputs.pop(0)

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)
    first = gateway.Identity(1, "Jacky Li", 7, "claude", "mac16")
    second = gateway.Identity(1, "Jacky Li", 8, "claude", "mac16-new-token")

    gateway._invoke_agent_turn(
        cmd=["claude", "--print"],
        prompt="first",
        timeout=30,
        me=first,
        host="http://localhost:8000",
        topic_id=42,
        session_dir=str(tmp_path),
    )
    gateway._invoke_agent_turn(
        cmd=["claude", "--print"],
        prompt="second",
        timeout=30,
        me=second,
        host="http://localhost:8000",
        topic_id=42,
        session_dir=str(tmp_path),
    )

    assert "--resume" in calls[1]
    assert "shared-topic-session" in calls[1]


def test_parse_agent_output_ignores_shell_noise_before_json():
    from app import gateway

    stdout = (
        "Restored session: 2026年 5月25日 星期一 17时23分01秒 CST\n"
        "\x1b]7;file://mac16/Users/jacky/.lets\x07"
        '{"type":"result","session_id":"sess-doubao","result":"当前方案总结：可以先做小验证。"}'
    )

    text, session_id = gateway._parse_agent_output(stdout)

    assert text == "当前方案总结：可以先做小验证。"
    assert session_id == "sess-doubao"


def test_lets_add_writes_per_role_token_and_starts_background(monkeypatch, tmp_path, capsys):
    """`lets add codex` should save tokens/codex.json (keeping any existing
    claude.json) and spawn a background gateway for that role."""
    from app import gateway
    import json

    monkeypatch.setenv("LETS_HOME", str(tmp_path))

    # Pre-seed a claude token so we can assert it is NOT clobbered.
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "claude.json").write_text(
        json.dumps({"host": "https://h", "token": "lets_claude_existing",
                    "agent_instance": {"id": 1, "role": "claude", "device_label": "mac"}})
    )

    def fake_http(host, method, path):
        if path.startswith("/auth/device-flow/start"):
            return {"device_code": "dc", "user_code": "X-Y",
                    "verification_url": "https://h/verify", "interval": 0}
        if path.startswith("/auth/device-flow/poll"):
            return {"status": "authorized", "token": "lets_codex_new",
                    "agent_instance": {"id": 2, "role": "codex", "device_label": "mac"}}
        raise AssertionError(path)

    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: True)

    spawns: list[tuple[str, str]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host)) or 12345,
    )

    rc = gateway.main(["add", "codex", "--host", "https://h", "--device-label", "mac"])
    assert rc == 0

    # Claude token preserved
    claude = json.loads((tmp_path / "tokens" / "claude.json").read_text())
    assert claude["token"] == "lets_claude_existing"
    # New codex token written
    codex = json.loads((tmp_path / "tokens" / "codex.json").read_text())
    assert codex["token"] == "lets_codex_new"
    assert codex["agent_instance"]["role"] == "codex"
    # Background gateway spawned for codex
    assert spawns == [("codex", "https://h")]


def test_lets_add_codex_passes_model_to_login_and_gateway(monkeypatch, tmp_path):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    start_paths: list[str] = []

    def fake_http(host, method, path):
        if path.startswith("/auth/device-flow/start"):
            start_paths.append(path)
            return {"device_code": "dc", "user_code": "X-Y",
                    "verification_url": "https://h/verify", "interval": 0}
        if path.startswith("/auth/device-flow/poll"):
            return {"status": "authorized", "token": "lets_codex_new",
                    "agent_instance": {
                        "id": 2,
                        "role": "codex",
                        "device_label": "mac",
                        "model": "gpt-5-codex",
                    }}
        raise AssertionError(path)

    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: True)

    spawns: list[tuple[str, str, list[str]]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host, extra)) or 12345,
    )

    rc = gateway.main([
        "add",
        "codex",
        "--host",
        "https://h",
        "--device-label",
        "mac",
        "--model",
        "gpt-5-codex",
    ])

    assert rc == 0
    assert "role=codex" in start_paths[0]
    assert "model=gpt-5-codex" in start_paths[0]
    assert spawns == [("codex", "https://h", ["--model", "gpt-5-codex"])]


def test_lets_add_codex_defaults_model_to_gpt55(monkeypatch, tmp_path):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    monkeypatch.delenv("LETS_MODEL", raising=False)
    start_paths: list[str] = []

    def fake_http(host, method, path):
        if path.startswith("/auth/device-flow/start"):
            start_paths.append(path)
            return {"device_code": "dc", "user_code": "X-Y",
                    "verification_url": "https://h/verify", "interval": 0}
        if path.startswith("/auth/device-flow/poll"):
            return {"status": "authorized", "token": "lets_codex_new",
                    "agent_instance": {
                        "id": 2,
                        "role": "codex",
                        "device_label": "mac",
                        "model": "gpt-5.5",
                    }}
        raise AssertionError(path)

    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: True)

    spawns: list[tuple[str, str, list[str]]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host, extra)) or 12345,
    )

    rc = gateway.main([
        "add",
        "codex",
        "--host",
        "https://h",
        "--device-label",
        "mac",
    ])

    assert rc == 0
    assert "role=codex" in start_paths[0]
    assert "model=gpt-5.5" in start_paths[0]
    assert spawns == [("codex", "https://h", ["--model", "gpt-5.5"])]


def test_lets_add_claude_defaults_model_to_opus47(monkeypatch, tmp_path):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    monkeypatch.delenv("LETS_MODEL", raising=False)
    start_paths: list[str] = []

    def fake_http(host, method, path):
        if path.startswith("/auth/device-flow/start"):
            start_paths.append(path)
            return {"device_code": "dc", "user_code": "X-Y",
                    "verification_url": "https://h/verify", "interval": 0}
        if path.startswith("/auth/device-flow/poll"):
            return {"status": "authorized", "token": "lets_claude_new",
                    "agent_instance": {
                        "id": 1,
                        "role": "claude",
                        "device_label": "mac",
                        "model": "claude-opus-4-7",
                    }}
        raise AssertionError(path)

    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: True)

    spawns: list[tuple[str, str, list[str]]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host, extra)) or 12345,
    )

    rc = gateway.main([
        "add",
        "claude",
        "--host",
        "https://h",
        "--device-label",
        "mac",
    ])

    assert rc == 0
    assert "role=claude" in start_paths[0]
    assert "model=claude-opus-4-7" in start_paths[0]
    assert spawns == [("claude", "https://h", ["--model", "claude-opus-4-7"])]


def test_lets_add_cc_doubao_does_not_force_model(monkeypatch, tmp_path):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    monkeypatch.delenv("LETS_MODEL", raising=False)
    start_paths: list[str] = []

    def fake_http(host, method, path):
        if path.startswith("/auth/device-flow/start"):
            start_paths.append(path)
            return {"device_code": "dc", "user_code": "X-Y",
                    "verification_url": "https://h/verify", "interval": 0}
        if path.startswith("/auth/device-flow/poll"):
            return {"status": "authorized", "token": "lets_doubao_new",
                    "agent_instance": {
                        "id": 3,
                        "role": "cc-doubao",
                        "device_label": "mac",
                    }}
        raise AssertionError(path)

    monkeypatch.setattr(gateway, "_http_public", fake_http)
    monkeypatch.setattr(gateway.webbrowser, "open", lambda url: True)
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: True)

    spawns: list[tuple[str, str, list[str]]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host, extra)) or 12345,
    )

    rc = gateway.main([
        "add",
        "cc-doubao",
        "--host",
        "https://h",
        "--device-label",
        "mac",
    ])

    assert rc == 0
    assert "role=cc-doubao" in start_paths[0]
    assert "model=" not in start_paths[0]
    assert spawns == [("cc-doubao", "https://h", [])]


def test_codex_command_includes_model():
    from app import gateway

    assert gateway._with_model(["codex", "exec"], "codex", "gpt-5-codex") == [
        "codex",
        "exec",
        "--model",
        "gpt-5-codex",
    ]


def test_cc_deepseek_command_can_include_explicit_model():
    from app import gateway

    assert gateway._with_model(["cc-deepseek", "--print"], "cc-deepseek", "deepseek-chat") == [
        "cc-deepseek",
        "--print",
        "--model",
        "deepseek-chat",
    ]


def test_lets_leave_removes_current_agent_from_workspace(monkeypatch, capsys):
    from app import gateway

    monkeypatch.setattr(
        gateway,
        "_load_token_for_agent",
        lambda role: {
            "host": "https://h",
            "token": "lets_codex",
            "agent_instance": {"id": 7, "role": "codex", "device_label": "mac"},
        },
    )
    calls: list[tuple[str, str, str]] = []

    def fake_http(host, token, method, path, body=None):
        calls.append((method, host, path))
        if method == "GET" and path == "/api/agents/me/memberships":
            return [
                {"id": 3, "slug": "my-ws", "name": "我的工作区"},
                {"id": 4, "slug": "other", "name": "Other"},
            ]
        if method == "DELETE" and path == "/api/workspaces/3/agent-members/7":
            return {"ok": True}
        raise AssertionError((method, path))

    monkeypatch.setattr(gateway, "_http", fake_http)

    rc = gateway.main(["leave", "--workspace", "my-ws", "--agent", "codex"])

    assert rc == 0
    assert calls == [
        ("GET", "https://h", "/api/agents/me/memberships"),
        ("DELETE", "https://h", "/api/workspaces/3/agent-members/7"),
    ]
    assert "codex:mac left workspace 我的工作区" in capsys.readouterr().out


def test_lets_workspaces_lists_current_agent_memberships(monkeypatch, capsys):
    from app import gateway

    monkeypatch.setattr(
        gateway,
        "_load_token_for_agent",
        lambda role: {
            "host": "https://h",
            "token": "lets_codex",
            "agent_instance": {"id": 7, "role": "codex", "device_label": "mac"},
        },
    )

    def fake_http(host, token, method, path, body=None):
        assert (method, host, path) == ("GET", "https://h", "/api/agents/me/memberships")
        return [
            {"id": 3, "slug": "my-ws", "name": "我的工作区"},
            {"id": 12, "slug": "research", "name": "Research"},
        ]

    monkeypatch.setattr(gateway, "_http", fake_http)

    rc = gateway.main(["workspaces", "--agent", "codex"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "ID" in out
    assert "SLUG" in out
    assert "my-ws" in out
    assert "我的工作区" in out
    assert "12" in out
    assert "research" in out


def test_lets_agents_lists_local_tokens_with_remote_status(monkeypatch, tmp_path, capsys):
    from app import gateway
    import json

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "codex.json").write_text(json.dumps({
        "host": "https://h",
        "token": "lets_codex",
        "agent_instance": {
            "id": 7,
            "role": "codex",
            "device_label": "mac",
            "model": "gpt-5-codex",
        },
    }))

    def fake_http(host, token, method, path, body=None):
        assert (host, token, method, path) == ("https://h", "lets_codex", "GET", "/api/agents/mine")
        return [{
            "agent_instance_id": 7,
            "role": "codex",
            "device_label": "mac",
            "model": "gpt-5-codex",
            "is_online": 1,
            "workspaces": [{"id": 3, "slug": "my-ws", "name": "我的工作区"}],
        }]

    monkeypatch.setattr(gateway, "_http", fake_http)

    rc = gateway.main(["agents"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "codex" in out
    assert "mac" in out
    assert "gpt-5-codex" in out
    assert "online" in out
    assert "my-ws" in out
    assert "codex.json" in out


def test_lets_model_set_updates_remote_and_local_token(monkeypatch, tmp_path, capsys):
    from app import gateway
    import json

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    (tmp_path / "tokens").mkdir()
    token_path = tmp_path / "tokens" / "codex.json"
    token_path.write_text(json.dumps({
        "host": "https://h",
        "token": "lets_codex",
        "agent_instance": {"id": 7, "role": "codex", "device_label": "mac"},
    }))
    calls = []

    def fake_http(host, token, method, path, body=None):
        calls.append((host, token, method, path, body))
        return {"id": 7, "model": "gpt-5-codex"}

    monkeypatch.setattr(gateway, "_http", fake_http)

    rc = gateway.main(["model", "set", "--agent", "codex", "--model", "gpt-5-codex"])

    assert rc == 0
    assert calls == [(
        "https://h",
        "lets_codex",
        "PATCH",
        "/api/agent-instances/7",
        {"model": "gpt-5-codex"},
    )]
    saved = json.loads(token_path.read_text())
    assert saved["agent_instance"]["model"] == "gpt-5-codex"
    assert "model set to gpt-5-codex" in capsys.readouterr().out


def test_lets_retire_deletes_remote_agent_and_local_token(monkeypatch, tmp_path, capsys):
    from app import gateway
    import json

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    (tmp_path / "tokens").mkdir()
    token_path = tmp_path / "tokens" / "codex.json"
    token_path.write_text(json.dumps({
        "host": "https://h",
        "token": "lets_codex",
        "agent_instance": {"id": 7, "role": "codex", "device_label": "mac"},
    }))
    calls = []

    def fake_http(host, token, method, path, body=None):
        calls.append((method, path))
        return {"ok": True}

    monkeypatch.setattr(gateway, "_http", fake_http)
    monkeypatch.setattr(gateway, "_stop_gateway_for_agent", lambda agent_id: False)

    rc = gateway.main(["retire", "--agent", "codex"])

    assert rc == 0
    assert calls == [("DELETE", "/api/agents/7")]
    assert not token_path.exists()
    out = capsys.readouterr().out
    assert "retired agent 7" in out
    assert "codex.json" in out


def test_lets_join_reuses_existing_agent_registration(monkeypatch):
    from app import gateway

    monkeypatch.setattr(
        gateway,
        "_load_token_for_agent",
        lambda role: {
            "host": "https://h",
            "token": "lets_codex",
            "agent_instance": {
                "id": 7,
                "role": "codex",
                "device_label": "mac",
                "model": "gpt-5-codex",
            },
        },
    )
    login_args = []
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: True)
    monkeypatch.setattr(gateway, "_login", lambda args: login_args.extend(args) or 0)

    rc = gateway.main(["join", "--workspace", "research", "--agent", "codex", "--no-open"])

    assert rc == 0
    assert login_args == [
        "--host", "https://h",
        "--role", "codex",
        "--device-label", "mac",
        "--workspace", "research",
        "--model", "gpt-5-codex",
        "--no-open",
    ]


def test_lets_add_fails_when_local_cli_is_missing(monkeypatch):
    from app import gateway

    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: False)
    calls: list[str] = []
    monkeypatch.setattr(gateway, "_login", lambda args: calls.append("login") or 0)

    rc = gateway.main(["add", "codex", "--host", "https://h"])

    assert rc == 2
    assert calls == []


def test_local_cli_preflight_reports_missing_executable(monkeypatch, capsys):
    from app import gateway

    monkeypatch.setattr(gateway.shutil, "which", lambda executable: None)
    monkeypatch.setattr(gateway, "_shell_resolves_command", lambda executable: False)

    assert gateway._require_local_cli_for_role("codex") is False
    assert "Local 'codex' CLI not found on PATH" in capsys.readouterr().err


def test_local_cli_preflight_accepts_shell_function(monkeypatch):
    from app import gateway

    monkeypatch.setattr(gateway.shutil, "which", lambda executable: None)
    monkeypatch.setattr(gateway, "_shell_resolves_command", lambda executable: executable == "cc-deepseek")

    assert gateway._require_local_cli_for_role("cc-deepseek") is True


def test_cc_deepseek_uses_claude_adapter_and_shell_wrapper(monkeypatch):
    from app import gateway

    monkeypatch.setattr(gateway.shutil, "which", lambda executable: None)
    monkeypatch.setattr(gateway, "_shell_resolves_command", lambda executable: executable == "cc-deepseek")

    cmd = gateway._agent_command(
        ["cc-deepseek", "--print"],
        "cc-deepseek",
        "sess-1",
        "PERSONA",
    )

    assert cmd == [
        "zsh",
        "-ic",
        'cc-deepseek "$@"',
        "cc-deepseek",
        "--print",
        "--output-format",
        "json",
        "--resume",
        "sess-1",
        "--append-system-prompt",
        "PERSONA",
    ]


def test_lets_join_fails_when_saved_agent_cli_is_missing(monkeypatch):
    from app import gateway

    monkeypatch.setattr(
        gateway,
        "_load_token_for_agent",
        lambda role: {
            "host": "https://h",
            "token": "lets_codex",
            "agent_instance": {"id": 7, "role": "codex", "device_label": "mac"},
        },
    )
    monkeypatch.setattr(gateway, "_require_local_cli_for_role", lambda role: False)
    calls: list[str] = []
    monkeypatch.setattr(gateway, "_login", lambda args: calls.append("login") or 0)

    rc = gateway.main(["join", "--workspace", "research", "--agent", "codex"])

    assert rc == 2
    assert calls == []


def test_lets_logs_prints_agent_log(monkeypatch, tmp_path, capsys):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "gateway-codex.out.log").write_text("one\ntwo\nthree\n")

    rc = gateway.main(["logs", "--agent", "codex", "--lines", "2"])

    assert rc == 0
    assert capsys.readouterr().out == "two\nthree\n"


def test_lets_update_downloads_gateway(monkeypatch, tmp_path, capsys):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    monkeypatch.setattr(gateway, "_download_text", lambda host, path: "# new gateway\n")

    rc = gateway.main(["update", "--host", "https://h"])

    assert rc == 0
    assert (tmp_path / "gateway.py").read_text() == "# new gateway\n"
    assert "updated" in capsys.readouterr().out


def test_urlopen_uses_proxy_only_for_public_hosts(monkeypatch):
    import urllib.request

    from app import gateway

    calls: list[str] = []

    class Opener:
        def __init__(self, name: str):
            self.name = name

        def open(self, req, timeout):
            calls.append(self.name)
            return object()

    monkeypatch.setattr(gateway, "_DEFAULT_OPENER", Opener("default"))
    monkeypatch.setattr(gateway, "_DIRECT_OPENER", Opener("direct"))

    gateway._urlopen(urllib.request.Request("http://localhost:8000/health"))
    gateway._urlopen(urllib.request.Request("https://lets.up.railway.app/install/gateway.py"))

    assert calls == ["direct", "default"]


def test_lets_doctor_reports_missing_tokens(monkeypatch, tmp_path, capsys):
    from app import gateway

    monkeypatch.setenv("LETS_HOME", str(tmp_path))

    rc = gateway.main(["doctor"])

    assert rc == 1
    out = capsys.readouterr().out
    assert "local_agents: 0" in out
    assert "ERROR no local tokens" in out


def test_lets_gateway_with_agent_picks_per_role_token(monkeypatch, tmp_path):
    """`lets gateway --agent codex` should resolve tokens/codex.json and
    spawn one background gateway for that role only."""
    from app import gateway
    import json

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    (tmp_path / "tokens").mkdir()
    (tmp_path / "tokens" / "claude.json").write_text(
        json.dumps({"host": "https://h", "token": "lets_c",
                    "agent_instance": {"id": 1, "role": "claude", "device_label": "mac"}})
    )
    (tmp_path / "tokens" / "codex.json").write_text(
        json.dumps({"host": "https://h", "token": "lets_x",
                    "agent_instance": {"id": 2, "role": "codex", "device_label": "mac"}})
    )

    spawns: list[tuple[str, str]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host)) or 1,
    )

    rc = gateway.main(["gateway", "--agent", "codex"])
    assert rc == 0
    assert spawns == [("codex", "https://h")]


def test_lets_gateway_no_agent_starts_all(monkeypatch, tmp_path):
    from app import gateway
    import json

    monkeypatch.setenv("LETS_HOME", str(tmp_path))
    (tmp_path / "tokens").mkdir()
    for role, tok in (("claude", "lets_c"), ("codex", "lets_x")):
        (tmp_path / "tokens" / f"{role}.json").write_text(
            json.dumps({"host": "https://h", "token": tok,
                        "agent_instance": {"id": 1, "role": role, "device_label": "mac"}})
        )

    spawns: list[tuple[str, str]] = []
    monkeypatch.setattr(
        gateway,
        "_spawn_background_for",
        lambda role, host, extra: spawns.append((role, host)) or 1,
    )
    rc = gateway.main(["gateway"])
    assert rc == 0
    assert set(spawns) == {("claude", "https://h"), ("codex", "https://h")}


def test_gateway_turn_retries_without_resume_when_session_is_stale(monkeypatch, tmp_path):
    """If `claude --resume <sid>` fails with 'No conversation found', the
    gateway should drop the stale session and retry without --resume."""
    from app import gateway
    import json

    # Pre-seed a saved session that the local CLI will reject.
    sess_dir = tmp_path
    me = gateway.Identity(
        human_id=1, human_name="Jacky",
        agent_instance_id=7, role="claude",
        device_label="mac",
    )
    gateway._save_session(
        str(sess_dir), "http://h", 42, "claude", "stale-sid",
        last_message_id=99,
    )

    class R:
        def __init__(self, code, out="", err=""):
            self.returncode = code; self.stdout = out; self.stderr = err

    outputs = [
        R(1, "", "No conversation found with session ID: stale-sid"),
        R(0, '{"type":"result","session_id":"fresh-sid","result":"pong"}', ""),
    ]
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return outputs.pop(0)

    monkeypatch.setattr(gateway.subprocess, "run", fake_run)

    ok, text = gateway._invoke_agent_turn(
        cmd=["claude", "--print"],
        prompt="ping",
        timeout=30,
        me=me,
        host="http://h",
        topic_id=42,
        session_dir=str(sess_dir),
    )
    assert ok, text
    assert text == "pong"
    # First call had --resume stale-sid; second did not.
    assert "--resume" in calls[0] and "stale-sid" in calls[0]
    assert "--resume" not in calls[1]
    # Stale cache file was removed, and fresh session saved.
    saved = gateway._load_session(str(sess_dir), "http://h", 42, "claude")
    assert saved and saved["session_id"] == "fresh-sid"


# ─── Slice 2c: pane_updates parsing & posting ─────────────────────────


def test_parse_pane_updates_strips_fence_and_returns_dict():
    from app.gateway import _parse_pane_updates

    raw = """那大致两条路：
- SAML 复用现有 IdP
- OIDC + 新建 IdP

<pane_updates>
{
  "options": [
    {"title": "A. SAML 接入", "body": "成熟、可复用 IdP",
     "pros": ["桌面成熟"], "cons": ["移动弱"]}
  ],
  "constraints": [{"body": "用户规模 2 万"}]
}
</pane_updates>
"""
    chat, updates = _parse_pane_updates(raw)
    assert "<pane_updates>" not in chat
    assert "SAML 复用现有 IdP" in chat
    assert updates["options"][0]["title"] == "A. SAML 接入"
    assert updates["constraints"][0]["body"] == "用户规模 2 万"


def test_parse_pane_updates_no_fence_passes_through():
    from app.gateway import _parse_pane_updates

    chat, updates = _parse_pane_updates("just a reply, no JSON")
    assert chat == "just a reply, no JSON"
    assert updates == {}


def test_fallback_pane_updates_extracts_design_sections():
    from app.gateway import _fallback_pane_updates

    updates = _fallback_pane_updates(
        """
我先把这个想法拆成三块。

**目标**

做一个支持自然语言的文件检索工具，让用户不用记文件名也能找文件。

**候选方案**

1. 传统关键词搜索增强版
基于文件名、路径、正文索引，再加自然语言 query rewrite。

2. Embedding 语义检索
把文件内容切块后向量化，按语义相似度召回。

**风险**

- 权限和隐私边界容易做错。
"""
    )

    assert updates["decisions"][0]["body"].startswith("做一个支持自然语言")
    assert len(updates["options"]) == 2
    assert updates["options"][0]["title"] == "传统关键词搜索增强版"
    assert "权限和隐私" in updates["blind_spots"][0]["body"]


def test_parse_pane_updates_malformed_json_degrades_gracefully(capsys):
    from app.gateway import _parse_pane_updates

    chat, updates = _parse_pane_updates(
        "prose\n<pane_updates>{ this is not json </pane_updates>"
    )
    # Fence still stripped; updates empty.
    assert "<pane_updates>" not in chat
    assert updates == {}


def test_parse_pane_updates_malformed_json_extracts_inner_sections(capsys):
    from app.gateway import _parse_pane_updates

    chat, updates = _parse_pane_updates(
        """可见回复
<pane_updates>
不是 JSON。

**目标**

让团队能用自然语言找到本地和共享空间里的文件。

**候选方案**

1. Embedding 语义检索
把文件切块向量化后按语义召回。

**风险**

- 权限过滤如果后置，会泄露文件标题。
</pane_updates>"""
    )

    assert chat == "可见回复"
    assert updates["decisions"][0]["body"].startswith("让团队能用自然语言")
    assert updates["options"][0]["title"] == "Embedding"
    assert "权限过滤" in updates["blind_spots"][0]["body"]


def test_parse_pane_updates_recovers_nested_real_block():
    from app.gateway import _parse_pane_updates

    chat, updates = _parse_pane_updates(
        """我先说明：回复里带 `<pane_updates>` JSON 会更新右侧面板。
<pane_updates>
` JSON 后会被拆成 typed messages。
真正内容如下：
<pane_updates>{"headline":"方案收敛","decisions":[{"body":"目标：自然语言找文件并解释命中原因"}]}</pane_updates>
</pane_updates>"""
    )

    assert "<pane_updates>" not in chat
    assert updates["headline"] == "方案收敛"
    assert updates["decisions"][0]["body"].startswith("目标：自然语言找文件")


def test_post_pane_updates_posts_one_typed_message_per_item(monkeypatch):
    from app import gateway

    calls: list[tuple] = []
    monkeypatch.setattr(
        gateway, "_post",
        lambda host, token, topic_id, type_, body, **meta:
            calls.append((type_, body, meta)) or {"id": len(calls)},
    )

    updates = {
        "decisions": [{"body": "三端都要 SSO"}],
        "options": [
            {"title": "A. SAML", "body": "成熟、可复用",
             "pros": ["桌面 ok"], "cons": ["移动差"]}
        ],
        "constraints": [{"body": "Java/Spring"}],
        "open_questions": [{"body": "离线模式？"}],
    }
    n = gateway._post_pane_updates("h", "t", 7, updates, source_msg_id=123)
    assert n == 4

    types = [c[0] for c in calls]
    assert "decision" in types
    assert "proactive_finding" in types
    assert "finding" in types
    assert "question" in types

    # Look at the option call: must carry title + pros + cons metadata.
    opt = next(c for c in calls if c[0] == "proactive_finding")
    assert opt[2]["title"] == "A. SAML"
    assert opt[2]["pros"] == ["桌面 ok"]
    assert opt[2]["cons"] == ["移动差"]
    assert opt[2]["discussion_kind"] == "option"
    assert opt[2]["promoted_from"] == 123


def test_post_pane_updates_skips_empty_items(monkeypatch):
    from app import gateway

    calls = []
    monkeypatch.setattr(
        gateway, "_post",
        lambda host, token, topic_id, type_, body, **meta:
            calls.append((type_, body)) or {"id": 1},
    )
    n = gateway._post_pane_updates("h", "t", 1, {
        "decisions": [{"body": "  "}, {"body": "real one"}, {}],
        "open_questions": [],
    })
    assert n == 1
    assert calls == [("decision", "real one")]


# ─── Slice 5d: annotations feed into the next prompt ─────────────────────


def test_build_prompt_surfaces_unresolved_annotations():
    from app import gateway

    me = gateway.Identity(
        human_id=1, human_name="Jacky",
        agent_instance_id=4, role="claude", device_label="mac",
    )
    recent = [
        {"id": 10, "type": "chat", "actor_type": "agent", "actor_id": 4,
         "body": "可以考虑 SAML 或 OIDC"},
        {"id": 11, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "iOS Safari 真的能跳回来吗？",
         "metadata": {"target_message_id": 10,
                      "target_quote": "SAML 桌面成熟但移动弱"}},
        {"id": 12, "type": "chat", "actor_type": "human", "actor_id": 1,
         "body": "另外，离线模式呢？"},
    ]
    trigger = recent[-1]
    prompt = gateway._build_prompt(me, "登录改造", recent, trigger)
    assert "SAML 桌面成熟但移动弱" in prompt
    assert "iOS Safari 真的能跳回来吗" in prompt
    # The annotation should NOT also appear in the regular history block
    # (we surface it in a dedicated section instead).
    assert prompt.count("iOS Safari") == 1


def test_build_prompt_drops_resolved_annotations():
    from app import gateway

    me = gateway.Identity(
        human_id=1, human_name="J", agent_instance_id=4,
        role="claude", device_label="mac",
    )
    recent = [
        {"id": 10, "type": "chat", "actor_type": "agent", "actor_id": 4,
         "body": "..."},
        {"id": 11, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "first comment",
         "metadata": {"target_message_id": 10, "target_quote": "X"}},
        {"id": 12, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "(resolved)",
         "metadata": {"target_message_id": 10, "target_quote": "X",
                      "resolved": True, "resolves": 11}},
        {"id": 13, "type": "chat", "actor_type": "human", "actor_id": 1,
         "body": "继续聊"},
    ]
    trigger = recent[-1]
    prompt = gateway._build_prompt(me, "T", recent, trigger)
    # The resolved annotation should NOT be surfaced.
    assert "first comment" not in prompt


# ─── Bug fix tests: read_topic ordering + default timeout ─────────────


def test_gateway_default_cli_timeout_is_240():
    """Long discussion prompts take 60-180s; 120 used to clip the tail.
    Lock the new default so it doesn't silently regress."""
    import argparse
    from app import gateway
    # Probe the default by parsing an empty `run` argv. Simplest way is to
    # look at the parser definition's default — but the parser is built
    # inside main(). Easier: spot-check the default by re-parsing.
    src = open(gateway.__file__).read()
    assert 'type=int, default=240' in src


def test_read_topic_no_after_id_uses_descending_then_reverses(monkeypatch):
    """When pulled without after_id, the gateway should ask for newest-first
    (so the tail isn't dropped by LIMIT) and then reverse for callers."""
    from app import gateway

    called: dict = {}
    # Server returns 5 messages newest-first (id 100, 99, 98, 97, 96)
    def fake_call(host, token, name, args):
        called["args"] = args
        return [
            {"id": 100, "type": "chat", "actor_type": "human"},
            {"id": 99,  "type": "chat", "actor_type": "human"},
            {"id": 98,  "type": "chat", "actor_type": "human"},
            {"id": 97,  "type": "chat", "actor_type": "human"},
            {"id": 96,  "type": "chat", "actor_type": "human"},
        ]
    monkeypatch.setattr(gateway, "_mcp_call", fake_call)

    msgs = gateway._read_topic("h", "t", 9, None)
    # Asked for desc
    assert called["args"]["order"] == "desc"
    # Returned in ascending order to the caller
    assert [m["id"] for m in msgs] == [96, 97, 98, 99, 100]


def test_read_topic_with_after_id_keeps_ascending(monkeypatch):
    """Incremental polling (after_id given) must NOT flip to desc — that
    would break the cursor advancement logic."""
    from app import gateway

    called: dict = {}
    def fake_call(host, token, name, args):
        called["args"] = args
        return [
            {"id": 11, "type": "chat", "actor_type": "human"},
            {"id": 12, "type": "chat", "actor_type": "human"},
        ]
    monkeypatch.setattr(gateway, "_mcp_call", fake_call)
    msgs = gateway._read_topic("h", "t", 9, 10)
    assert called["args"]["after_id"] == 10
    assert "order" not in called["args"]
    assert [m["id"] for m in msgs] == [11, 12]


def test_proactive_join_requires_multi_human_discussion_density():
    from app import gateway

    recent = [
        {"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "A"},
        {"id": 2, "type": "chat", "actor_type": "human", "actor_id": 2, "body": "B"},
    ]

    assert gateway._should_proactively_join(recent, recent[-1], my_agent_id=7) is True


def test_proactive_join_waits_for_a_two_message_exchange():
    from app import gateway

    recent = [
        {"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "A"},
    ]

    assert gateway._should_proactively_join(recent, recent[-1], my_agent_id=7) is False


def test_proactive_join_stays_quiet_for_single_human():
    from app import gateway

    recent = [
        {"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "A"},
        {"id": 2, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "B"},
        {"id": 3, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "C"},
        {"id": 4, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "D"},
    ]

    assert gateway._should_proactively_join(recent, recent[-1], my_agent_id=7) is False


def test_proactive_prompt_tells_agent_not_to_take_over():
    from app import gateway

    me = gateway.Identity(1, "Jacky", 7, "codex", "mac")
    recent = [
        {"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "先做 IM"},
        {"id": 2, "type": "chat", "actor_type": "human", "actor_id": 2, "body": "还要 context"},
        {"id": 3, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "agent 要旁听"},
        {"id": 4, "type": "chat", "actor_type": "human", "actor_id": 2, "body": "何时发言？"},
    ]
    system_prompt, user_prompt = gateway._build_prompt_split(
        me, "T", recent, recent[-1], intervention_mode="proactive",
    )

    assert "not a fourth person competing for airtime" in system_prompt
    assert "living context pane" in system_prompt
    assert "pane_updates carry the durable shared structure" in system_prompt
    assert "proactive observer" in user_prompt
    assert "living discussion memo" in user_prompt
    assert "broaden the option space" in user_prompt
    assert "avoid taking over" in user_prompt


def test_direct_prompt_tells_agent_to_nudge_off_topic_tangents():
    from app import gateway

    me = gateway.Identity(1, "Jacky", 7, "codex", "mac")
    recent = [
        {
            "id": 1,
            "type": "chat",
            "actor_type": "human",
            "actor_id": 1,
            "body": "自然语言 Everything 工具要解决文件检索。",
        },
        {
            "id": 2,
            "type": "chat",
            "actor_type": "human",
            "actor_id": 2,
            "body": "明天穿什么衣服去公司？",
        },
        {
            "id": 3,
            "type": "chat",
            "actor_type": "human",
            "actor_id": 1,
            "body": "@neo 你觉得呢？",
        },
    ]
    system_prompt, user_prompt = gateway._build_prompt_split(
        me, "自然语言Everything工具，让检索文件更灵活", recent, recent[-1],
    )

    assert "GOAL GUARDIAN" in system_prompt
    assert "do not answer the tangent" in system_prompt
    assert "gentle nudge back to the topic" in system_prompt
    assert "suggest moving it to a separate topic" in system_prompt
    assert "自然语言Everything工具" in user_prompt
    assert "穿什么衣服" in user_prompt


def test_health_prompt_switches_to_safety_mode():
    from app import gateway

    me = gateway.Identity(1, "Jacky", 7, "codex", "mac")
    trigger = {
        "id": 1,
        "type": "chat",
        "actor_type": "human",
        "actor_id": 1,
        "body": "我现在肚子疼，想和家人聊一下怎么用药",
    }
    system_prompt, user_prompt = gateway._build_prompt_split(
        me, "新话题", [trigger], trigger,
    )

    assert "HEALTH SAFETY MODE" in system_prompt
    assert "must not diagnose or prescribe" in system_prompt
    assert "red flags" in system_prompt
    assert "Do not brainstorm like a design topic" in user_prompt


def test_build_prompt_split_isolates_stable_persona():
    """The new split separates stable persona+protocol (cacheable) from
    variable history+message (per-turn). Cache-hit rate depends on the
    stable prefix being byte-identical across turns."""
    from app import gateway

    me = gateway.Identity(
        human_id=1, human_name="J", agent_instance_id=4,
        role="claude", device_label="mac",
    )
    recent_a = [
        {"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "A"},
        {"id": 2, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "B"},
    ]
    recent_b = recent_a + [
        {"id": 3, "type": "chat", "actor_type": "human", "actor_id": 1, "body": "C"},
    ]
    sys_a, user_a = gateway._build_prompt_split(me, "T", recent_a, recent_a[-1])
    sys_b, user_b = gateway._build_prompt_split(me, "T", recent_b, recent_b[-1])

    # System prompt must be byte-identical across turns (cache-key).
    assert sys_a == sys_b
    # User prompt obviously differs (history grew).
    assert user_a != user_b
    # Persona content lives in system, not user.
    assert "design partner" in sys_a
    assert "design partner" not in user_a
    # pane_updates spec lives in system.
    assert "<pane_updates>" in sys_a


def test_claude_command_injects_append_system_prompt_when_given():
    from app.gateway import _agent_command
    cmd = _agent_command(["claude", "--print"], "claude", None, "PERSONA")
    assert "--append-system-prompt" in cmd
    assert "PERSONA" in cmd


def test_claude_command_omits_system_prompt_when_none():
    from app.gateway import _agent_command
    cmd = _agent_command(["claude", "--print"], "claude", None, None)
    assert "--append-system-prompt" not in cmd


def test_codex_command_skips_git_repo_check_for_local_gateway():
    from app.gateway import _agent_command
    cmd = _agent_command(["codex", "exec"], "codex", None, None)
    assert cmd == ["codex", "exec", "--skip-git-repo-check", "--json"]


def test_codex_resume_keeps_subcommand_after_exec_options():
    from app.gateway import _agent_command
    cmd = _agent_command(["codex", "exec"], "codex", "sess-1", None)
    assert cmd == ["codex", "exec", "--skip-git-repo-check", "resume", "sess-1", "--json"]


def test_build_prompt_includes_resolved_questions_section():
    """When the human has resolved a question via the right-pane 答 button,
    the gateway should surface the Q+A pair so the agent stops re-raising it."""
    from app import gateway

    me = gateway.Identity(
        human_id=1, human_name="J", agent_instance_id=4,
        role="claude", device_label="mac",
    )
    recent = [
        # Agent posted a question
        {"id": 10, "type": "question", "actor_type": "agent", "actor_id": 4,
         "body": "MVP 是同时支持港大+UCAS 还是先收窄？",
         "metadata": {"discussion_kind": "open_question"}},
        # Human resolved it via inline answer
        {"id": 11, "type": "decision", "actor_type": "human", "actor_id": 1,
         "body": "先收窄到 UCAS 走的英港国际部学生",
         "metadata": {"discussion_kind": "decision",
                      "resolves_question": 10,
                      "promoted_from": 10}},
        # New human message
        {"id": 12, "type": "chat", "actor_type": "human", "actor_id": 1,
         "body": "下一步谈数据来源"},
    ]
    trigger = recent[-1]
    sys_p, user_p = gateway._build_prompt_split(me, "T", recent, trigger)
    assert "already answered" in user_p
    assert "MVP" in user_p and "收窄到 UCAS" in user_p
    # Should NOT live in the system prompt (which must stay cache-stable).
    assert "已 already answered" not in sys_p


def test_post_pane_updates_routes_blind_spots(monkeypatch):
    """blind_spots in pane_updates must be posted as proactive_finding
    typed messages tagged with discussion_kind=blind_spot. Right pane
    projects them into the「可能漏掉」panel."""
    from app import gateway

    calls: list[tuple] = []
    monkeypatch.setattr(
        gateway, "_post",
        lambda host, token, topic_id, type_, body, **meta:
            calls.append((type_, body, meta)) or {"id": len(calls)},
    )

    n = gateway._post_pane_updates("h", "t", 1, {
        "blind_spots": [
            {"body": "没考虑香港本地学生中文需求"},
            {"body": "  "},  # empty — should be skipped
        ],
    }, source_msg_id=42)
    assert n == 1
    type_, body, meta = calls[0]
    assert type_ == "proactive_finding"
    assert body == "没考虑香港本地学生中文需求"
    assert meta["discussion_kind"] == "blind_spot"
    assert meta["promoted_from"] == 42


def test_render_spec_markdown_groups_by_discussion_kind():
    """lets spec must group typed messages by discussion_kind so the
    downstream weak agent sees decisions / constraints / blind spots /
    critiques as separate sections, not as a chronological pile."""
    from app import gateway

    msgs = [
        {"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1,
         "body": "we want to support hk + ucas students",
         "metadata": None},
        {"id": 2, "type": "decision", "actor_type": "agent", "actor_id": 5,
         "body": "MVP 收窄到 UCAS 国际部学生",
         "metadata": {"discussion_kind": "decision"}},
        {"id": 3, "type": "finding", "actor_type": "agent", "actor_id": 5,
         "body": "数据源限 UCAS 公开 API",
         "metadata": {"discussion_kind": "constraint"}},
        {"id": 4, "type": "proactive_finding", "actor_type": "agent", "actor_id": 5,
         "body": "没考虑香港本地学生中文需求",
         "metadata": {"discussion_kind": "blind_spot"}},
        {"id": 5, "type": "proactive_finding", "actor_type": "agent", "actor_id": 5,
         "body": "纯线上工具竞品已多，差异化弱",
         "metadata": {"discussion_kind": "critique"}},
        {"id": 6, "type": "proactive_finding", "actor_type": "agent", "actor_id": 5,
         "body": "可加家长 portal 抓住付费决策者",
         "metadata": {"discussion_kind": "extension"}},
        # An open_question that gets resolved — must NOT appear in 待解决
        {"id": 7, "type": "question", "actor_type": "agent", "actor_id": 5,
         "body": "客户端是 GUI 还是 CLI？",
         "metadata": {"discussion_kind": "open_question"}},
        {"id": 8, "type": "decision", "actor_type": "human", "actor_id": 1,
         "body": "GUI",
         "metadata": {"discussion_kind": "decision", "resolves_question": 7}},
        # An open_question that does NOT have a resolution — must appear
        {"id": 9, "type": "question", "actor_type": "agent", "actor_id": 5,
         "body": "数据更新频率？",
         "metadata": {"discussion_kind": "open_question"}},
        # A mermaid in chat — collected into 图与资料
        {"id": 10, "type": "chat", "actor_type": "agent", "actor_id": 5,
         "body": "整体架构：\n```mermaid\ngraph TD\nA-->B\n```\n",
         "metadata": None},
    ]

    out = gateway._render_spec_markdown(42, msgs)
    assert "# Topic #42" in out
    # Sections
    assert "共识 (decisions)" in out
    assert "MVP 收窄到 UCAS 国际部学生" in out
    assert "GUI" in out  # the resolving decision
    assert "约束 (constraints)" in out
    assert "数据源限 UCAS 公开 API" in out
    assert "盲点" in out
    assert "没考虑香港本地学生中文需求" in out
    assert "反方观点" in out
    assert "纯线上工具竞品已多" in out
    assert "延展想法" in out
    assert "家长 portal" in out
    # Open question that got resolved should NOT show up under "待解决"
    assert "客户端是 GUI 还是 CLI" not in out.split("## 待解决问题")[-1].split("## ")[0] \
        if "## 待解决问题" in out else True
    # Open question without resolution must show up
    assert "数据更新频率" in out
    # Mermaid collected
    assert "```mermaid" in out
    assert "graph TD" in out
    # Tail chats — last 12 chats with id markers
    assert "关键讨论 (tail)" in out


def test_render_spec_markdown_includes_msg_id_citations_and_score_sort():
    """Each spec line should carry a [#id] back-reference so a downstream
    agent can grep the chat for context, and items must be sorted by
    aggregate ±1 score so human-curated priorities rise to the top."""
    from app import gateway

    msgs = [
        # Two decisions; the second is +2 voted, should sort first.
        {"id": 1, "type": "decision", "actor_type": "agent", "actor_id": 5,
         "body": "decision A",
         "metadata": {"discussion_kind": "decision"}},
        {"id": 2, "type": "decision", "actor_type": "agent", "actor_id": 5,
         "body": "decision B",
         "metadata": {"discussion_kind": "decision"}},
        # Two humans +1 each on msg 2
        {"id": 100, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "", "metadata": {"target_message_id": 2, "score": 1}},
        {"id": 101, "type": "annotation", "actor_type": "human", "actor_id": 7,
         "body": "", "metadata": {"target_message_id": 2, "score": 1}},
        # Same actor re-vote — only latest counts (re-vote to 0 cancels).
        {"id": 102, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "", "metadata": {"target_message_id": 2, "score": 1}},
    ]
    out = gateway._render_spec_markdown(7, msgs)
    # Citations present
    assert "[#1]" in out
    assert "[#2]" in out
    # Score badge on msg 2
    assert "`+2`" in out
    # Sort: decision B (+2) appears before decision A in 共识 section.
    dec_section = out.split("## 共识")[1].split("## ")[0]
    assert dec_section.index("decision B") < dec_section.index("decision A")


def test_strip_polish_preamble_removes_common_wrappers():
    """When claude prepends '以下是…' or '```markdown' the postprocessor
    must strip those so the spec starts cleanly with '# Topic …'."""
    from app import gateway

    header = "# Topic #9 — PS service"
    raw_outputs = [
        # Case 1: 「以下是」 preamble + horizontal rule + body
        "以下是完整增强后的 spec：\n\n---\n\n## 设计目标\n…",
        # Case 2: code-fence wrap + dropped header
        "```markdown\n## 设计目标\n…\n```",
        # Case 3: header preserved + clean
        f"{header}\n\n## 设计目标\n…",
        # Case 4: english preamble
        "Here is the polished spec:\n\n## 设计目标\n…",
    ]
    for raw in raw_outputs:
        out = gateway._strip_polish_preamble(raw, expected_header=header)
        assert out.startswith(header), f"missing header in: {out[:80]!r}"
        assert "以下是" not in out
        assert not out.startswith("```")


def test_append_self_test_inserts_section_with_citations_preserved(monkeypatch):
    """--self-test should append a「自检」section while leaving the rest of
    the spec (including [#nnn] citations) untouched."""
    from app import gateway

    class FakeProc:
        returncode = 0
        stderr = ""
        stdout = (
            "- 状态机的「完成」分支没定义验收 [#207]\n"
            "- KB schema 字段未列 [#218]\n"
            "- Reviewer 路由策略未定 [#222]\n"
        )

    monkeypatch.setattr(
        gateway.subprocess if hasattr(gateway, "subprocess") else __import__("subprocess"),
        "run",
        lambda cmd, **kw: FakeProc(),
    )

    spec = (
        "# Topic #9\n\n"
        "## 共识\n"
        "- MVP 切 PS [#187]\n"
    )
    out = gateway._append_self_test(spec)
    # Spec body preserved
    assert "# Topic #9" in out
    assert "MVP 切 PS [#187]" in out
    # Self-test section appended with citations intact
    assert "## 自检" in out
    assert "状态机的「完成」分支没定义验收 [#207]" in out
    assert "KB schema" in out


def test_persona_red_appends_red_team_overlay_to_system_prompt():
    """--persona=red must add the red-team overlay to the system prompt
    so the agent challenges the direction. Default persona must leave the
    base prompt untouched."""
    from app import gateway

    me = gateway.Identity(human_id=1, human_name="J", agent_instance_id=4,
                          role="claude", device_label="mac")
    recent = [{"id": 1, "type": "chat", "actor_type": "human", "actor_id": 1,
               "body": "let's ship X", "metadata": None}]
    trigger = recent[0]

    sys_default, _ = gateway._build_prompt_split(me, "T", recent, trigger, persona="default")
    sys_red, _ = gateway._build_prompt_split(me, "T", recent, trigger, persona="red")
    sys_blue, _ = gateway._build_prompt_split(me, "T", recent, trigger, persona="blue")

    assert "RED-TEAM" not in sys_default
    assert "BLUE-TEAM" not in sys_default
    assert "RED-TEAM" in sys_red
    assert "BLUE-TEAM" in sys_blue
    # Same base prompt — overlay is additive, not replacement.
    assert "sharp design partner" in sys_default
    assert "sharp design partner" in sys_red
    assert "sharp design partner" in sys_blue


def test_collect_open_annotations_skips_pure_score_votes():
    """+1/-1 vote annotations have empty body — they're a vote affordance,
    not a comment thread. The prompt context must skip them, otherwise the
    agent sees ` - on "node": ` empty lines on every turn."""
    from app import gateway
    recent = [
        # Pure vote — should be skipped
        {"id": 100, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "", "metadata": {"target_message_id": 50, "target_quote": "GUI",
                                   "score": 1}},
        # Real comment — should be kept
        {"id": 101, "type": "annotation", "actor_type": "human", "actor_id": 1,
         "body": "这个节点要拆细", "metadata": {"target_message_id": 50,
                                                 "target_quote": "KB"}},
    ]
    out = gateway._collect_open_annotations(recent)
    assert len(out) == 1
    assert out[0]["id"] == 101
