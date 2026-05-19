"""End-to-end tests for the v1.5 MCP tools that bridge agents to the
typed-message + artifact world.

Each test goes through the real ASGI middleware (BearerAuthMiddleware
sets the principal contextvar) and the FastMCP HTTP transport, so a
failure here would actually break a real CC/Codex connecting via
.mcp.json. The shape of every assertion matches what an agent caller
would observe over JSON-RPC.
"""
from __future__ import annotations

import base64
import json
import subprocess

import pytest


def _call(client, headers, name, arguments, *, expect_list: bool = False):
    """Helper: POST /mcp/ with a JSON-RPC tools/call and return the parsed result content.

    FastMCP serializes a tool that returns ``list[dict]`` as N separate text
    content blocks (one per item). When a list has exactly one element we
    can't tell whether the tool returns a dict or a single-element list,
    so callers explicitly pass ``expect_list=True`` for list-returning tools.
    """
    resp = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.text
    if body.startswith("event:"):
        for line in body.splitlines():
            if line.startswith("data: "):
                body = line[6:]
                break
    payload = json.loads(body)
    result = payload.get("result", {})

    # Prefer structuredContent when present and unambiguous.
    sc = result.get("structuredContent")
    if isinstance(sc, dict) and set(sc.keys()) == {"result"}:
        return sc["result"]
    if sc is not None:
        return sc

    content = result.get("content", [])
    texts = [c["text"] for c in content if c.get("type") == "text"]
    if not texts:
        return result
    parsed = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except json.JSONDecodeError:
            parsed.append(t)
    if expect_list:
        return parsed
    return parsed if len(parsed) > 1 else parsed[0]


@pytest.fixture
def agent_auth(client):
    """Issue an agent-bound token for Neo + claude on neo-mbp and return Bearer headers."""
    from app.auth import issue_token
    from app.identity import ensure_human, ensure_agent_instance

    neo_id = ensure_human("Neo")
    ai_id = ensure_agent_instance("claude", neo_id, "neo-mbp-mcp-test")
    tok, _ = issue_token(human_id=neo_id, agent_instance_id=ai_id, label="mcp-v15-test")
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json, text/event-stream",
    }, neo_id, ai_id


def test_whoami_returns_token_principal(client, agent_auth):
    headers, neo_id, ai_id = agent_auth
    out = _call(client, headers, "whoami", {})
    assert out["human_id"] == neo_id
    assert out["agent_instance_id"] == ai_id
    assert out["human_name"] == "Neo"
    assert out["role"] == "claude"
    assert out["device_label"] == "neo-mbp-mcp-test"


def test_list_my_topics_sees_a_topic(client, agent_auth):
    headers, _, _ = agent_auth
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-v15-t1', 'MCP T1')")

    topics = _call(client, headers, "list_my_topics", {"limit": 200}, expect_list=True)
    slugs = {t["slug"] for t in topics}
    assert "mcp-v15-t1" in slugs


def test_post_typed_message_writes_as_calling_agent(client, agent_auth):
    headers, neo_id, ai_id = agent_auth
    from app.db import connect
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mcp-v15-t2', 'MCP T2')"
        )
        topic_id = cur.lastrowid

    msg = _call(client, headers, "post_typed_message", {
        "topic_id": topic_id,
        "type": "chat",
        "body": "hello from MCP agent",
    })
    assert msg["topic_id"] == topic_id
    assert msg["type"] == "chat"
    assert msg["actor_type"] == "agent"
    assert msg["actor_id"] == ai_id
    assert msg["body"] == "hello from MCP agent"


def test_post_typed_message_addressed_to_lands_in_attention(client, agent_auth):
    headers, _, _ = agent_auth
    from app.identity import ensure_human
    from app.db import connect

    trinity_id = ensure_human("Trinity")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mcp-v15-t3', 'MCP T3')"
        )
        topic_id = cur.lastrowid

    _call(client, headers, "post_typed_message", {
        "topic_id": topic_id,
        "type": "question",
        "body": "@trinity is this fine?",
        "addressed_to": str(trinity_id),
    })

    # Now check the attention queue using a human-session-style HTTP call.
    # We use a separate token for the test client to query /api/attention.
    from app.auth import issue_token
    admin_id = ensure_human("admin")
    tok, _ = issue_token(human_id=admin_id, label="att-probe")
    att = client.get(
        f"/api/attention?human_id={trinity_id}",
        headers={"Authorization": f"Bearer {tok}"},
    ).json()
    bodies = [m["body"] for m in att["needs_decision"]]
    assert "@trinity is this fine?" in bodies


def test_read_topic_returns_stream(client, agent_auth):
    headers, neo_id, ai_id = agent_auth
    from app.db import connect
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mcp-v15-t4', 'MCP T4')"
        )
        topic_id = cur.lastrowid

    for body in ("first", "second", "third"):
        _call(client, headers, "post_typed_message", {
            "topic_id": topic_id, "type": "chat", "body": body,
        })

    msgs = _call(client, headers, "read_topic", {"topic_id": topic_id}, expect_list=True)
    bodies = [m["body"] for m in msgs]
    assert bodies == ["first", "second", "third"]

    # after_id filter
    middle_id = msgs[1]["id"]
    tail = _call(client, headers, "read_topic", {
        "topic_id": topic_id, "after_id": middle_id,
    }, expect_list=True)
    assert [m["body"] for m in tail] == ["third"]


def test_create_and_update_artifact_via_mcp(client, agent_auth, tmp_path, monkeypatch):
    headers, _, _ = agent_auth
    # Provision a clean git repo for the artifact backend
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    monkeypatch.setenv("LETS_GIT_REPO", str(tmp_path))

    from app.db import connect
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mcp-v15-t5', 'MCP T5')"
        )
        topic_id = cur.lastrowid

    create = _call(client, headers, "create_artifact", {
        "topic_id": topic_id,
        "slug": "smoke-ppt",
        "type": "doc",
        "title": "Smoke PPT v0",
        "content_b64": base64.b64encode(b"v0 outline").decode(),
        "summary": "initial outline",
    })
    art_id = create["artifact"]["id"]
    assert create["version"]["version_label"] == "v0"
    assert (tmp_path / "smoke-ppt.doc").read_bytes() == b"v0 outline"

    update = _call(client, headers, "update_artifact", {
        "artifact_id": art_id,
        "version_label": "v1",
        "content_b64": base64.b64encode(b"v1 with refinements").decode(),
        "summary": "tightened wording",
    })
    assert update["version"]["version_label"] == "v1"
    assert (tmp_path / "smoke-ppt.doc").read_bytes() == b"v1 with refinements"


def test_v15_tools_require_agent_bound_token(client):
    """A token bound to a human-only (no agent_instance) should NOT be able to post."""
    from app.auth import issue_token
    from app.identity import ensure_human

    neo_id = ensure_human("Neo")
    tok, _ = issue_token(human_id=neo_id, label="human-only")  # no agent_instance_id
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json, text/event-stream",
    }

    from app.db import connect
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mcp-v15-t6', 'MCP T6')"
        )
        topic_id = cur.lastrowid

    # Call should error — assert via the JSON-RPC error envelope, not _call helper.
    resp = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {
                "name": "post_typed_message",
                "arguments": {"topic_id": topic_id, "type": "chat", "body": "should fail"},
            },
        },
    )
    assert resp.status_code == 200
    # Tool error comes back either as JSON-RPC error or as a tool result with isError=true.
    body = resp.text
    assert "agent_instance" in body, f"expected agent_instance error mention; got {body[:400]}"
